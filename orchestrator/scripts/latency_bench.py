from __future__ import annotations

import argparse
import csv
import json
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

import env  # noqa: E402,F401  loads orchestrator/.env like the server does
from pipeline import CommandContext, PipelineError  # noqa: E402
from schema import Page  # noqa: E402
from tatl.config import SuiteConfig  # noqa: E402
from tatl.data import load  # noqa: E402
from tatl.suite import load_suites  # noqa: E402

OWNER = "tatl"


def scenarios(config: SuiteConfig, select: list[str]) -> list[tuple[str, object]]:
    registry = load_suites(config.path(config.suite_dir))
    root = config.path(config.data_dir)
    unique: dict[str, tuple[str, object]] = {}
    for case in registry.by_stage("outcome") + registry.by_stage("path"):
        if select and not any(part in case.name for part in select):
            continue
        spec = load(case.stage, case.data, root)
        unique.setdefault(spec.key(), (case.name, spec))
    return list(unique.values())


def intent_of(trace: dict) -> str | None:
    for step in trace.get("steps") or []:
        call = step.get("call") or {}
        result = step.get("result") or {}
        if call.get("tool") == "interpret" and isinstance(result, dict):
            return result.get("intent")
    return None


def run_one(adapter, name: str, spec, repeat: int) -> dict:
    db_name = f"vlp-latency-{repeat}"
    adapter._client.drop_database(db_name)
    services = adapter.services_for(db_name)
    phrasings = spec.phrasings()
    text = phrasings[repeat % len(phrasings)]
    try:
        page_id = None
        for page in spec.setup:
            doc = services.pages.create(Page(**page), OWNER)
            page_id = page_id or doc["_id"]
        ctx = CommandContext(page_id=page_id, owner=OWNER)
        started = time.perf_counter()
        try:
            result = services.command_service.execute(text, "en", ctx, keep_trace=True)
            seconds = time.perf_counter() - started
            trace = result.get("_trace") or {}
            plan = result.get("plan") or {}
            action = plan.get("action") or intent_of(trace)
            outcome = "clarification" if result.get("clarification") else "done"
        except PipelineError as e:
            seconds = time.perf_counter() - started
            trace = e.trace or {}
            action = intent_of(trace) or "rejected"
            outcome = f"rejected:{e.stage}"
    finally:
        services.command_service.close()
        adapter._client.drop_database(db_name)

    calls = ((trace.get("telemetry") or {}).get("total") or {})
    return {
        "case": name,
        "repeat": repeat,
        "text": text,
        "action": action,
        "outcome": outcome,
        "seconds": round(seconds, 2),
        "model_calls": calls.get("calls", 0),
        "retried": calls.get("retried_valid", 0),
        "exhausted": calls.get("exhausted", 0),
        "steps": len(trace.get("steps") or []),
    }


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    rank = q * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def summarise(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        key = row["action"] if row["outcome"] == "done" else row["outcome"]
        groups.setdefault(str(key), []).append(row)
    groups["all commands"] = rows

    def stats(items: list[dict]) -> dict:
        secs = [r["seconds"] for r in items]
        return {
            "n": len(secs),
            "median": round(statistics.median(secs), 1),
            "p90": round(percentile(secs, 0.9), 1),
            "max": round(max(secs), 1),
            "mean_model_calls": round(statistics.mean(r["model_calls"] for r in items), 1),
        }

    return {key: stats(items) for key, items in groups.items()}


def git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=HERE,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Time each suite command end to end")
    parser.add_argument("--repeats", type=int, default=3,
                        help="runs per scenario; repeat i uses phrasing i")
    parser.add_argument("-k", "--select", default=None,
                        help="only cases whose name contains one of these comma-separated substrings")
    parser.add_argument("--out", default="reports/latency")
    args = parser.parse_args()

    config = SuiteConfig.load(None, HERE)
    select = [p.strip() for p in (args.select or "").split(",") if p.strip()]
    todo = scenarios(config, select)
    if not todo:
        raise SystemExit("no scenarios selected")

    adapter = config.build_adapter()
    started_at = datetime.now(timezone.utc)
    rows: list[dict] = []
    total = len(todo) * args.repeats
    try:
        for repeat in range(args.repeats):
            for name, spec in todo:
                row = run_one(adapter, name, spec, repeat)
                rows.append(row)
                print(f"{len(rows):3d}/{total}  {row['seconds']:6.1f}s  "
                      f"{str(row['action']):18s} {row['outcome']:18s} {name}", flush=True)
    finally:
        adapter.close()

    summary = summarise(rows)
    slug = re.sub(r"[^A-Za-z0-9.]+", "-", adapter.name).strip("-")
    out = HERE / args.out
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "model": adapter.name,
        "started": started_at.isoformat(timespec="seconds"),
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": git_commit(),
        "host": f"{platform.system()} {platform.machine()} / Python {platform.python_version()}",
        "method": "sequential, one command at a time, in-process CommandService.execute; "
                  "setup pages and teardown excluded from timing",
        "repeats": args.repeats,
        "summary": summary,
        "commands": rows,
    }
    (out / f"latency-{slug}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    with (out / f"latency-{slug}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'action':22s} {'n':>4s} {'median':>8s} {'p90':>8s} {'max':>8s} {'calls':>6s}")
    for key, s in sorted(summary.items(), key=lambda kv: (kv[0] == "all commands", kv[0])):
        print(f"{key:22s} {s['n']:4d} {s['median']:7.1f}s {s['p90']:7.1f}s "
              f"{s['max']:7.1f}s {s['mean_model_calls']:6.1f}")
    print(f"\njson  {out / f'latency-{slug}.json'}\ncsv   {out / f'latency-{slug}.csv'}")


if __name__ == "__main__":
    main()
