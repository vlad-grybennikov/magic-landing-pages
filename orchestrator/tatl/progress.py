from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Optional


class Progress:
    def __init__(self, path: Optional[Path] = None, model: str = "", total_episodes: int = 0):
        self.path = path
        self.model = model
        self.started = time.time()
        self.total_episodes = total_episodes
        self.episodes_done = 0
        self.stage = "starting"
        self.events: list[dict] = []
        self.results: list[dict] = []
        self.finished = False
        self._lock = threading.Lock()
        self.publish()

    def log(self, message: str, level: str = "info") -> None:
        with self._lock:
            self.events.append({
                "at": round(time.time() - self.started, 1),
                "level": level,
                "message": message,
            })
            del self.events[:-400]
        self.publish()

    def set_stage(self, stage: str, total_episodes: Optional[int] = None) -> None:
        with self._lock:
            self.stage = stage
            if total_episodes is not None:
                self.total_episodes = total_episodes
        self.log(stage)

    def episode_done(self, label: str = "") -> None:
        with self._lock:
            self.episodes_done += 1
            done, total = self.episodes_done, self.total_episodes
        self.log(f"episode {done}/{total}{f'  {label}' if label else ''}")

    def case_done(self, name: str, stage: str, passed: bool, detail: str = "") -> None:
        with self._lock:
            self.results.append({"name": name, "stage": stage,
                                 "passed": passed, "detail": detail})
        self.log(f"{'PASS' if passed else 'FAIL'}  {name} ({stage})"
                 + (f" -- {detail}" if detail else ""),
                 level="info" if passed else "error")

    def done(self) -> None:
        with self._lock:
            self.finished = True
            self.stage = "finished"
        self.log("run finished")

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "model": self.model,
                "stage": self.stage,
                "seconds": round(time.time() - self.started, 1),
                "episodes_done": self.episodes_done,
                "episodes_total": self.total_episodes,
                "finished": self.finished,
                "passed": sum(1 for r in self.results if r["passed"]),
                "failed": sum(1 for r in self.results if not r["passed"]),
                "results": list(self.results),
                "events": list(self.events),
            }

    def publish(self) -> None:
        if self.path is None:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(self.snapshot()), encoding="utf-8")
            os.replace(temp, self.path)
        except OSError:
            pass


def serve(directory: Path, port: int) -> str:
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class Quiet(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Quiet)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}/live.html"
