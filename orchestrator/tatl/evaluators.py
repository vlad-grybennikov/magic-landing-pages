from __future__ import annotations

import json
import re
from math import comb
from typing import Callable, Optional

from pydantic import BaseModel, Field

from .annotations import (
    DependencyGraph,
    GoalState,
    IntentCase,
    PolicyAssertion,
    Projection,
    TaskAnnotation,
)


class OutcomeCheck(BaseModel):
    passed: bool
    diffs: list[str] = Field(default_factory=list)


MATCHERS = ("$changed", "$contains", "$between", "$startswith", "$endswith")


def _contains(got, needle) -> bool:
    return isinstance(got, (str, list)) and needle in got


def _edge(got, want, start: bool) -> bool:
    if isinstance(got, str):
        return got.startswith(want) if start else got.endswith(want)
    if isinstance(got, list):
        want = want if isinstance(want, list) else [want]
        return (got[:len(want)] if start else got[len(got) - len(want):]) == want
    return False


def matches(expected, got, initial=None) -> bool:
    if not isinstance(expected, dict) or not any(k in MATCHERS for k in expected):
        return got == expected
    for key, want in expected.items():
        if key == "$changed":
            if (got != initial) != bool(want):
                return False
        elif key == "$contains":
            if not all(_contains(got, n) for n in (want if isinstance(want, list) else [want])):
                return False
        elif key == "$between":
            size = got if isinstance(got, (int, float)) else len(got or [])
            if not want[0] <= size <= want[1]:
                return False
        elif key in ("$startswith", "$endswith"):
            if not _edge(got, want, key == "$startswith"):
                return False
    return True


def evaluate_outcome(trace: dict, goal: GoalState,
                    projection: Projection) -> OutcomeCheck:
    initial = projection.apply(trace["initial_snapshot"])
    actual = projection.apply(trace["final_snapshot"])

    expected = {t: {rid: dict(row) for rid, row in rows.items()}
                for t, rows in initial.items()}
    diffs: list[str] = []

    for table, rows in goal.expected.items():
        for row_id, patch in rows.items():
            if table not in expected or row_id not in expected[table]:
                diffs.append(f"goal references unknown row {table}/{row_id}")
                continue
            expected[table][row_id].update(patch)

    for table, rows in goal.created.items():
        for row_id, patch in rows.items():
            expected.setdefault(table, {})[row_id] = patch

    for table, exp_rows in expected.items():
        act_rows = actual.get(table, {})
        for row_id, exp_row in exp_rows.items():
            if row_id not in act_rows:
                diffs.append(f"{table}/{row_id}: row missing in final state")
                continue
            for col, exp_val in exp_row.items():
                got = act_rows[row_id].get(col)
                before = initial.get(table, {}).get(row_id, {}).get(col)
                if not matches(exp_val, got, before):
                    diffs.append(
                        f"{table}/{row_id}.{col}: expected {exp_val!r}, got {got!r}"
                    )
        for row_id in act_rows:
            if row_id not in exp_rows:
                diffs.append(f"{table}/{row_id}: unexpected new row")

    return OutcomeCheck(passed=not diffs, diffs=diffs)


def pass_hat_k(n: int, c: int, k: int) -> float:
    if k > n:
        raise ValueError("k cannot exceed the number of runs")
    if c < k:
        return 0.0
    return comb(c, k) / comb(n, k)


class PolicyResult(BaseModel):
    assertion: PolicyAssertion
    passed: bool
    detail: str


class PathCheck(BaseModel):
    node_precision: float
    node_recall: float
    node_f1: float
    edge_precision: float
    edge_recall: float
    edge_f1: float
    order_conformance: float
    redundancy_ratio: float
    observed_ops: list[str]
    missing_ops: list[str]
    policy_results: list[PolicyResult]

    @property
    def policies_passed(self) -> bool:
        return all(p.passed for p in self.policy_results)


def _successful_calls(trace: dict) -> list[dict]:
    return [
        s for s in trace["steps"]
        if s.get("call") and s.get("error") is None
    ]


def _scalars(obj) -> set:
    out: set = set()

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str) and len(x) >= 3:
            out.add(x)
        elif isinstance(x, int) and not isinstance(x, bool) and abs(x) >= 10:
            out.add(x)

    walk(obj)
    return out


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def evaluate_path(trace: dict, dep: DependencyGraph,
                    policies: list[PolicyAssertion]) -> PathCheck:
    calls = _successful_calls(trace)
    observed_tools = [c["call"]["tool"] for c in calls]
    observed_set = set(observed_tools)

    def op_matched(spec) -> bool:
        for c in calls:
            if c["call"]["tool"] != spec.tool:
                continue
            args = c["call"]["args"]
            if all(args.get(k) == v for k, v in spec.args_include.items()):
                return True
        return False

    required = dep.required_ops
    matched = [spec for spec in required if op_matched(spec)]
    required_tools = {spec.tool for spec in required}
    node_recall = len(matched) / len(required) if required else 1.0
    node_precision = (
        len(observed_set & required_tools) / len(observed_set)
        if observed_set else 1.0
    )

    inferred: set[tuple[str, str]] = set()
    producer: dict = {}
    for c in calls:
        tool = c["call"]["tool"]
        for value in _scalars(c["call"]["args"]):
            if value in producer:
                inferred.add((producer[value], tool))
        for value in _scalars(c.get("result")):
            producer.setdefault(value, tool)
    declared = {(e.source, e.target) for e in dep.edges}
    edge_recall = len(inferred & declared) / len(declared) if declared else 1.0
    edge_precision = len(inferred & declared) / len(inferred) if inferred else 1.0

    def first_index(tool: str) -> Optional[int]:
        for idx, c in enumerate(calls):
            if c["call"]["tool"] == tool:
                return idx
        return None

    satisfied = 0
    for pair in dep.ordering:
        a, b = first_index(pair.source), first_index(pair.target)
        if a is not None and b is not None and a < b:
            satisfied += 1
    order_conformance = satisfied / len(dep.ordering) if dep.ordering else 1.0

    seen: set[str] = set()
    duplicates = 0
    for c in calls:
        key = c["call"]["tool"] + json.dumps(c["call"]["args"], sort_keys=True)
        if key in seen:
            duplicates += 1
        seen.add(key)
    redundancy_ratio = round(duplicates / len(calls), 4) if calls else 0.0

    policy_results = []
    for assertion in policies:
        if assertion.kind == "require_before":
            then_idxs = [i for i, c in enumerate(calls)
                         if c["call"]["tool"] == assertion.then]
            first_idxs = [i for i, c in enumerate(calls)
                          if c["call"]["tool"] == assertion.first]
            bad = [i for i in then_idxs
                   if not any(j < i for j in first_idxs)]
            passed = not bad
            detail = ("ok" if passed else
                      f"{assertion.then} executed without prior {assertion.first}")
        else:
            passed = assertion.tool not in observed_set
            detail = "ok" if passed else f"{assertion.tool} was executed"
        policy_results.append(PolicyResult(
            assertion=assertion, passed=passed, detail=detail))

    return PathCheck(
        node_precision=round(node_precision, 4),
        node_recall=round(node_recall, 4),
        node_f1=_f1(node_precision, node_recall),
        edge_precision=round(edge_precision, 4),
        edge_recall=round(edge_recall, 4),
        edge_f1=_f1(edge_precision, edge_recall),
        order_conformance=round(order_conformance, 4),
        redundancy_ratio=redundancy_ratio,
        observed_ops=observed_tools,
        missing_ops=[s.tool for s in required if s not in matched],
        policy_results=policy_results,
    )


FILLER = frozenset("a an the to for of on in so can with and that this their them they".split())


def _stems(text: str) -> set[str]:
    return {word[:5] for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in FILLER}


def _slot_match(got, expected) -> bool:
    if isinstance(expected, dict) and "$any" in expected:
        return any(_slot_match(got, option) for option in expected["$any"])
    if got is None:
        return False
    if isinstance(expected, str) and isinstance(got, str):
        a = "".join(ch for ch in got.lower() if ch.isalnum())
        b = "".join(ch for ch in expected.lower() if ch.isalnum())
        if a == b or a in b or b in a:
            return True
        sa, sb = _stems(got), _stems(expected)
        return len(sa) > 1 and len(sb) > 1 and len(sa & sb) / len(sa | sb) >= 0.5
    return got == expected


class ClassMetrics(BaseModel):
    precision: float
    recall: float
    f1: float
    support: int


class ClassificationScore(BaseModel):
    accuracy: float
    macro_f1: float
    per_class: dict[str, ClassMetrics] = Field(default_factory=dict)
    errors: list[dict] = Field(default_factory=list)
    total: int = 0


def score_classification(inputs: list[str], expected: list, predicted: list
                         ) -> ClassificationScore:
    labels = sorted({e for e in expected})
    per_class: dict[str, ClassMetrics] = {}
    f1s = []
    for label in labels:
        tp = sum(1 for e, p in zip(expected, predicted) if e == label and p == label)
        fp = sum(1 for e, p in zip(expected, predicted) if e != label and p == label)
        fn = sum(1 for e, p in zip(expected, predicted) if e == label and p != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0.0)
        per_class[label] = ClassMetrics(
            precision=round(precision, 4), recall=round(recall, 4),
            f1=round(f1, 4), support=tp + fn)
        f1s.append(f1)

    n = len(expected) or 1
    return ClassificationScore(
        total=len(expected),
        accuracy=round(sum(1 for e, p in zip(expected, predicted) if e == p) / n, 4),
        macro_f1=round(sum(f1s) / len(f1s), 4) if f1s else 0.0,
        per_class=per_class,
        errors=[{"input": i, "expected": e, "predicted": p}
                for i, e, p in zip(inputs, expected, predicted) if e != p],
    )


class ExtractionScore(BaseModel):
    slot_accuracy: float
    per_slot: dict[str, float] = Field(default_factory=dict)
    errors: list[dict] = Field(default_factory=list)
    total: int = 0


def score_extraction(inputs: list[str], expected: list[dict], produced: list[dict]
                     ) -> ExtractionScore:
    hits: dict[str, list[bool]] = {}
    errors = []
    for text, want, got in zip(inputs, expected, produced):
        got = got or {}
        for slot, value in (want or {}).items():
            ok = _slot_match(got.get(slot), value)
            hits.setdefault(slot, []).append(ok)
            if not ok:
                errors.append({"input": text, "slot": slot,
                               "expected": value, "got": got.get(slot)})
    flat = [ok for values in hits.values() for ok in values]
    return ExtractionScore(
        total=len(inputs),
        slot_accuracy=round(sum(flat) / len(flat), 4) if flat else 1.0,
        per_slot={k: round(sum(v) / len(v), 4) for k, v in hits.items()},
        errors=errors,
    )


class RetrievalScore(BaseModel):
    recall_at_k: float
    hits: int = 0
    total: int = 0
    misses: list[dict] = Field(default_factory=list)


def score_retrieval(inputs: list[str], expected: list[str],
                    rankings: list[Optional[list[str]]]) -> RetrievalScore:
    hits, misses = 0, []
    for text, want, ranked in zip(inputs, expected, rankings):
        ranked = ranked or []
        if want in ranked:
            hits += 1
        else:
            misses.append({"input": text, "expected": want, "ranked": ranked[:5]})
    n = len(inputs) or 1
    return RetrievalScore(total=len(inputs), hits=hits,
                          recall_at_k=round(hits / n, 4) if inputs else 1.0,
                          misses=misses)
