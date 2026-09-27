from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import Column, SuiteConfig

TEMPLATES = Path(__file__).resolve().parent / "templates"

STOPS = [
    (0.00, (192, 57, 43)),
    (0.35, (232, 112, 26)),
    (0.60, (200, 150, 30)),
    (0.80, (111, 148, 64)),
    (1.00, (33, 150, 90)),
]

RESET = "\033[0m"


def _lerp(value: float) -> tuple[int, int, int]:
    value = max(0.0, min(1.0, value))
    for (lo, c_lo), (hi, c_hi) in zip(STOPS, STOPS[1:]):
        if value <= hi:
            span = hi - lo or 1.0
            t = (value - lo) / span
            return tuple(round(a + (b - a) * t) for a, b in zip(c_lo, c_hi))  # type: ignore
    return STOPS[-1][1]


def _score(column: Column, value) -> Optional[float]:
    if value is None or column.format == "count":
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str):
        return None
    lo, hi = (column.bad, column.good) if not column.inverted else (column.good, column.bad)
    if hi == lo:
        return 1.0 if value == hi else 0.0
    normalised = (value - lo) / (hi - lo)
    if column.inverted:
        normalised = 1.0 - normalised
    return max(0.0, min(1.0, normalised))


def _text(column: Column, value) -> str:
    if value is None:
        return "--"
    if column.format in ("ratio", "count"):
        return str(value)
    if column.format in ("flag", "text") or isinstance(value, bool):
        return ("ok" if value else "FAIL") if isinstance(value, bool) else str(value)
    return f"{value:.2f}" if isinstance(value, (int, float)) else str(value)


def _is_dataset(result) -> bool:
    return result.kind in ("classification", "extraction", "retrieval")


def matrix_rows(report) -> list[dict]:
    rows: dict[str, dict] = {}
    order: list[str] = []

    for result in report.results:
        row = rows.get(result.name)
        if row is None:
            row = {"task": result.name, "verdicts": [], "n": None}
            rows[result.name] = row
            order.append(result.name)
        row["verdicts"].append(result.passed or result.skipped)

        m = result.measurement
        if m is None:
            continue

        if result.kind == "outcome":
            row.update({"runs": f"{m.passes}/{m.runs}", "pass_k": m.pass_hat_k,
                        "k": m.k or m.runs})
        elif result.kind == "path":
            checks = [p for r in m.per_run for p in r.policy_results]
            row.update({
                "node_f1": m.node_f1,
                "edge_f1": m.edge_f1,
                "order": m.order_conformance,
                "redundancy": m.redundancy_ratio,
                "policies": (round(sum(1 for p in checks if p.passed) / len(checks), 4)
                             if checks else float(m.policies_passed)),
            })
        elif result.kind == "components":
            row.update({
                "intent": m.intent_accuracy,
                "slots": m.slot_accuracy,
                "sections": m.sections_accuracy,
                "image": m.image_recall,
                "n": m.phrasings,
            })
        elif result.kind == "classification":
            row.update({"intent": m.macro_f1, "n": m.total})
        elif result.kind == "extraction":
            row.update({"slots": m.slot_accuracy, "n": m.total})
        elif result.kind == "retrieval":
            row.update({"image": m.recall_at_k, "n": m.total})

    out = []
    for name in order:
        row = rows[name]
        row["ok"] = all(row.pop("verdicts"))
        out.append(row)
    return out


def dataset_rows(report) -> list[dict]:
    return [r for r in matrix_rows(report)
            if any(res.name == r["task"] and _is_dataset(res)
                   for res in report.results)]


def failure_details(result) -> list[str]:
    m = result.measurement
    if m is None:
        return []
    if result.kind == "outcome":
        return list(m.diffs[:4])
    if result.kind == "path":
        details = [f"missing operations: {', '.join(m.missing_ops)}"] if m.missing_ops else []
        return details + [f"policy: {p}" for p in m.policy_failures]
    if result.kind == "components":
        return list(m.errors[:5])
    out = []
    for err in getattr(m, "errors", [])[:5]:
        if "predicted" in err:
            out.append(f"{err['expected']} -> {err['predicted']}   {err['input'][:48]!r}")
        else:
            out.append(f"{err['slot']}: expected {err['expected']!r}, got {err.get('got')!r}")
    return out


def _is_count(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def telemetry_tables(telemetry: dict, prefix: str = "") -> list[dict]:
    tables: list[dict] = []
    for key, block in telemetry.items():
        if not isinstance(block, dict) or not block:
            continue
        title = f"{prefix}{key}"
        counts = {k: v for k, v in block.items() if _is_count(v)}
        nested = {k: v for k, v in block.items() if isinstance(v, dict) and v}
        rows = {k: v for k, v in nested.items() if all(_is_count(x) for x in v.values())}
        deeper = {k: v for k, v in nested.items() if k not in rows}
        if counts:
            tables.append({"title": title, "columns": list(counts),
                           "rows": [["", *counts.values()]]})
        if rows:
            columns = list(dict.fromkeys(c for inner in rows.values() for c in inner))
            tables.append({"title": title, "columns": columns,
                           "rows": [[label, *(inner.get(c, 0) for c in columns)]
                                    for label, inner in rows.items()]})
        tables += telemetry_tables(deeper, f"{title} / ")
    return tables


def _pass_k_label(report, fallback: str) -> str:
    ks = {row["k"] for row in matrix_rows(report) if row.get("k")}
    return fallback.replace("{k}", str(ks.pop()) if len(ks) == 1 else "k")


def build_view(report, config: SuiteConfig) -> dict:
    columns = config.matrix

    groups, seps, i = [], set(), 0
    while i < len(columns):
        group, span = columns[i].group, 1
        while i + span < len(columns) and columns[i + span].group == group:
            span += 1
        groups.append({"label": group, "span": span})
        if i:
            seps.add(i)
        i += span

    header = [{"label": _pass_k_label(report, c.label), "sep": idx in seps,
               "width": c.width}
              for idx, c in enumerate(columns)]

    rows = []
    for row in matrix_rows(report):
        cells = []
        for idx, column in enumerate(columns):
            value = row.get(column.key)
            score = _score(column, value)
            cells.append({
                "text": _text(column, value),
                "color": f"rgb{_lerp(score)}".replace(" ", "") if score is not None else None,
                "rgb": _lerp(score) if score is not None else None,
                "sep": idx in seps,
                "width": column.width,
            })
        rows.append({"name": row["task"], "ok": row["ok"], "cells": cells})

    failures = [{
        "name": r.name, "stage": r.stage, "error": r.error or "",
        "doc": r.doc, "details": failure_details(r),
    } for r in report.failures]

    return {
        "model": report.model,
        "seconds": report.seconds,
        "episodes": report.episodes_run,
        "passed": sum(1 for r in report.results if r.passed and not r.skipped),
        "failed": len(report.failures),
        "skipped": sum(1 for r in report.results if r.skipped),
        "groups": groups,
        "columns": header,
        "rows": rows,
        "failures": failures,
        "telemetry": telemetry_tables(report.telemetry),
    }


def render_terminal(report, config: SuiteConfig, name_width: int = 30) -> str:
    view = build_view(report, config)
    lines: list[str] = []

    band = " " * (name_width + 2)
    index = 0
    for group in view["groups"]:
        width = sum(view["columns"][index + n]["width"] + 1 for n in range(group["span"]))
        band += group["label"].center(width)
        index += group["span"]
    lines.append(band)

    header = "  " + "case".ljust(name_width)
    for column in view["columns"]:
        header += column["label"].center(column["width"]) + " "
    lines.append(header)
    lines.append("-" * len(header))

    for row in view["rows"]:
        line = ("  " if row["ok"] else "✗ ") + row["name"][:name_width - 1].ljust(name_width)
        for cell in row["cells"]:
            label = cell["text"].center(cell["width"])
            if cell["rgb"] is None:
                line += label + " "
            else:
                r, g, b = cell["rgb"]
                line += f"\033[48;2;{r};{g};{b}m\033[97m{label}{RESET} "
        lines.append(line)

    return "\n".join(lines)


def render_summary(report, config: SuiteConfig) -> str:
    view = build_view(report, config)
    parts = [
        "",
        "=" * 78,
        f"THREE-LEVEL SUITE -- {view['model']}   "
        f"{view['episodes']} episodes   {view['seconds']}s",
        "=" * 78,
        render_terminal(report, config),
        "",
        f"{view['passed']} passed, {view['failed']} failed"
        + (f", {view['skipped']} skipped" if view["skipped"] else "")
        + f"   ({len(view['rows'])} cases)",
    ]

    if view["failures"]:
        parts += ["", "FAILURES", "-" * 78]
        for failure in view["failures"]:
            parts.append(f"{failure['name']} ({failure['stage']}): {failure['error']}")
            parts += [f"    {d}" for d in failure["details"]]

    if view["telemetry"]:
        parts += ["", "TELEMETRY", "-" * 78]
        for table in view["telemetry"]:
            parts += [table["title"]] + _table_lines(table)
    return "\n".join(parts)


def _table_lines(table: dict, label_width: int = 24) -> list[str]:
    widths = [max(len(c), *(len(str(row[i + 1])) for row in table["rows"]))
              for i, c in enumerate(table["columns"])]
    header = " " * label_width + "  ".join(c.rjust(w) for c, w in zip(table["columns"], widths))
    body = [str(row[0])[:label_width - 1].ljust(label_width)
            + "  ".join(str(v).rjust(w) for v, w in zip(row[1:], widths))
            for row in table["rows"]]
    return [f"    {line}" for line in [header, *body]]


@lru_cache(maxsize=1)
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_html(report, config: SuiteConfig) -> str:
    view = build_view(report, config)
    view["css"] = (TEMPLATES / "report.css").read_text(encoding="utf-8")
    return _environment().get_template("report.html.j2").render(**view)
