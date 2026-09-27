import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tatl import SuiteConfig, component, load_suites, outcome, path
from tatl.data import OutcomeData, PathData, DatasetData, load
from tatl.evaluators import score_classification, score_extraction, score_retrieval
from tatl.report import dataset_rows, matrix_rows, render_html, render_summary
from tatl.results import (
    CaseResult,
    Classification,
    Components,
    Extraction,
    Outcome,
    Path as PathResult,
    Retrieval,
)
from tatl.runner import SuiteReport, _verdict, grade_dataset
from tatl.suite import REGISTRY, STAGES, Case, Registry

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "test_data"


def test_level1_data_converts_to_goal_state():
    spec = load("outcome", "outcome/create_page_collision.json", DATA)
    goal = spec.expect.to_goal()
    assert "/maria-s-bakery-2" in goal.created["pages"]
    assert goal.expected["pages"]["/maria-s-bakery"]["n_sections"] == 1
    assert spec.setup and spec.instruction


def test_level1_empty_expectation_means_untouched():
    spec = load("outcome", "outcome/reject_unsupported_intent.json", DATA)
    goal = spec.expect.to_goal()
    assert goal.created == {} and goal.expected == {}
    assert spec.expect_rejection == "intent"


def test_level2_data_converts_to_dependency_and_policies():
    spec = load("path", "path/create_page_default.json", DATA)
    dep = spec.to_dependency()
    assert {op.tool for op in dep.required_ops} >= {"interpret", "assemble_page", "save_draft"}
    assert ("assemble_page", "save_draft") in {(e.source, e.target) for e in dep.ordering}

    policies = spec.to_policies()
    assert any(p.kind == "require_before" and p.first == "assemble_page"
               and p.then == "save_draft" for p in policies)


def test_level2_where_clause_survives_conversion():
    spec = load("path", "path/create_page_collision.json", DATA)
    save = next(op for op in spec.to_dependency().required_ops if op.tool == "save_draft")
    assert save.args_include == {"url": "/maria-s-bakery-2"}


def test_forbid_policy_converts():
    spec = load("path", "path/reject_unsupported_intent.json", DATA)
    forbidden = {p.tool for p in spec.to_policies() if p.kind == "forbid_call"}
    assert forbidden == {"generate_copy", "assemble_page", "save_draft"}


def test_scenario_key_identifies_identical_runs():
    a = OutcomeData(instruction="do it", setup=[])
    b = PathData(instruction="do it", setup=[])
    c = OutcomeData(instruction="do something else", setup=[])
    assert a.key() == b.key()
    assert a.key() != c.key()


def test_unknown_field_is_rejected_with_the_filename(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"instruction": "x", "expect": {}, "typo": 1}))
    with pytest.raises(ValueError, match="bad.json"):
        load("outcome", bad)


def test_policy_needs_a_rule():
    from tatl.data import Policy
    with pytest.raises(ValueError):
        Policy().to_assertion()


def test_level3_filters_unreviewed_cases():
    spec = DatasetData(cases=[
        {"input": "a", "expect": "x"},
        {"input": "b", "expect": "y", "reviewed": False},
    ])
    assert [c.input for c in spec.reviewed_cases()] == ["a"]


@pytest.mark.parametrize("stage,folder", [
    ("outcome", "outcome"), ("path", "path"),
    ("components", "component"), ("component", "dataset"),
])
def test_every_shipped_data_file_loads(stage, folder):
    files = sorted((DATA / folder).glob("*.json"))
    assert files, f"no data files in {folder}"
    for path in files:
        load(stage, path)


def test_intent_dataset_is_balanced():
    spec = load("component", "dataset/intent_classification.json", DATA)
    counts: dict[str, int] = {}
    for case in spec.cases:
        counts[case.expect] = counts.get(case.expect, 0) + 1
    from typing import get_args

    from llm import Intent

    assert set(counts) == set(get_args(Intent))
    assert min(counts.values()) >= 10
    assert len({c.input for c in spec.cases}) == len(spec.cases), "duplicate inputs"


def test_suite_modules_register_expected_cases():
    registry = load_suites(ROOT / "suite")
    names = {(c.stage, c.name) for c in registry.cases}
    assert ("outcome", "create_page_default") in names
    assert ("path", "create_page_default") in names
    assert ("component", "intent_classification") in names
    for case in registry.cases:
        assert (DATA / case.data).is_file(), case.data


def test_duplicate_case_names_are_rejected():
    registry = Registry()
    registry.add(Case(stage="outcome", kind="outcome", name="dup", data="a.json", fn=lambda r: None))
    with pytest.raises(ValueError, match="duplicate"):
        registry.add(Case(stage="outcome", kind="outcome", name="dup", data="b.json", fn=lambda r: None))


def test_decorators_register_and_return_the_function():
    REGISTRY.clear()
    try:
        @outcome(data="outcome/x.json", k=2)
        def outcome_case(outcome):
            return "kept"

        @path(data="path/x.json")
        def path_case(path):
            pass

        @component.retrieval(data="dataset/x.json", k=7)
        def retrieval_case(report):
            pass

        assert outcome_case(None) == "kept"
        by_stage = {c.stage: c for c in REGISTRY.cases}
        assert by_stage["outcome"].k == 2 and by_stage["outcome"].name == "x"
        assert by_stage["outcome"].episodes == 2
        assert by_stage["component"].kind == "retrieval" and by_stage["component"].image_k == 7
    finally:
        REGISTRY.clear()


def test_runs_can_exceed_k_so_pass_hat_k_is_estimated_not_all_or_nothing():
    from tatl.data import OutcomeData
    from tatl.runner import grade_outcome

    REGISTRY.clear()
    try:
        @outcome(data="outcome/x.json", k=2, runs=4)
        def sampled(outcome):
            pass

        case = REGISTRY.cases[0]
        assert case.episodes == 4

        spec = OutcomeData(instruction="i", expect={"created": {"pages": {"/p": {"name": "P"}}}})
        page = {"id": "/p", "url": "/p", "name": "P", "sections": []}
        def episode(created):
            final = {"tables": {"pages": [page] if created else []}}
            return type("E", (), {"trace": {"initial_snapshot": {"tables": {"pages": []}},
                                           "final_snapshot": final}, "rejected_at": None})()
        measured = grade_outcome(case, spec, [episode(True), episode(True), episode(True), episode(False)])
        assert (measured.runs, measured.k, measured.passes) == (4, 2, 3)
        assert measured.pass_hat_k == 0.5
        assert measured.pass_rate == 0.75
    finally:
        REGISTRY.clear()


class StubProbes:
    def __init__(self, mapping):
        self.mapping = mapping

    def classify(self, text):
        return self.mapping.get(text, ("unsupported", {}))

    def plan_sections(self, slots, text):
        return self.mapping.get(text, [])

    def rank_images(self, text, k):
        return self.mapping.get(text, [])[:k]


def case(kind, name="c", image_k=5):
    return Case(stage="component", kind=kind, name=name, data="d.json", fn=lambda r: None,
                image_k=image_k)


def test_grade_classification():
    spec = DatasetData(probe="classify", cases=[
        {"input": "a", "expect": "createPage"},
        {"input": "b", "expect": "removeSection"},
    ])
    probes = StubProbes({"a": ("createPage", {}), "b": ("createPage", {})})
    result = grade_dataset(case("classification"), spec, probes, 2)
    assert result.accuracy == 0.5
    assert result.errors[0]["expected"] == "removeSection"


def test_grade_extraction():
    spec = DatasetData(probe="classify", metric="slot_accuracy", cases=[
        {"input": "a", "expect": {"business": "Maria's Bakery", "goal": "orders"}},
    ])
    probes = StubProbes({"a": ("createPage", {"business": "marias-bakery", "goal": None})})
    result = grade_dataset(case("extraction"), spec, probes, 2)
    assert result.slot_accuracy == 0.5
    assert result.per_slot == {"business": 1.0, "goal": 0.0}


def test_grade_retrieval_respects_k():
    spec = DatasetData(probe="rank_images", metric="recall_at_k",
                      cases=[{"input": "q", "expect": "img-4"}])
    probes = StubProbes({"q": ["img-1", "img-2", "img-3", "img-4"]})
    assert grade_dataset(case("retrieval", image_k=5), spec, probes, 1).recall_at_k == 1.0
    assert grade_dataset(case("retrieval", image_k=2), spec, probes, 1).recall_at_k == 0.0


def test_plan_sections_output_is_joined_for_comparison():
    spec = DatasetData(probe="plan_sections", cases=[{"input": "q", "expect": "hero,faq"}])
    probes = StubProbes({"q": ["hero", "faq"]})
    assert grade_dataset(case("classification"), spec, probes, 1).accuracy == 1.0


def test_grade_returns_none_for_empty_data():
    assert grade_dataset(case("classification"), DatasetData(cases=[]), StubProbes({}), 1) is None


def test_verdict_records_assertion_failure_without_crashing():
    def body(outcome):
        assert outcome.pass_hat_k == 1.0, "flaky"

    measurement = Outcome(name="c", runs=3, passes=2, pass_rate=0.67, pass_hat_k=0.0)
    result = _verdict(Case(stage="outcome", kind="outcome", name="c", data="d", fn=body),
                      measurement, "outcome")
    assert result.passed is False and "flaky" in result.error


def test_verdict_records_unexpected_exception():
    def body(outcome):
        raise KeyError("boom")

    result = _verdict(Case(stage="outcome", kind="outcome", name="c", data="d", fn=body),
                      Outcome(name="c", runs=1, passes=1, pass_rate=1.0, pass_hat_k=1.0), "outcome")
    assert result.passed is False and "KeyError" in result.error


def test_verdict_skips_when_nothing_was_measured():
    result = _verdict(Case(stage="outcome", kind="outcome", name="c", data="d",
                           fn=lambda r: None), None, "outcome")
    assert result.skipped and result.passed


def test_score_classification_macro_f1_penalises_rare_class_misses():
    inputs = ["a", "b", "c"]
    perfect = score_classification(inputs, ["x", "x", "y"], ["x", "x", "y"])
    assert perfect.macro_f1 == 1.0 and perfect.accuracy == 1.0

    collapsed = score_classification(inputs, ["x", "x", "y"], ["x", "x", "x"])
    assert collapsed.accuracy == pytest.approx(2 / 3, abs=1e-4)
    assert collapsed.macro_f1 < collapsed.accuracy


def test_score_extraction_handles_no_expectations():
    assert score_extraction(["a"], [{}], [{}]).slot_accuracy == 1.0


def test_score_retrieval_reports_misses():
    score = score_retrieval(["q"], ["want"], [["other"]])
    assert score.recall_at_k == 0.0 and score.misses[0]["expected"] == "want"


def sample_report():
    return SuiteReport(model="m", seconds=1.0, episodes_run=6, results=[
        CaseResult(name="create_page_default", stage="outcome", kind="outcome", passed=True,
                   measurement=Outcome(name="create_page_default", runs=3, passes=3,
                                       pass_rate=1.0, pass_hat_k=1.0)),
        CaseResult(name="create_page_default", stage="path", kind="path", passed=False,
                   error="policy violated",
                   measurement=PathResult(
                       name="create_page_default", runs=3, node_f1=0.9, node_precision=0.9,
                       node_recall=0.9, edge_f1=0.8, order_conformance=0.5,
                       redundancy_ratio=0.1, policies_passed=False,
                       policy_failures=["save_draft executed without prior assemble_page"])),
        CaseResult(name="create_page_default", stage="component", kind="components", passed=True,
                   measurement=Components(name="create_page_default", phrasings=4,
                                          intent_accuracy=1.0, slot_accuracy=1.0,
                                          sections_accuracy=0.75, image_recall=0.5)),
        CaseResult(name="intent_classification", stage="component", kind="classification", passed=True,
                   measurement=Classification(name="intent_classification", accuracy=0.95,
                                              macro_f1=0.93, total=60)),
        CaseResult(name="brief_slots", stage="component", kind="extraction", passed=True,
                   measurement=Extraction(name="brief_slots", slot_accuracy=0.97, total=10)),
        CaseResult(name="image_selection", stage="component", kind="retrieval", passed=True,
                   measurement=Retrieval(name="image_selection", k=5, recall_at_k=0.8,
                                         hits=8, total=10)),
    ])


def test_matrix_merges_all_three_stages_onto_one_row():
    rows = {r["task"]: r for r in matrix_rows(sample_report())}
    row = rows["create_page_default"]
    assert row["runs"] == "3/3" and row["pass_k"] == 1.0
    assert row["order"] == 0.5 and row["policies"] == 0.0
    assert row["intent"] == 1.0 and row["slots"] == 1.0
    assert row["sections"] == 0.75 and row["image"] == 0.5
    assert row["n"] == 4
    assert row["ok"] is False


def test_dataset_probes_share_the_matrix_with_scenarios():
    rows = {r["task"]: r for r in matrix_rows(sample_report())}
    assert {"intent_classification", "brief_slots", "image_selection"} <= set(rows)
    assert rows["intent_classification"]["intent"] == 0.93
    assert rows["intent_classification"]["n"] == 60
    assert rows["brief_slots"]["slots"] == 0.97
    assert rows["image_selection"]["image"] == 0.8
    assert rows["intent_classification"].get("pass_k") is None


def test_pass_k_label_shows_the_real_k():
    from tatl.report import _pass_k_label
    assert _pass_k_label(sample_report(), "pass^{k}") == "pass^3"


def test_summary_shows_failures_with_detail():
    text = render_summary(sample_report(), SuiteConfig(root=str(ROOT)))
    assert "5 passed, 1 failed" in text
    assert "policy violated" in text
    assert "save_draft executed without prior assemble_page" in text


def test_html_is_self_contained_and_shaded():
    page = render_html(sample_report(), SuiteConfig(root=str(ROOT)))
    assert page.startswith("<!doctype html>")
    assert "src=" not in page and "<style>" in page
    assert "background:rgb(" in page
    assert "create_page_default" in page


def test_config_without_file_builds_default_adapter(tmp_path, monkeypatch):
    import mongomock
    import mlp_adapter

    monkeypatch.setenv("MLP_LLM", "stub")
    monkeypatch.setenv("MLP_IMAGES", "stub")
    monkeypatch.setattr(mlp_adapter, "MongoClient", mongomock.MongoClient)

    config = SuiteConfig.load(None, tmp_path)
    adapter = config.build_adapter()
    try:
        assert isinstance(adapter, mlp_adapter.MlpAdapter)
        intent, _ = adapter.probes().classify("Create a landing page for a bakery")
        assert intent == "createPage"
    finally:
        adapter.close()


def test_shipped_config_matches_produced_columns():
    config = SuiteConfig.load(ROOT / "tatl.config.json", ROOT)
    produced = {key for row in matrix_rows(sample_report()) for key in row}
    assert {c.key for c in config.matrix} <= produced
    assert config.path(config.suite_dir).is_dir()
    assert config.path(config.data_dir).is_dir()


def test_report_json_round_trips():
    report = sample_report()
    restored = SuiteReport.model_validate(json.loads(report.model_dump_json()))
    assert len(restored.failures) == 1


def test_grade_components_all_correct():
    from tatl.data import ComponentData
    from tatl.runner import grade_components

    spec = ComponentData(instruction="q", expect={
        "intent": "createPage",
        "slots": {"business": "Maria's Bakery"},
        "sections": ["hero", "faq"],
    })
    probes = StubProbes({"q": ("createPage", {"business": "marias bakery"})})
    probes.plan_sections = lambda slots, text: ["hero", "faq"]
    result = grade_components(case("components"), spec, probes)
    assert result.intent_accuracy == 1.0
    assert result.slot_accuracy == 1.0 and result.sections_accuracy == 1.0
    assert result.errors == []


def test_a_variant_can_expect_its_own_slot_values():
    from tatl.data import ComponentData
    from tatl.runner import grade_components

    spec = ComponentData(
        instruction="Swap the first two steps",
        variants=["Move the first step down one",
                  {"text": "Put Order online after We bake",
                   "slots": {"path": "items.order online", "position": "after we bake"}}],
        expect={"intent": "moveItem",
                "slots": {"section": "process", "path": "items.0", "position": "down"}})
    assert spec.phrasings() == ["Swap the first two steps", "Move the first step down one",
                                "Put Order online after We bake"]
    assert spec.expected_slots("Move the first step down one") == \
        {"section": "process", "path": "items.0", "position": "down"}
    assert spec.expected_slots("Put Order online after We bake") == \
        {"section": "process", "path": "items.order online", "position": "after we bake"}

    counted = ("moveItem", {"section": "process", "path": "items.0", "position": "down"})
    named = ("moveItem", {"section": "process", "path": "items.order online",
                          "position": "after we bake"})
    probes = StubProbes({"Swap the first two steps": counted,
                         "Move the first step down one": counted,
                         "Put Order online after We bake": named})
    result = grade_components(case("components"), spec, probes)
    assert result.slot_accuracy == 1.0, result.errors


def test_a_probe_that_raises_scores_as_a_miss_instead_of_aborting_the_suite():
    from tatl.data import ComponentData
    from tatl.runner import grade_components

    spec = ComponentData(instruction="q", variants=["r"], expect={
        "intent": "createPage", "slots": {"business": "Maria's Bakery"}})

    class Flaky(StubProbes):
        def classify(self, text):
            if text == "q":
                raise RuntimeError("read timed out")
            return super().classify(text)

    result = grade_components(case("components"), spec,
                              Flaky({"r": ("createPage", {"business": "Maria's Bakery"})}))
    assert result.intent_accuracy == 0.5 and result.slot_accuracy == 0.5
    assert any("classify failed: RuntimeError: read timed out" in e for e in result.errors)


def test_grade_components_reports_each_failure():
    from tatl.data import ComponentData
    from tatl.runner import grade_components

    spec = ComponentData(instruction="q", expect={
        "intent": "createPage",
        "slots": {"business": "Maria's Bakery", "goal": "orders"},
        "sections": ["hero"],
    })
    probes = StubProbes({"q": ("editContent", {"business": "Wrong Co"})})
    probes.plan_sections = lambda slots, text: ["hero", "benefits"]
    result = grade_components(case("components"), spec, probes)
    assert result.intent_accuracy == 0.0
    assert result.slot_accuracy == 0.0
    assert result.sections_accuracy == 0.0
    assert len(result.errors) == 4


def test_grade_components_skips_unstated_expectations():
    from tatl.data import ComponentData
    from tatl.runner import grade_components

    spec = ComponentData(instruction="q", expect={"intent": "unsupported"})
    probes = StubProbes({"q": ("unsupported", {})})
    result = grade_components(case("components"), spec, probes)
    assert result.intent_accuracy == 1.0
    assert result.slot_accuracy is None and result.sections_accuracy is None


def test_every_shipped_components_file_loads():
    for path in sorted((DATA / "level3" / "components").glob("*.json")):
        spec = load("components", path)
        assert spec.instruction and spec.expect.intent


def test_view_model_is_shared_by_both_renderers():
    from tatl.report import build_view

    view = build_view(sample_report(), SuiteConfig(root=str(ROOT)))
    row = next(r for r in view["rows"] if r["name"] == "create_page_default")
    assert len(row["cells"]) == len(SuiteConfig(root=str(ROOT)).matrix)
    assert [c["text"] for c in row["cells"]][:3] == ["4", "3/3", "1.00"]
    coloured = [c for c in row["cells"] if c["color"]]
    assert coloured and all(c["rgb"] and c["color"].startswith("rgb(") for c in coloured)


def test_view_groups_span_their_columns():
    from tatl.report import build_view

    view = build_view(sample_report(), SuiteConfig(root=str(ROOT)))
    assert [g["label"] for g in view["groups"]] == ["scope", "Outcome", "Path", "Component"]
    assert sum(g["span"] for g in view["groups"]) == len(view["columns"])
    assert sum(1 for c in view["columns"] if c["sep"]) == len(view["groups"]) - 1


def test_html_renders_from_the_template():
    page = render_html(sample_report(), SuiteConfig(root=str(ROOT)))
    assert page.startswith("<!doctype html>")
    assert page.rstrip().endswith("</html>")
    assert "<style>" in page and "src=" not in page and "<link" not in page
    assert "background:rgb(" in page
    assert "create_page_default" in page


def test_html_escapes_case_names():
    report = sample_report()
    report.results[0].name = "<script>alert(1)</script>"
    page = render_html(report, SuiteConfig(root=str(ROOT)))
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_html_marks_failures():
    page = render_html(sample_report(), SuiteConfig(root=str(ROOT)))
    assert "Failures" in page and "policy violated" in page
    assert "&#10007;" in page


def test_stylesheet_is_light_only():
    css = (Path(__file__).resolve().parents[2] / "tatl/templates/report.css").read_text()
    assert "prefers-color-scheme" not in css
    assert "--bg: #ffffff" in css


def test_saved_report_restores_typed_measurements():
    original = sample_report()
    restored = SuiteReport.model_validate_json(original.model_dump_json())

    outcome = restored.results[0].measurement
    assert isinstance(outcome, Outcome) and outcome.pass_hat_k == 1.0
    assert isinstance(restored.results[1].measurement, PathResult)
    assert isinstance(restored.results[2].measurement, Components)
    assert isinstance(restored.results[3].measurement, Classification)

    config = SuiteConfig(root=str(ROOT))
    assert matrix_rows(restored) == matrix_rows(original)
    assert dataset_rows(restored) == dataset_rows(original)
    assert render_html(restored, config) == render_html(original, config)


class FakeAdapter:
    name = "fake"

    def __init__(self):
        self.episodes = 0

    def run_episode(self, task, run_index):
        from tatl.adapter import EpisodeOutcome
        self.episodes += 1
        empty = {"tables": {"pages": []}}
        return EpisodeOutcome(
            trace={"instruction": task.instruction, "steps": [],
                   "initial_snapshot": empty, "final_snapshot": empty,
                   "summary": ""},
            rejected_at="intent")

    def probes(self):
        class Probes:
            def classify(self, text):
                return "unsupported", {}

            def plan_sections(self, slots, text):
                return []

            def rank_images(self, query, k):
                return None

            def rank_categories(self, query, k):
                return None
        return Probes()

    def close(self):
        pass


def test_run_suite_executes_every_shipped_case():
    from tatl.runner import run_suite

    config = SuiteConfig.load(ROOT / "tatl.config.json", ROOT)
    config.workers = 2
    registry = load_suites(config.path(config.suite_dir))
    adapter = FakeAdapter()

    report = run_suite(config, adapter, registry)

    assert len(report.results) == len(registry.cases)
    assert adapter.episodes > 0
    stages = {r.stage for r in report.results}
    assert stages == {"outcome", "path", "component"}
    assert render_html(report, config).startswith("<!doctype html>")
    assert "THREE-LEVEL SUITE" in render_summary(report, config)
    assert report.telemetry == {"episodes": adapter.episodes, "model_calls": {},
                                "step_status": {}, "defaulted_by_tool": {}}


def step(tool, result):
    return {"call": {"tool": tool, "args": {}}, "result": result, "error": None}


def model_calls(**stages):
    zero = {"calls": 0, "first_attempt_valid": 0, "retried_valid": 0, "exhausted": 0}
    by_stage = {name: {**zero, **counts} for name, counts in stages.items()}
    total = {key: sum(counts[key] for counts in by_stage.values()) for key in zero}
    return {"total": total, "by_stage": by_stage}


def test_the_pool_sums_telemetry_and_step_statuses_over_every_episode():
    from tatl.runner import EpisodePool

    pool = EpisodePool(adapter=None, workers=1)
    pool.collect({
        "steps": [step("select_theme", {"name": "Hue", "status": "repaired"}),
                  step("select_layout", "defaulted"),
                  step("generate_copy", {"fields": ["headline"]}),
                  step("plan", ["a", "b"]),
                  step("assemble_section", "ok")],
        "telemetry": model_calls(
            Interpretation={"calls": 1, "first_attempt_valid": 1},
            HeroCopy={"calls": 2, "retried_valid": 1, "exhausted": 1}),
    })
    pool.collect({
        "steps": [step("select_icon", {"icon": "x", "status": "defaulted"}),
                  step("assemble_section", "defaulted"),
                  step("assemble_section", "ok")],
        "telemetry": model_calls(Interpretation={"calls": 1, "retried_valid": 1}),
    })
    pool.collect({"steps": [step("interpret", {"intent": "createPage"})], "telemetry": None})

    summary = pool.telemetry()
    assert summary["step_status"] == {"repaired": 1, "defaulted": 3, "ok": 2}
    assert summary["defaulted_by_tool"] == {"select_layout": 1, "select_icon": 1,
                                            "assemble_section": 1}
    assert summary["model_calls"]["total"] == {"calls": 4, "first_attempt_valid": 1,
                                               "retried_valid": 2, "exhausted": 1}
    assert summary["model_calls"]["by_stage"]["Interpretation"] == {
        "calls": 2, "first_attempt_valid": 1, "retried_valid": 1, "exhausted": 0}
    assert summary["model_calls"]["by_stage"]["HeroCopy"]["exhausted"] == 1


def telemetry_report():
    report = sample_report()
    report.telemetry = {
        "episodes": 6,
        "model_calls": model_calls(Interpretation={"calls": 6, "first_attempt_valid": 5,
                                                   "retried_valid": 1}),
        "step_status": {"ok": 40, "repaired": 3, "defaulted": 2},
        "defaulted_by_tool": {"select_icon": 2},
    }
    return report


def test_telemetry_is_reported_beside_the_matrix_in_json_text_and_html():
    from tatl.report import telemetry_tables

    report = telemetry_report()
    config = SuiteConfig(root=str(ROOT))

    tables = telemetry_tables(report.telemetry)
    assert [t["title"] for t in tables] == ["model_calls", "model_calls / by_stage",
                                            "step_status", "defaulted_by_tool"]
    assert tables[0]["rows"] == [["total", 6, 5, 1, 0]]
    assert tables[1]["columns"] == ["calls", "first_attempt_valid", "retried_valid", "exhausted"]
    assert tables[1]["rows"] == [["Interpretation", 6, 5, 1, 0]]
    assert tables[2]["rows"] == [["", 40, 3, 2]]

    report.telemetry["model_calls"]["by_stage"] = {}
    assert [t["title"] for t in telemetry_tables(report.telemetry)] == [
        "model_calls", "step_status", "defaulted_by_tool"]

    text = render_summary(report, config)
    assert "TELEMETRY" in text and "first_attempt_valid" in text and "select_icon" in text
    assert "TELEMETRY" not in render_summary(sample_report(), config)

    page = render_html(report, config)
    assert "<h2>Telemetry</h2>" in page and "defaulted_by_tool" in page
    assert "<h2>Telemetry</h2>" not in render_html(sample_report(), config)

    saved = json.loads(report.model_dump_json())
    assert saved["telemetry"]["episodes"] == 6
    assert set(saved) >= {"model", "seconds", "episodes_run", "telemetry"}
    restored = SuiteReport.model_validate_json(report.model_dump_json())
    assert restored.telemetry == report.telemetry


def test_reports_saved_before_telemetry_existed_still_render():
    saved = json.loads(sample_report().model_dump_json())
    del saved["telemetry"]
    restored = SuiteReport.model_validate_json(json.dumps(saved))
    assert restored.telemetry == {}
    assert "TELEMETRY" not in render_summary(restored, SuiteConfig(root=str(ROOT)))


def test_run_suite_shares_episodes_between_outcome_and_path():
    from tatl.runner import run_suite

    config = SuiteConfig.load(ROOT / "tatl.config.json", ROOT)
    config.workers = 2
    registry = load_suites(config.path(config.suite_dir))
    outcome_cases = {c.name: c.episodes for c in registry.by_stage("outcome")}
    path_cases = {c.name: c.episodes for c in registry.by_stage("path")}
    shared = set(outcome_cases) & set(path_cases)
    assert shared, "expected some scenarios graded at both stages"

    adapter = FakeAdapter()
    run_suite(config, adapter, registry)

    naive = sum(outcome_cases.values()) + sum(path_cases.values())
    assert adapter.episodes < naive
    assert adapter.episodes == sum(
        max(outcome_cases.get(n, 0), path_cases.get(n, 0))
        for n in set(outcome_cases) | set(path_cases))
