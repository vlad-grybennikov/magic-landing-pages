import pytest

import providers
from llm import ExtractedArgs, ModelLanguageService, to_brief
from llm_client import LLMResponseInvalid, LLMUnavailable
from pipeline import ServiceUnavailable, run_create_page


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete_json(self, system, user, schema=None, options=None):
        self.calls.append({"system": system, "user": user, "schema": schema})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def service(*responses):
    return ModelLanguageService(FakeClient(responses))


INTERPRET_OK = {
    "intent": "createPage",
    "args": {"business": "Maria's Bakery", "audience": "young families",
             "goal": "collect orders"},
    "missing": [],
}


def test_interpret_happy_path():
    svc = service(INTERPRET_OK)
    interp = svc.interpret("a page for Maria's Bakery")
    assert interp.intent == "createPage"
    assert interp.args.business == "Maria's Bakery"
    assert interp.missing == []


def test_interpret_missing_is_recomputed_not_trusted():
    svc = service({
        "intent": "createPage",
        "args": {"business": "Apex Plumbing"},
        "missing": [],
    })
    interp = svc.interpret("a page for Apex Plumbing")
    assert interp.missing == ["audience", "goal"]


def test_interpret_retries_invalid_then_succeeds():
    svc = service({"intent": "nonsense"}, INTERPRET_OK)
    interp = svc.interpret("a page for Maria's Bakery")
    assert interp.intent == "createPage"
    assert len(svc.client.calls) == 2
    assert "previous response was invalid" in svc.client.calls[1]["user"]


def test_a_request_that_names_no_business_reports_it_missing_without_retrying():
    svc = service({"intent": "createPage",
                   "args": {"audience": "tourists visiting Toronto", "goal": "sell day tours"},
                   "missing": ["business"]})
    interp = svc.interpret("Can you create a website for a tourism guide? I'm working in Toronto")
    assert interp.args.business is None
    assert interp.missing == ["business"]
    assert len(svc.client.calls) == 1


def test_an_answer_with_no_arguments_at_all_is_asked_once_more():
    empty = {"intent": "createPage", "args": {}, "missing": ["business", "audience", "goal"]}
    svc = service(empty, INTERPRET_OK)
    interp = svc.interpret("Set up a second Maria's Bakery page aimed at young families to take online orders")
    assert interp.args.business == "Maria's Bakery"
    assert len(svc.client.calls) == 2
    assert "gave no arguments at all" in svc.client.calls[1]["user"]

    svc = service(empty, empty)
    interp = svc.interpret("Set up a second Maria's Bakery page aimed at young families to take online orders")
    assert interp.args.business is None
    assert interp.missing == ["business", "audience", "goal"]
    assert len(svc.client.calls) == 2

    svc = service({"intent": "unsupported", "args": {}, "missing": []})
    assert svc.interpret("What time is it?").intent == "unsupported"
    assert len(svc.client.calls) == 1


def test_two_invalid_answers_keep_the_intent_but_guess_no_slots():
    svc = service({"intent": "nope"}, LLMResponseInvalid("garbage"))
    interp = svc.interpret("Can you create a website for a tourism guide? I'm working in Toronto")
    assert interp.intent == "createPage"
    assert interp.args.business is None
    assert interp.missing == ["business", "audience", "goal"]


def test_interpret_propagates_unavailable():
    svc = service(LLMUnavailable("connection refused"))
    with pytest.raises(LLMUnavailable):
        svc.interpret("a page for Maria's Bakery")


BRIEF = {"business": "Maria's Bakery", "audience": "families", "goal": "orders", "tone": None}


def test_generate_schema_dedupes_and_validates():
    svc = service({"sections": ["hero", "hero", "faq"]})
    assert svc.generate_schema(BRIEF, "hero and faq please") == ["hero", "faq"]


def test_generate_schema_falls_back_to_stub():
    svc = service({"sections": ["banner"]}, {"sections": ["banner"]})
    assert svc.generate_schema(BRIEF, "a page with a hero and an FAQ") == ["hero", "faq"]


def test_generate_copy_returns_validated_dump():
    svc = service({
        "headline": "Fresh bread, every morning",
        "subhead": "Baked before sunrise.",
        "button": {"label": "Order now"},
    })
    result = svc.generate_copy("hero", BRIEF)
    assert result["headline"] == "Fresh bread, every morning"
    assert result["button"] == {"label": "Order now"}


def test_generate_copy_returns_empty_after_two_failures():
    svc = service({"headline": ""}, {"headline": ""})
    assert svc.generate_copy("hero", BRIEF) == {}
    assert len(svc.client.calls) == 2


def test_to_brief_fallbacks():
    brief = to_brief(ExtractedArgs(), "Create a page for Apex Plumbing today")
    assert brief["business"] == "Apex Plumbing"
    assert brief["audience"] == "Local customers"
    assert brief["goal"] == "Generate enquiries"


def test_pipeline_maps_unavailable_to_service_error(monkeypatch):
    def dead_interpret(transcript, pending=None):
        raise LLMUnavailable("connection refused")

    monkeypatch.setattr(providers.DEFAULT.lang, "interpret", dead_interpret)
    with pytest.raises(ServiceUnavailable) as exc:
        run_create_page("Create a landing page for Maria's Bakery")
    assert exc.value.stage == "llm"
    assert exc.value.trace is not None
