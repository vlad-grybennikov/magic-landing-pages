import mongomock
import pytest

import providers
from llm import ExtractedArgs, Interpretation
from pipeline import CommandContext, IntentInvalid, run_command
from providers import Providers
from storage import PageStore


class FakeLang:
    def __init__(self, intent, **args):
        self.interpretation = Interpretation(intent=intent, args=ExtractedArgs(**args))

    def interpret(self, transcript, pending=None):
        return self.interpretation

    def choose_layouts(self, brief, pack, section_types):
        return {}


    def generate_schema(self, brief, transcript):
        return ["hero", "faq"]

    def generate_copy(self, section_type, brief):
        return {"headline": "Headline", "heading": "Heading", "button": {"label": "Go"},
                "items": [{"question": "Q?", "answer": "A."}]}

    def generate_theme(self, brief, hint=None):
        return {}

    def suggest_options(self, intent, args, missing, request=""):
        return {}


@pytest.fixture
def store():
    return PageStore(mongomock.MongoClient()["vlp-scope"]["pages"])


@pytest.fixture
def page(store):
    result = run_command("Create a page for Nordvik Dental with a hero and an FAQ",
                         "en", store, CommandContext(), None)
    return result["page"]["id"]


def edit(store, url, text, lang, section=None):
    stack = Providers(lang=lang, images=providers.DEFAULT.images,
                      icons=providers.DEFAULT.icons)
    ctx = None if url is None else CommandContext(page_id=url, section=section)
    return run_command(text, "en", store, ctx, None, providers=stack)


def composed(page):
    sections = page["sections"] if isinstance(page, dict) else page
    return [s["type"] for s in sections
            if s["type"] not in ("header", "footer")]


def by_type(page, kind):
    sections = page["sections"] if isinstance(page, dict) else page
    return next(s for s in sections if s["type"] == kind)


def test_an_unnamed_section_falls_back_to_the_selected_one(store, page):
    result = edit(store, page, "shorten the headline",
                  FakeLang("editContent", field="title", value="Shorter"),
                  section="hero")

    assert by_type(result["page"], "hero")["headline"] == "Shorter"


def test_a_named_section_wins_over_the_selection(store, page):
    result = edit(store, page, "change the FAQ heading to Questions",
                  FakeLang("editContent", section="faq", field="title",
                           value="Questions"),
                  section="hero")

    assert by_type(result["page"], "faq")["heading"] == "Questions"
    assert by_type(result["page"], "hero")["headline"] != "Questions"


def test_without_a_selection_the_command_is_still_asked_about(store, page):
    with pytest.raises(IntentInvalid, match="Which section"):
        edit(store, page, "shorten the headline",
             FakeLang("editContent", field="title", value="Shorter"))


def test_creating_a_page_ignores_the_selection(store):
    result = edit(store, None, "Create a page for Apex Plumbing",
                  FakeLang("createPage", business="Apex Plumbing",
                           audience="homeowners", goal="quotes"))
    assert composed(result["page"]) == ["hero", "faq"]
