from __future__ import annotations

import asyncio
import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Callable, Optional

from pymongo.errors import DuplicateKeyError

from page_service import PageService
from pipeline import (CommandCancelled, CommandContext, PipelineError,
                      TranscriptionUnavailable, run_command)
from providers import Providers
from session import SessionStore
from storage import PageStore
from transcriber import TranscriptionFailed

logger = logging.getLogger("mlp.commands")

TERMINAL = frozenset({"done", "failed", "cancelled"})

RunFn = Callable[[Callable[[dict], None]], dict]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(when) -> Optional[str]:
    return when.isoformat(timespec="seconds") if isinstance(when, datetime) else when


class CommandStore:
    def __init__(self, collection, ttl_days: int = 7):
        self._commands = collection
        self.ttl_days = ttl_days

    def ensure_indexes(self) -> None:
        self._commands.create_index("key", unique=True, sparse=True)
        self._commands.create_index([("owner", 1), ("created", -1)])
        self._commands.create_index("created", expireAfterSeconds=self.ttl_days * 86400)

    def begin(self, owner: str, build_id: Optional[str], text: str,
              key: Optional[str] = None) -> tuple[dict, bool]:
        now = _now()
        record = {
            "_id": uuid.uuid4().hex[:16],
            "owner": owner,
            "build_id": build_id,
            "text": text,
            "status": "queued",
            "result": None,
            "error": None,
            "created": now,
            "updated": now,
            "started": None,
            "finished": None,
        }
        if key:
            record["key"] = f"{owner}:{key}"
        try:
            self._commands.insert_one(record)
        except DuplicateKeyError:
            existing = self._commands.find_one({"key": record["key"], "owner": owner})
            return existing, False
        return record, True

    def get(self, command_id: str, owner: str) -> Optional[dict]:
        return self._commands.find_one({"_id": command_id, "owner": owner})

    def start(self, command_id: str) -> bool:
        now = _now()
        return self._commands.update_one(
            {"_id": command_id, "status": "queued"},
            {"$set": {"status": "running", "started": now, "updated": now}},
        ).matched_count == 1

    def finish(self, command_id: str, result: dict) -> bool:
        now = _now()
        return self._commands.update_one(
            {"_id": command_id, "status": "running"},
            {"$set": {"status": "done", "result": result, "finished": now, "updated": now}},
        ).matched_count == 1

    def fail(self, command_id: str, error: dict) -> bool:
        now = _now()
        return self._commands.update_one(
            {"_id": command_id, "status": {"$in": ["queued", "running"]}},
            {"$set": {"status": "failed", "error": error, "finished": now, "updated": now}},
        ).matched_count == 1

    def cancel(self, command_id: str, owner: str) -> Optional[dict]:
        now = _now()
        matched = self._commands.update_one(
            {"_id": command_id, "owner": owner, "status": {"$in": ["queued", "running"]}},
            {"$set": {"status": "cancelled", "finished": now, "updated": now,
                      "error": {"stage": "cancelled", "message": "Cancelled."}}},
        ).matched_count == 1
        record = self.get(command_id, owner)
        return record if matched or record is not None else None

    def is_cancelled(self, command_id: str) -> bool:
        doc = self._commands.find_one({"_id": command_id}, {"status": 1})
        return doc is not None and doc.get("status") == "cancelled"

    @staticmethod
    def view(record: dict) -> dict:
        return {
            "id": record["_id"],
            "buildId": record.get("build_id"),
            "status": record["status"],
            "text": record.get("text"),
            "result": record.get("result"),
            "error": record.get("error"),
            "created": _iso(record.get("created")),
            "updated": _iso(record.get("updated")),
        }


class Execution:
    def __init__(self, command_id: str):
        self.id = command_id
        self.history: list[dict] = []
        self.subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self.done = threading.Event()
        self.cancel_requested = threading.Event()
        self.outcome: Optional[dict] = None
        self._lock = threading.Lock()
        self.future = None

    def subscribe(self) -> asyncio.Queue:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            for event in self.history:
                queue.put_nowait(event)
            if self.done.is_set():
                queue.put_nowait(None)
            else:
                self.subscribers.append((loop, queue))
        return queue

    def publish(self, event: dict) -> None:
        with self._lock:
            self.history.append(event)
            targets = list(self.subscribers)
        for loop, queue in targets:
            loop.call_soon_threadsafe(queue.put_nowait, event)

    def close(self, outcome: dict) -> None:
        with self._lock:
            self.outcome = outcome
            self.done.set()
            targets = list(self.subscribers)
            self.subscribers.clear()
        for loop, queue in targets:
            loop.call_soon_threadsafe(queue.put_nowait, None)


class CommandService:
    def __init__(self, pages: PageStore, sessions: SessionStore, commands: CommandStore,
                 providers: Providers, transcriber, page_service: PageService,
                 max_workers: int = 2):
        self.pages = pages
        self.sessions = sessions
        self.commands = commands
        self.providers = providers
        self.transcriber = transcriber
        self.page_service = page_service
        self._pool = ThreadPoolExecutor(max_workers=max(1, max_workers),
                                        thread_name_prefix="command")
        self._live: dict[str, Execution] = {}
        self._lock = threading.Lock()

    def context(self, user: dict, session_id: Optional[str], page_id: Optional[str],
                answering: bool = False, section: Optional[str] = None,
                model: Optional[str] = None) -> CommandContext:
        return CommandContext(session_id=session_id or self.sessions.new_id(),
                              page_id=page_id, answering=answering, section=section,
                              owner=user["id"], model=self.providers.models.check(model))

    def execute(self, text: str, language: Optional[str], ctx: CommandContext,
                on_step=None, keep_trace: bool = False) -> dict:
        result = run_command(text, language, self.pages, ctx, self.sessions,
                             on_step=on_step, providers=self.providers.for_model(ctx.model))
        if not keep_trace:
            result.pop("_trace", None)
        result.setdefault("sessionId", ctx.session_id)
        return self.page_service.enrich(result, ctx.owner)

    def text_run(self, text: str, ctx: CommandContext) -> RunFn:
        def run(on_step):
            return self.execute(text, "en", ctx, on_step)
        return run

    def audio_run(self, audio: bytes, ctx: CommandContext) -> RunFn:
        def run(on_step):
            on_step({"index": 0, "tool": "transcribe"})
            try:
                text, language = self.transcriber.transcribe(audio)
            except TranscriptionFailed as e:
                logger.error("transcription failed: %s", e)
                raise TranscriptionUnavailable(
                    "Speech recognition is unavailable -- type the command instead.") from e
            logger.info("transcribed (lang=%s): %r", language, text)
            on_step({"index": 0, "tool": "transcribed", "text": text})
            return self.execute(text, language, ctx, on_step)
        return run

    def submit(self, owner: str, build_id: Optional[str], text: str, run: RunFn,
               key: Optional[str] = None) -> tuple[dict, Optional[Execution]]:
        record, created = self.commands.begin(owner, build_id, text, key)
        with self._lock:
            if not created:
                return record, self._live.get(record["_id"])
            execution = Execution(record["_id"])
            self._live[record["_id"]] = execution
        execution.future = self._pool.submit(self._execute, execution, run)
        return record, execution

    def _execute(self, execution: Execution, run: RunFn) -> None:
        command_id = execution.id
        outcome = {"type": "error", "commandId": command_id,
                   "error": {"stage": "internal", "message": "Internal server error."}}
        try:
            if not self.commands.start(command_id):
                outcome = {"type": "error", "commandId": command_id,
                           "error": {"stage": "cancelled", "message": "Cancelled."}}
                return

            def on_step(event: dict) -> None:
                if execution.cancel_requested.is_set():
                    raise CommandCancelled("Cancelled.")
                execution.publish({"type": "step", "commandId": command_id, **event})

            result = run(on_step)
            if self.commands.finish(command_id, result):
                outcome = {"type": "result", "commandId": command_id, "result": result}
            else:
                outcome = {"type": "error", "commandId": command_id,
                           "error": {"stage": "cancelled",
                                     "message": "Cancelled before the result was saved."}}
        except CommandCancelled:
            outcome = {"type": "error", "commandId": command_id,
                       "error": {"stage": "cancelled", "message": "Cancelled."}}
        except PipelineError as e:
            logger.warning("command %s rejected at %s gate: %s", command_id, e.stage, e.message)
            error = {"stage": e.stage, "message": e.message}
            if getattr(e, "current", None) is not None:
                error["current"] = e.current
                error["expected"] = e.expected
            self.commands.fail(command_id, error)
            outcome = {"type": "error", "commandId": command_id, "error": error}
        except Exception:
            logger.exception("unhandled error in command %s", command_id)
            error = {"stage": "internal", "message": "Internal server error."}
            self.commands.fail(command_id, error)
            outcome = {"type": "error", "commandId": command_id, "error": error}
        finally:
            execution.publish(outcome)
            execution.close(outcome)
            with self._lock:
                self._live.pop(command_id, None)

    def cancel(self, command_id: str, owner: str) -> Optional[dict]:
        with self._lock:
            execution = self._live.get(command_id)
        if execution is not None:
            execution.cancel_requested.set()
            if execution.future is not None:
                execution.future.cancel()
        return self.commands.cancel(command_id, owner)

    def wait(self, execution: Execution, timeout: Optional[float] = None) -> dict:
        execution.done.wait(timeout)
        return execution.outcome or {"type": "error", "commandId": execution.id,
                                     "error": {"stage": "internal",
                                               "message": "The command did not finish."}}

    def status(self, command_id: str, owner: str) -> Optional[dict]:
        record = self.commands.get(command_id, owner)
        return None if record is None else self.commands.view(record)

    async def events(self, command_id: str, owner: str,
                     execution: Optional[Execution] = None):
        yield _frame({"type": "command", "commandId": command_id})
        if execution is None:
            with self._lock:
                execution = self._live.get(command_id)
        if execution is not None:
            queue = execution.subscribe()
            while True:
                event = await queue.get()
                if event is None:
                    return
                yield _frame(event)
                if event["type"] in ("result", "error"):
                    return

        record = self.commands.get(command_id, owner)
        if record is None:
            yield _frame({"type": "error", "commandId": command_id,
                          "error": {"stage": "command", "message": "No such command."}})
        elif record["status"] == "done":
            yield _frame({"type": "result", "commandId": command_id,
                          "result": record["result"]})
        elif record["status"] in TERMINAL:
            yield _frame({"type": "error", "commandId": command_id,
                          "error": record.get("error") or {"stage": record["status"],
                                                          "message": record["status"]}})
        else:
            yield _frame({"type": "status", "commandId": command_id,
                          "status": record["status"], "detached": True})

    def live(self) -> int:
        with self._lock:
            return len(self._live)

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


def _frame(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"
