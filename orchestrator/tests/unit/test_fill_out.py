import mongomock
import pytest

import providers
from llm import ExtractedArgs, Interpretation
from pipeline import CORE_SECTIONS, CommandContext, IntentInvalid, run_command
from session import SessionStore
from storage import PageStore


class BareAddSection:
    def choose_layouts(self, brief, pack, section_types):
        return {}


    def interpret(self, transcript, pending=None):
        return Interpretation(intent="addSection", args=ExtractedArgs())


@pytest.fixture
def store():
    return PageStore(mongomock.MongoClient()["vlp-fill"]["pages"])


def create(store, command="Create a page for Nordvik Dental with just a hero"):
    return run_command(command, "en", store, CommandContext(), None)


def fill(store, url, **args):
    return run_command("[addSection]", "en", store, CommandContext(page_id=url),
                       None, forced=("addSection", args))


def composed(page):
    sections = page["sections"] if isinstance(page, dict) else page
    return [s["type"] for s in sections
            if s["type"] not in ("header", "footer")]


def by_type(page, kind):
    sections = page["sections"] if isinstance(page, dict) else page
    return next(s for s in sections if s["type"] == kind)


def test_a_short_page_is_filled_out_to_the_full_layout(store):
    url = create(store)["page"]["id"]
    assert composed(store.get(url, None)) == ["hero"]

    result = fill(store, url)
    assert composed(result["page"]) == CORE_SECTIONS
    assert result["message"] == "Done -- added 4 sections."


def test_naming_a_type_still_adds_only_that_one(store):
    url = create(store)["page"]["id"]
    result = fill(store, url, type="faq")
    assert composed(result["page"]) == ["hero", "faq"]


def test_filling_out_is_one_version(store):
    url = create(store)["page"]["id"]
    fill(store, url)
    versions = store.get(url, None)["versions"]
    assert [v["label"] for v in versions] == ["Initial draft", "Added 4 sections"]


def test_a_complete_page_offers_the_rest_when_it_cannot_ask(store):
    url = create(store, "Create a page for Nordvik Dental")["page"]["id"]
    assert composed(store.get(url, None)) == CORE_SECTIONS

    with pytest.raises(IntentInvalid, match="Which one"):
        fill(store, url)


def test_a_complete_page_asks_which_section_to_add(monkeypatch, store):
    url = create(store, "Create a page for Nordvik Dental")["page"]["id"]
    monkeypatch.setattr(providers.DEFAULT, "lang", BareAddSection())

    result = run_command("can we add more sections describing the product?", "en",
                         store, CommandContext(session_id="s1", page_id=url),
                         SessionStore(mongomock.MongoClient()["vlp-fill"]["sessions"]))

    clarification = result["clarification"]
    assert clarification["intent"] == "addSection"
    field = clarification["fields"][0]
    assert field["name"] == "type"
    assert field["question"] == "What kind of section should I add?"
    assert "services" in field["options"]
    assert all(kind not in field["options"] for kind in CORE_SECTIONS)


def test_the_last_missing_section_is_named_in_the_label(store):
    url = create(store, "Create a page for Nordvik Dental with just a hero")["page"]["id"]
    fill(store, url, type="benefits")
    fill(store, url, type="testimonials")
    fill(store, url, type="promotion")

    result = fill(store, url)
    assert composed(result["page"])[-1] == "faq"
    assert "Added faq section" in [v["label"] for v in store.get(url, None)["versions"]]
