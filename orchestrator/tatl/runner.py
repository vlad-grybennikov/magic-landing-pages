from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .adapter import AgentAdapter
from .config import SuiteConfig
from .data import OutcomeData, PathData, ComponentData, DatasetData, load
from .evaluators import (
    OutcomeCheck,
    PathCheck,
    _slot_match,
    evaluate_outcome,
    evaluate_path,
    matches,
    pass_hat_k,
    score_classification,
    score_extraction,
    score_retrieval,
)
from .progress import Progress, serve
from .report import render_html, render_summary
from .results import (
    CaseResult,
    ClassLabelMetrics,
    Classification,
    Components,
    Extraction,
    Outcome,
    Path as PathResult,
    Retrieval,
)
from .suite import STAGES, Case, Registry, load_suites

HERE = Path(__file__).resolve().parent.parent


class SuiteReport(BaseModel):
    model: str
    seconds: float
    results: list[CaseResult] = Field(default_factory=list)
    episodes_run: int = 0
    telemetry: dict = Field(default_factory=dict)

    @property
    def failures(self) -> list[CaseResult]:
        return [r for r in self.results if not r.passed and not r.skipped]

    def measurement(self, stage: str, name: str):
        for r in self.results:
            if r.stage == stage and r.name == name:
                return r.measurement
        return None


class EpisodePool:
    def __init__(self, adapter: AgentAdapter, workers: int, progress=None):
        self.adapter = adapter
        self.workers = workers
        self.progress = progress
        self._cache: dict[tuple[str, int], list] = {}
        self.count = 0
        self.model_calls: dict = {}
        self.step_status: dict[str, int] = {}
        self.defaulted_by_tool: dict[str, int] = {}

    def collect(self, trace: dict) -> None:
        _add_counts(self.model_calls, trace.get("telemetry") or {})
        for step in trace.get("steps", []):
            status = _step_status(step.get("result"))
            if status is None:
                continue
            self.step_status[status] = self.step_status.get(status, 0) + 1
            tool = step.get("call", {}).get("tool")
            if status == "defaulted" and tool:
                self.defaulted_by_tool[tool] = self.defaulted_by_tool.get(tool, 0) + 1

    def telemetry(self) -> dict:
        return {
            "episodes": self.count,
            "model_calls": self.model_calls,
            "step_status": self.step_status,
            "defaulted_by_tool": self.defaulted_by_tool,
        }

    def plan(self, requests: list[tuple[str, object, int]]) -> None:
        jobs = []
        for key, scenario, k in requests:
            for i in range(k):
                if (key, i) not in self._cache:
                    self._cache[(key, i)] = []
                    jobs.append((key, scenario, i))
        if not jobs:
            return

        def execute(job):
            key, scenario, index = job
            phrasings = scenario.phrasings()
            task = _as_task(scenario, f"{abs(hash(key)) % 10**8}",
                            phrasings[index % len(phrasings)])
            return key, index, self.adapter.run_episode(task, index)

        if self.progress:
            self.progress.set_stage("running episodes", total_episodes=len(jobs))
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for key, index, outcome in pool.map(execute, jobs):
                self._cache[(key, index)] = outcome
                self.collect(outcome.trace)
                if self.progress:
                    self.progress.episode_done(
                        f"rejected at {outcome.rejected_at} gate"
                        if outcome.rejected_at else "")
        self.count += len(jobs)

    def get(self, key: str, k: int) -> list:
        return [self._cache[(key, i)] for i in range(k) if (key, i) in self._cache]


def _step_status(result) -> Optional[str]:
    if isinstance(result, dict):
        result = result.get("status")
    return result if isinstance(result, str) else None


def _add_counts(into: dict, counts: dict) -> None:
    for key, value in counts.items():
        if isinstance(value, dict):
            _add_counts(into.setdefault(key, {}), value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            into[key] = into.get(key, 0) + value


def _as_task(scenario, ident: str, instruction: str | None = None):
    from .annotations import TaskAnnotation

    return TaskAnnotation(
        id=f"case-{ident}",
        capability="case",
        instruction=instruction or scenario.instruction,
        setup_pages=scenario.setup,
    )


def grade_outcome(case: Case, spec: OutcomeData, outcomes) -> Outcome:
    goal = spec.expect.to_goal()
    projection = spec.projection()
    per_run: list[OutcomeCheck] = []
    rejected: Optional[str] = None
    for episode in outcomes:
        per_run.append(evaluate_outcome(episode.trace, goal, projection))
        rejected = rejected or episode.rejected_at

    passes = sum(1 for r in per_run if r.passed)
    runs = len(per_run) or 1
    first_failure = next((r.diffs for r in per_run if not r.passed), [])
    k = min(case.k, len(per_run)) or len(per_run)
    return Outcome(
        name=case.name, runs=len(per_run), k=k, passes=passes,
        pass_rate=round(passes / runs, 4),
        pass_hat_k=round(pass_hat_k(len(per_run), passes, k), 4) if per_run else 0.0,
        diffs=first_failure, rejected_at=rejected, per_run=per_run,
    )


def grade_path(case: Case, spec: PathData, outcomes) -> PathResult:
    dependency = spec.to_dependency()
    policies = spec.to_policies()
    per_run: list[PathCheck] = [
        evaluate_path(e.trace, dependency, policies) for e in outcomes]
    n = len(per_run) or 1

    def mean(fn):
        return round(sum(fn(r) for r in per_run) / n, 4) if per_run else 0.0

    failures = [p.detail for r in per_run for p in r.policy_results if not p.passed]
    return PathResult(
        name=case.name, runs=len(per_run),
        node_f1=mean(lambda r: r.node_f1),
        node_precision=mean(lambda r: r.node_precision),
        node_recall=mean(lambda r: r.node_recall),
        edge_f1=mean(lambda r: r.edge_f1),
        order_conformance=mean(lambda r: r.order_conformance),
        redundancy_ratio=mean(lambda r: r.redundancy_ratio),
        policies_passed=all(r.policies_passed for r in per_run),
        missing_ops=sorted({op for r in per_run for op in r.missing_ops}),
        observed_ops=per_run[0].observed_ops if per_run else [],
        policy_failures=sorted(set(failures)),
        per_run=per_run,
    )


def _normalise(output):
    if isinstance(output, tuple):
        return output
    if isinstance(output, list):
        return ",".join(str(v) for v in output), {}
    return output, {}


def _probe(fn, *args):
    try:
        return fn(*args), None
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {str(e)[:120]}"


def grade_components(case: Case, spec: ComponentData, probes) -> Components:
    expect = spec.expect
    phrasings = spec.phrasings()
    errors: list[str] = []

    intents: list[str] = []
    slot_hits: dict[str, list[bool]] = {}
    section_hits: list[bool] = []
    image_hits: list[bool] = []

    for text in phrasings:
        output, failure = _probe(probes.classify, text)
        if failure:
            errors.append(f"classify failed: {failure} for {text[:40]!r}")
        predicted, args = _normalise(output)
        predicted = predicted or ""
        intents.append(predicted)
        if expect.intent is not None and predicted != expect.intent:
            errors.append(f"intent: expected {expect.intent!r}, got {predicted!r} "
                          f"for {text[:40]!r}")

        for slot, value in spec.expected_slots(text).items():
            ok = _slot_match(args.get(slot), value)
            slot_hits.setdefault(slot, []).append(ok)
            if not ok:
                errors.append(f"slot {slot}: expected {value!r}, got {args.get(slot)!r} "
                              f"for {text[:40]!r}")

        if expect.sections is not None:
            planned, failure = _probe(probes.plan_sections, dict(expect.slots or {}), text)
            if failure:
                errors.append(f"plan_sections failed: {failure} for {text[:40]!r}")
            ok = matches(expect.sections, planned)
            section_hits.append(ok)
            if not ok:
                errors.append(f"sections: expected {expect.sections}, got {planned} "
                              f"for {text[:40]!r}")

        if expect.image is not None:
            ranked = _probe(probes.rank_categories, text, case.image_k)[0] or []
            ok = expect.image in ranked
            image_hits.append(ok)
            if not ok:
                errors.append(f"image: {expect.image!r} not in top {case.image_k} "
                              f"({', '.join(ranked[:3])}) for {text[:40]!r}")

    def rate(hits):
        return round(sum(hits) / len(hits), 4) if hits else None

    correct = [i == expect.intent for i in intents] if expect.intent else []
    flat = [ok for values in slot_hits.values() for ok in values]

    return Components(
        name=case.name,
        phrasings=len(phrasings),
        intent_accuracy=rate(correct),
        slot_accuracy=rate(flat),
        sections_accuracy=rate(section_hits),
        image_recall=rate(image_hits),
        per_slot={k: round(sum(v) / len(v), 4) for k, v in slot_hits.items()},
        predicted_intents=intents,
        errors=errors,
    )


def _normalise(output):
    if isinstance(output, tuple):
        return output
    if isinstance(output, list):
        return ",".join(str(v) for v in output), {}
    return output, {}


def grade_dataset(case: Case, spec: DatasetData, probes, workers: int):
    cases = spec.reviewed_cases()
    if not cases:
        return None

    if spec.probe == "classify":
        call = lambda c: probes.classify(c.input)  # noqa: E731
    elif spec.probe == "plan_sections":
        call = lambda c: probes.plan_sections({}, c.input)  # noqa: E731
    elif spec.probe == "rank_categories":
        call = lambda c: probes.rank_categories(c.input, case.image_k)  # noqa: E731
    else:
        call = lambda c: probes.rank_images(c.input, case.image_k)  # noqa: E731

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outputs = [output for output, _ in pool.map(lambda c: _probe(call, c), cases)]

    if all(o is None for o in outputs):
        return None

    inputs = [c.input for c in cases]
    expected = [c.expect for c in cases]

    if case.kind == "classification":
        predicted = [_normalise(o)[0] for o in outputs]
        score = score_classification(inputs, expected, predicted)
        return Classification(
            name=case.name, accuracy=score.accuracy, macro_f1=score.macro_f1,
            per_class={k: ClassLabelMetrics(**v.model_dump())
                       for k, v in score.per_class.items()},
            errors=score.errors, total=score.total)

    if case.kind == "extraction":
        produced = [_normalise(o)[1] for o in outputs]
        score = score_extraction(inputs, expected, produced)
        return Extraction(
            name=case.name, slot_accuracy=score.slot_accuracy,
            per_slot=score.per_slot, errors=score.errors, total=score.total)

    score = score_retrieval(inputs, expected, outputs)
    return Retrieval(name=case.name, k=case.image_k, total=score.total,
                     hits=score.hits, recall_at_k=score.recall_at_k,
                     misses=score.misses)


def _verdict(case: Case, measurement, stage: str, progress=None) -> CaseResult:
    result = CaseResult(name=case.name, stage=stage, kind=case.kind,
                        doc=case.doc, measurement=measurement)
    if measurement is None:
        result.skipped = True
        return result
    try:
        case.fn(measurement)
    except AssertionError as e:
        result.passed = False
        result.error = str(e) or "assertion failed"
    except Exception as e:  # noqa: BLE001
        result.passed = False
        result.error = f"{type(e).__name__}: {e}"
    _stream(result)
    if progress:
        progress.case_done(case.name, stage, result.passed, (result.error or "")[:160])
    return result


_GREEN, _RED, _DIM, _OFF = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def _stream(result: CaseResult) -> None:
    if result.skipped:
        mark, colour = "SKIP", _DIM
    elif result.passed:
        mark, colour = "PASS", _GREEN
    else:
        mark, colour = "FAIL", _RED
    line = f"{colour}{mark}{_OFF}  {result.name} {_DIM}({result.stage}){_OFF}"
    if not result.passed and not result.skipped:
        line += f"\n      {_RED}{(result.error or '')[:150]}{_OFF}"
    print(line, flush=True)


def run_suite(config: SuiteConfig, adapter: AgentAdapter,
              registry: Registry, progress=None) -> SuiteReport:
    started = time.perf_counter()
    root = config.path(config.data_dir)
    results: list[CaseResult] = []

    specs: dict[tuple[int, str], object] = {}
    requests: list[tuple[str, object, int]] = []
    for case in registry.by_stage("outcome") + registry.by_stage("path"):
        spec = load(case.stage, case.data, root)
        specs[(case.stage, case.name)] = spec
        requests.append((spec.key(), spec, case.episodes))

    pool = EpisodePool(adapter, config.workers, progress)
    pool.plan(requests)

    for case in registry.by_stage("outcome"):
        spec = specs[("outcome", case.name)]
        results.append(_verdict(case, grade_outcome(case, spec, pool.get(spec.key(), case.episodes)), "outcome", progress))

    for case in registry.by_stage("path"):
        spec = specs[("path", case.name)]
        results.append(_verdict(case, grade_path(case, spec, pool.get(spec.key(), case.episodes)), "path", progress))

    if progress:
        progress.set_stage("probing components")
    probes = adapter.probes()
    for case in registry.by_stage("component"):
        if case.kind == "components":
            spec = load("components", case.data, root)
            measurement = grade_components(case, spec, probes)
        else:
            spec = load("component", case.data, root)
            measurement = grade_dataset(case, spec, probes, config.workers)
        results.append(_verdict(case, measurement, "component", progress))

    return SuiteReport(
        model=adapter.name,
        seconds=round(time.perf_counter() - started, 1),
        results=results,
        episodes_run=pool.count,
        telemetry=pool.telemetry(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="tatl", description="Run the three-level suite")
    parser.add_argument("--config", default=None, help="suite config JSON")
    parser.add_argument("--suite", default=None, help="directory of suite modules")
    parser.add_argument("--workers", type=int, default=None, help="concurrent episodes")
    parser.add_argument("--adapter", default=None, help="module:Class under test")
    parser.add_argument("--name", default=None, help="label for this run in reports")
    parser.add_argument("-k", "--select", default=None,
                        help="only cases whose name contains one of these comma-separated substrings")
    parser.add_argument("--stage", default=None, choices=STAGES,
                        help="only cases from this stage")
    parser.add_argument("--out", default=None, help="output directory")
    parser.add_argument("--no-html", action="store_true")
    parser.add_argument("--serve", nargs="?", type=int, const=8900, default=None,
                        metavar="PORT",
                        help="stream live progress to a local page while running")
    parser.add_argument("--render", default=None, metavar="REPORT.JSON",
                        help="re-render a saved report without re-running it")
    args = parser.parse_args()

    config = SuiteConfig.load(args.config, HERE)

    if args.render:
        saved = SuiteReport.model_validate_json(Path(args.render).read_text(encoding="utf-8"))
        print(render_summary(saved, config))
        target = Path(args.render).with_suffix(".html")
        target.write_text(render_html(saved, config), encoding="utf-8")
        print(f"\nhtml  {target}")
        return
    for attr, value in (("suite_dir", args.suite), ("workers", args.workers),
                        ("adapter", args.adapter), ("out_dir", args.out)):
        if value is not None:
            setattr(config, attr, value)

    registry = load_suites(config.path(config.suite_dir))
    if args.select:
        wanted = [part.strip() for part in args.select.split(",") if part.strip()]
        registry.cases = [c for c in registry.cases if any(part in c.name for part in wanted)]
    if args.stage:
        registry.cases = [c for c in registry.cases if c.stage == args.stage]
    if not registry.cases:
        raise SystemExit("no cases selected")

    out_dir = config.path(config.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    adapter = config.build_adapter(**({"name": args.name} if args.name else {}))
    progress = None
    if args.serve is not None:
        import shutil
        shutil.copy(Path(__file__).resolve().parent / "templates" / "live.html",
                    out_dir / "live.html")
        progress = Progress(out_dir / "live.json", adapter.name)
        print(f"live  {serve(out_dir, args.serve)}\n")

    try:
        report = run_suite(config, adapter, registry, progress)
    finally:
        if progress:
            progress.done()
        adapter.close()

    print(render_summary(report, config))

    slug = report.model.replace(":", "-").replace("/", "-")
    if args.select or args.stage:
        slug += "-partial"
    (out_dir / f"report-{slug}.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8")
    print(f"\njson  {out_dir / f'report-{slug}.json'}")
    if not args.no_html:
        (out_dir / f"report-{slug}.html").write_text(
            render_html(report, config), encoding="utf-8")
        print(f"html  {out_dir / f'report-{slug}.html'}")

    raise SystemExit(1 if report.failures else 0)


if __name__ == "__main__":
    main()
