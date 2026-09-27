import pytest

import providers
import telemetry
from llm import ModelLanguageService
from llm_client import LLMResponseInvalid
from pipeline import SchemaInvalid, run_create_page
from tatl.runner import _step_status


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)

    def complete_json(self, system, user, schema=None, options=None):
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def service(*responses):
    return ModelLanguageService(FakeClient(responses))


HERO = {"headline": "Fresh bread", "subhead": "Baked before sunrise.", "button": {"label": "Order"}}
BRIEF = {"business": "Maria's Bakery", "audience": "families", "goal": "orders", "tone": None}
CREATE_CMD = "Create a landing page for Maria's Bakery with a hero and an FAQ"


@pytest.fixture(autouse=True)
def fresh_collector():
    yield
    telemetry._current.set(None)


def test_summary_counts_first_attempt_retried_and_exhausted_per_stage():
    calls = telemetry.ModelCalls()
    calls.record("Interpretation", 1, True)
    calls.record("Interpretation", 2, True)
    calls.record("HeroCopy", 1, True)
    calls.record("HeroCopy", 2, False)

    summary = calls.summary()
    assert summary["total"] == {"calls": 4, "first_attempt_valid": 2,
                                "retried_valid": 1, "exhausted": 1}
    assert summary["by_stage"]["Interpretation"] == {
        "calls": 2, "first_attempt_valid": 1, "retried_valid": 1, "exhausted": 0}
    assert summary["by_stage"]["HeroCopy"] == {
        "calls": 2, "first_attempt_valid": 1, "retried_valid": 0, "exhausted": 1}


def test_recording_without_a_collector_is_a_no_op():
    assert telemetry.current() is None
    telemetry.record("HeroCopy", 1, True)
    assert telemetry.current() is None


def test_a_valid_first_answer_is_recorded_as_first_attempt_valid():
    calls = telemetry.start()
    service(HERO).generate_copy("hero", BRIEF)
    assert calls.calls == [{"stage": "HeroCopy", "attempts": 1, "ok": True}]


def test_a_valid_second_answer_is_recorded_as_retried_valid():
    calls = telemetry.start()
    service({"headline": ""}, HERO).generate_copy("hero", BRIEF)
    assert calls.calls == [{"stage": "HeroCopy", "attempts": 2, "ok": True}]


def test_two_invalid_answers_are_recorded_as_exhausted():
    calls = telemetry.start()
    service(LLMResponseInvalid("garbage"), {"headline": ""}).generate_copy("hero", BRIEF)
    assert calls.calls == [{"stage": "HeroCopy", "attempts": 2, "ok": False}]


def test_the_stage_is_the_model_that_was_asked_for():
    calls = telemetry.start()
    svc = service({"intent": "createPage", "args": {"business": "Maria's Bakery"}, "missing": []},
                  {"sections": ["hero", "faq"]})
    svc.interpret("a page for Maria's Bakery")
    svc.generate_schema(BRIEF, "hero and faq")
    assert [c["stage"] for c in calls.calls] == ["Interpretation", "SectionPlan"]


def counting(method, stage, attempts):
    def wrapped(*args, **kwargs):
        telemetry.record(stage, attempts, True)
        return method(*args, **kwargs)
    return wrapped


def test_the_trace_carries_the_calls_made_during_the_command(monkeypatch):
    lang = providers.DEFAULT.lang
    monkeypatch.setattr(lang, "interpret", counting(lang.interpret, "Interpretation", 2))
    monkeypatch.setattr(lang, "generate_copy", counting(lang.generate_copy, "Copy", 1))

    result = run_create_page(CREATE_CMD)

    summary = result["_trace"]["telemetry"]
    assert summary["total"] == {"calls": 3, "first_attempt_valid": 2,
                                "retried_valid": 1, "exhausted": 0}
    assert summary["by_stage"]["Interpretation"]["retried_valid"] == 1
    assert summary["by_stage"]["Copy"]["calls"] == 2


def test_each_command_starts_its_own_count(monkeypatch):
    lang = providers.DEFAULT.lang
    monkeypatch.setattr(lang, "interpret", counting(lang.interpret, "Interpretation", 1))

    first = run_create_page(CREATE_CMD)["_trace"]["telemetry"]
    second = run_create_page(CREATE_CMD)["_trace"]["telemetry"]
    assert first["total"]["calls"] == second["total"]["calls"] == 1


def test_a_rejected_command_still_reports_its_calls(monkeypatch):
    lang = providers.DEFAULT.lang
    monkeypatch.setattr(lang, "interpret", counting(lang.interpret, "Interpretation", 2))

    with pytest.raises(SchemaInvalid) as exc:
        run_create_page("break the page schema now")
    assert exc.value.trace["telemetry"]["total"]["retried_valid"] == 1


def test_the_stub_makes_no_model_calls():
    summary = run_create_page(CREATE_CMD)["_trace"]["telemetry"]
    assert summary["total"]["calls"] == 0
    assert summary["by_stage"] == {}


def test_every_constraint_site_writes_its_status_into_the_trace(monkeypatch):
    monkeypatch.setattr(providers.DEFAULT.lang, "choose_layouts",
                        lambda brief, pack, types: {"hero": "parallax-zoom",
                                                    "faq": "two-column-static"})
    steps = run_create_page(CREATE_CMD)["_trace"]["steps"]
    by_tool = {}
    for step in steps:
        by_tool.setdefault(step["call"]["tool"], set()).add(_step_status(step["result"]))

    assert by_tool["select_layout"] == {"repaired"}
    assert by_tool["select_theme"] <= {"ok", "repaired"}
    assert by_tool["assemble_section"] == {"ok"}
