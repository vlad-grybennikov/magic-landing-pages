from __future__ import annotations

import contextvars
from dataclasses import dataclass, field

COUNTERS = ("calls", "first_attempt_valid", "retried_valid", "exhausted")


def _outcome(attempts: int, ok: bool) -> str:
    if not ok:
        return "exhausted"
    return "first_attempt_valid" if attempts == 1 else "retried_valid"


@dataclass
class ModelCalls:
    calls: list[dict] = field(default_factory=list)

    def record(self, stage: str, attempts: int, ok: bool) -> None:
        self.calls.append({"stage": stage, "attempts": attempts, "ok": ok})

    def summary(self) -> dict:
        total = dict.fromkeys(COUNTERS, 0)
        by_stage: dict[str, dict] = {}
        for call in self.calls:
            stage = by_stage.setdefault(call["stage"], dict.fromkeys(COUNTERS, 0))
            for counters in (total, stage):
                counters["calls"] += 1
                counters[_outcome(call["attempts"], call["ok"])] += 1
        return {"total": total, "by_stage": by_stage}


_current: contextvars.ContextVar[ModelCalls | None] = contextvars.ContextVar(
    "model_calls", default=None)


def start() -> ModelCalls:
    calls = ModelCalls()
    _current.set(calls)
    return calls


def current() -> ModelCalls | None:
    return _current.get()


def record(stage: str, attempts: int, ok: bool) -> None:
    calls = _current.get()
    if calls is not None:
        calls.record(stage, attempts, ok)
