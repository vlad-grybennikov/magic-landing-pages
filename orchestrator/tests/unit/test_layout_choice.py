import mongomock
import pytest

import providers
from layouts import LAYOUT_PACKS, is_known
from pipeline import CommandContext, run_command
from storage import PageStore

COMMAND = "Create a page for Nordvik Dental with a hero and an FAQ"


@pytest.fixture
def store():
    return PageStore(mongomock.MongoClient()["vlp-layout"]["pages"])


def variants(result):
    return {s["type"]: s.get("variant") for s in result["page"]["sections"]}


def create(store):
    return run_command(COMMAND, "en", store, CommandContext(), None)


def test_the_model_s_choice_is_used(monkeypatch, store):
    monkeypatch.setattr(providers.DEFAULT.lang, "choose_layouts",
                        lambda brief, pack, types: {"hero": "full-bleed",
                                                    "faq": "two-column-static"})
    result = create(store)

    assert variants(result)["hero"] == "full-bleed"
    assert variants(result)["faq"] == "two-column-static"
    assert result["validation"]["gates"]["layout"] == "ok"


def test_a_variant_that_does_not_exist_falls_back_to_the_pack(monkeypatch, store):
    monkeypatch.setattr(providers.DEFAULT.lang, "choose_layouts",
                        lambda brief, pack, types: {"hero": "parallax-zoom",
                                                    "faq": "two-column-static"})
    result = create(store)
    chosen = variants(result)

    assert chosen["faq"] == "two-column-static"
    assert is_known("hero", chosen["hero"])
    assert result["validation"]["gates"]["layout"] == "repaired"


def test_a_variant_from_the_wrong_section_is_refused(monkeypatch, store):
    monkeypatch.setattr(providers.DEFAULT.lang, "choose_layouts",
                        lambda brief, pack, types: {"hero": "masonry",
                                                    "faq": "two-column-static"})
    result = create(store)

    assert is_known("hero", variants(result)["hero"])
    assert variants(result)["hero"] != "masonry"
    assert result["validation"]["gates"]["layout"] == "repaired"


def test_no_choice_leaves_the_pack_in_charge(monkeypatch, store):
    monkeypatch.setattr(providers.DEFAULT.lang, "choose_layouts",
                        lambda brief, pack, types: {})
    result = create(store)
    chosen = variants(result)
    pack = result["page"]["theme"]["layout"] if result["page"]["theme"] else None

    assert result["validation"]["gates"]["layout"] == "defaulted"
    if pack in LAYOUT_PACKS:
        assert chosen["hero"] == LAYOUT_PACKS[pack]["hero"]


def test_the_layout_is_chosen_after_the_palette_and_before_the_sections(store):
    result = create(store)
    tools = [s["call"]["tool"] for s in result["_trace"]["steps"]]

    assert tools.index("select_theme") < tools.index("select_layout")
    assert tools.index("select_layout") < tools.index("assemble_section")


def test_every_section_still_renders_something(store):
    result = create(store)
    for section_type, variant in variants(result).items():
        assert is_known(section_type, variant), f"{section_type}: {variant}"
