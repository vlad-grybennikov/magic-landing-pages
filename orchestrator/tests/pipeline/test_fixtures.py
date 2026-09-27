from pathlib import Path

import mongomock
import pytest

from icon_selector import build_icon_service
from image_selector import StubImageService
from mlp_adapter import run_task
from oracle import FixtureLanguageService
from providers import Providers
from services import Services
from settings import Settings
from tatl.annotations import TaskAnnotation
from tatl.data import load
from tatl.evaluators import evaluate_outcome, evaluate_path
from transcriber import ScriptedTranscriber

DATA = Path(__file__).resolve().parents[2] / "test_data"
ORACLE = FixtureLanguageService(DATA)
ICONS = build_icon_service()


def fixtures(stage: str) -> list:
    return [pytest.param(spec, phrasing, id=f"{path.stem}[{index}]")
            for path in sorted((DATA / stage).glob("*.json"))
            for spec in [load(stage, path)]
            for index, phrasing in enumerate(spec.phrasings())]


def episode(spec, phrasing):
    services = Services.from_db(
        Settings(), mongomock.MongoClient()["vlp-fixtures"],
        Providers(lang=ORACLE, images=StubImageService(), icons=ICONS),
        ScriptedTranscriber())
    services.ensure_indexes()
    task = TaskAnnotation(id="case", capability="case", instruction=phrasing,
                          setup_pages=spec.setup)
    try:
        return run_task(services, task)
    finally:
        services.command_service.close()


@pytest.mark.parametrize("spec,phrasing", fixtures("outcome"))
def test_outcome_fixture_holds_through_the_real_pipeline(spec, phrasing):
    outcome = episode(spec, phrasing)
    assert outcome.rejected_at == spec.expect_rejection, outcome.trace.get("summary")
    result = evaluate_outcome(outcome.trace, spec.expect.to_goal(), spec.projection())
    assert result.passed, result.diffs


@pytest.mark.parametrize("spec,phrasing", fixtures("path"))
def test_path_fixture_holds_through_the_real_pipeline(spec, phrasing):
    outcome = episode(spec, phrasing)
    result = evaluate_path(outcome.trace, spec.to_dependency(), spec.to_policies())
    assert result.node_recall == 1.0, f"missing operations: {result.missing_ops}"
    assert result.policies_passed, [p.detail for p in result.policy_results if not p.passed]
    assert result.order_conformance == 1.0


def test_every_outcome_phrasing_is_covered_by_a_component_annotation():
    uncovered = []
    for path in sorted((DATA / "outcome").glob("*.json")):
        spec = load("outcome", path)
        if spec.expect_rejection:
            continue
        for phrasing in spec.phrasings():
            if ORACLE.lookup(phrasing) is None:
                uncovered.append((path.stem, phrasing))
    assert uncovered == []
