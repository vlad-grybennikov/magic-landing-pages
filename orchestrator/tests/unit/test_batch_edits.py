import mongomock
import pytest

import providers
from pipeline import CommandContext, IntentInvalid, Trace, run_command, run_edits
from storage import PageStore


@pytest.fixture
def store():
    return PageStore(mongomock.MongoClient()["vlp-batch"]["pages"])


@pytest.fixture
def url(store):
    result = run_command("Create a page for Nordvik Dental with a hero and an FAQ",
                         "en", store, CommandContext(), None)
    return result["page"]["id"]


def save(store, url, changes):
    return run_edits(changes, "[save]", "en", store,
                     CommandContext(page_id=url), Trace("[save]"))


def versions(store, url):
    return [v["label"] for v in store.get(url, None)["versions"]]


def composed(page):
    sections = page["sections"] if isinstance(page, dict) else page
    return [s["type"] for s in sections
            if s["type"] not in ("header", "footer")]


def by_type(page, kind):
    sections = page["sections"] if isinstance(page, dict) else page
    return next(s for s in sections if s["type"] == kind)


def test_several_changes_land_as_one_version(store, url):
    result = save(store, url, [
        {"action": "setTheme", "args": {"primary": "#2f6f4e"}},
        {"action": "editContent",
         "args": {"section": "hero", "field": "title", "value": "Bright smiles"}},
        {"action": "editContent",
         "args": {"section": "faq", "field": "title", "value": "Questions"}},
    ])

    assert versions(store, url) == ["Initial draft", "3 changes"]
    assert result["page"]["theme"]["primary"] == "#2f6f4e"
    assert by_type(result["page"], "hero")["headline"] == "Bright smiles"
    assert by_type(result["page"], "faq")["heading"] == "Questions"


def test_two_changes_are_named_rather_than_counted(store, url):
    save(store, url, [
        {"action": "setTheme", "args": {"primary": "#2f6f4e"}},
        {"action": "editContent",
         "args": {"section": "hero", "field": "title", "value": "Bright smiles"}},
    ])
    assert versions(store, url)[-1] == "Updated colour scheme and edited hero headline"


def test_one_change_reads_as_itself(store, url):
    save(store, url, [
        {"action": "editContent",
         "args": {"section": "hero", "field": "title", "value": "Bright smiles"}},
    ])
    assert versions(store, url)[-1] == "Edited hero headline"


def test_a_batch_that_fails_writes_nothing(store, url):
    before = store.get(url, None)

    with pytest.raises(IntentInvalid):
        save(store, url, [
            {"action": "editContent",
             "args": {"section": "hero", "field": "title", "value": "Bright smiles"}},
            {"action": "editContent",
             "args": {"section": "promotion", "field": "title", "value": "Offer"}},
        ])

    after = store.get(url, None)
    assert after["sections"] == before["sections"]
    assert len(after["versions"]) == len(before["versions"])


def test_the_business_name_is_editable(store, url):
    result = save(store, url, [
        {"action": "setName", "args": {"value": "Nordvik Dental Care"}},
    ])

    assert result["page"]["name"] == "Nordvik Dental Care"
    assert result["brief"]["business"] == "Nordvik Dental Care"
    assert store.get(url, None)["name"] == "Nordvik Dental Care"
    assert versions(store, url)[-1] == "Renamed to Nordvik Dental Care"
    assert {s["name"] for s in result["page"]["sections"]
            if s["type"] in ("header", "footer")} == {"Nordvik Dental Care"}


def test_an_empty_name_is_refused(store, url):
    with pytest.raises(IntentInvalid, match="called"):
        save(store, url, [{"action": "setName", "args": {"value": "  "}}])


def rewrite(store, url, section, hint=None, **scope):
    args = {"section": section, **({"query": hint} if hint else {}), **scope}
    return run_command("[regenerateSection]", "en", store, CommandContext(page_id=url),
                       None, forced=("regenerateSection", args))


def test_a_section_can_be_written_again_in_place(store, url):
    before = store.get(url, None)
    faq = by_type(before["sections"], "faq")
    store._pages.update_one({"_id": url}, {"$set": {"sections": [
        {**s, "anchor": "questions"} if s["type"] == "faq" else s
        for s in before["sections"]]}})

    result = rewrite(store, url, "faq", "shorter")
    after = by_type(result["page"], "faq")
    assert result["message"] == "Done -- rewrote faq."
    assert versions(store, url)[-1] == "Rewrote faq"
    assert composed(result["page"]) == composed(before)
    assert after["variant"] == faq["variant"]
    assert after["anchor"] == "questions"
    assert after["provenance"] == "generated"
    assert after["reviewed"] is False


def test_rewriting_generated_claims_says_they_are_still_invented(store):
    created = run_command("Create a page for Nordvik Dental with a hero and testimonials",
                          "en", store, CommandContext(), None)
    result = rewrite(store, created["page"]["id"], "testimonials", "more real")
    assert result["message"].startswith("Done -- rewrote testimonials.")
    assert "still invented" in result["message"]


def test_a_rewrite_that_cannot_be_written_leaves_the_page_alone(store, url, monkeypatch):
    before = store.get(url, None)
    monkeypatch.setattr(providers.DEFAULT.lang, "generate_copy",
                        lambda section_type, brief: {})

    for scope in ({}, {"field": "title"}, {"path": "items.0"}):
        with pytest.raises(IntentInvalid, match="couldn't write a usable"):
            rewrite(store, url, "faq", **scope)

    after = store.get(url, None)
    assert after["sections"] == before["sections"]
    assert after["version"] == before["version"]
    assert versions(store, url) == [v["label"] for v in before["versions"]]


def test_the_chrome_cannot_be_rewritten(store, url):
    with pytest.raises(IntentInvalid, match="follows the rest of the page"):
        rewrite(store, url, "header")


def test_rewrites_use_the_brief_the_page_was_created_with(store, monkeypatch):
    seen = {}
    original = providers.DEFAULT.lang.generate_copy

    def spy(section_type, brief):
        seen[section_type] = dict(brief)
        return original(section_type, brief)

    monkeypatch.setattr(providers.DEFAULT.lang, "generate_copy", spy)
    created = run_command("Create a page for Nordvik Dental with a hero and an FAQ",
                          "en", store, CommandContext(), None)
    assert store.get(created["page"]["id"], None)["brief"]["business"] == "Nordvik Dental"
    store._pages.update_one({"_id": created["page"]["id"]},
                            {"$set": {"brief.audience": "nervous patients",
                                      "brief.goal": "book a check-up"}})

    rewrite(store, created["page"]["id"], "faq", "friendlier")
    assert seen["faq"]["audience"] == "nervous patients"
    assert seen["faq"]["goal"] == "book a check-up"
    assert seen["faq"]["tone"] == "friendlier"


def test_asking_to_change_a_section_without_saying_which_part_offers_a_rewrite(store, url):
    with pytest.raises(IntentInvalid, match='rewrite the faq'):
        save(store, url, [{"action": "editContent",
                           "args": {"section": "faq", "value": "make it real"}}])


def test_adding_a_section_that_exists_offers_a_rewrite(store, url):
    with pytest.raises(IntentInvalid, match='rewrite the faq'):
        run_command("[addSection]", "en", store, CommandContext(page_id=url), None,
                    forced=("addSection", {"type": "faq"}))


def test_a_rewrite_can_be_limited_to_one_field(store, url):
    before = by_type(store.get(url, None)["sections"], "hero")
    store._pages.update_one({"_id": url}, {"$set": {"sections": [
        {**s, "subhead": "Kept as it was"} if s["type"] == "hero" else s
        for s in store.get(url, None)["sections"]]}})

    result = rewrite(store, url, "hero", "shorter", field="headline")
    after = by_type(result["page"], "hero")
    assert versions(store, url)[-1] == "Rewrote hero headline"
    assert after["subhead"] == "Kept as it was"
    assert after["image"] == before["image"]
    assert after["button"] == before["button"]
    assert after["provenance"] == "generated"


def test_a_rewrite_can_be_limited_to_the_entries(store):
    created = run_command("Create a page for Nordvik Dental with a hero and testimonials",
                          "en", store, CommandContext(), None)
    page_id = created["page"]["id"]
    store._pages.update_one({"_id": page_id}, {"$set": {"sections": [
        {**s, "heading": "What patients say", "reviewed": True, "provenance": "edited"}
        if s["type"] == "testimonials" else s
        for s in store.get(page_id, None)["sections"]]}})

    result = rewrite(store, page_id, "testimonials", "more real", path="items")
    after = by_type(result["page"], "testimonials")
    assert versions(store, page_id)[-1] == "Rewrote every testimonial in testimonials"
    assert after["heading"] == "What patients say"
    assert after["items"]
    assert after["provenance"] == "generated" and after["reviewed"] is False
    assert "still invented" in result["message"]


def test_a_rewrite_can_be_limited_to_one_entry(store, url):
    before = by_type(store.get(url, None)["sections"], "faq")
    store._pages.update_one({"_id": url}, {"$set": {"sections": [
        {**s, "items": [{"question": "Keep me?", "answer": "Yes."}, *s["items"]]}
        if s["type"] == "faq" else s
        for s in store.get(url, None)["sections"]]}})

    result = rewrite(store, url, "faq", path="items.2")
    after = by_type(result["page"], "faq")
    assert versions(store, url)[-1] == "Rewrote question 3 in faq"
    assert after["items"][0] == {"question": "Keep me?", "answer": "Yes."}
    assert len(after["items"]) == len(before["items"]) + 1


def test_a_rewrite_of_something_that_is_not_there_is_refused(store, url):
    with pytest.raises(IntentInvalid, match="no 'plans.1' on this section"):
        rewrite(store, url, "faq", path="plans.1")


def test_a_section_or_part_named_in_the_wording_fills_a_slot_the_interpreter_dropped():
    from pipeline import infer_from_wording

    assert infer_from_wording("removeItem", {"path": "items.1"}, "Remove the second question") == \
        {"path": "items.1", "section": "faq"}
    assert infer_from_wording("moveItem", {"path": "items.0", "position": "down"},
                              "Swap the first two steps")["section"] == "process"
    assert infer_from_wording("moveSection", {}, "Put the FAQ before the reviews") == {}
    assert infer_from_wording("editContent", {"section": "hero", "value": "Baked Before Sunrise"},
                              "Change the hero headline to Baked Before Sunrise")["field"] == "headline"
    assert "field" not in infer_from_wording("editContent", {"section": "faq", "value": "make it real"},
                                             "Change the faq to make it real")
    assert infer_from_wording("editContent", {"section": "hero", "value": "Go", "path": "button.label"},
                              "Change the hero button to Go") == \
        {"section": "hero", "value": "Go", "path": "button.label"}
    assert infer_from_wording("setTheme", {"style": "green"}, "Make the benefits green") == {"style": "green"}
    assert infer_from_wording("removeItem", {"section": "faq", "path": "items.1"},
                              "Remove the second step")["section"] == "faq"


def test_paths_positions_types_variants_and_icons_come_from_the_wording_when_dropped():
    from icon_selector import build_icon_service
    from pipeline import infer_from_wording, section_holding

    icons = build_icon_service()
    assert infer_from_wording("removeItem", {}, "Remove the second question") == \
        {"section": "faq", "path": "items.1"}
    assert infer_from_wording("removeItem", {}, "Drop question two")["path"] == "items.1"
    assert infer_from_wording("moveItem", {}, "Move the first step down one") == \
        {"section": "process", "path": "items.0", "position": "down"}
    assert infer_from_wording("moveSection", {"section": "faq"}, "Shift the FAQ higher")["position"] == "up"
    assert infer_from_wording("moveSection", {"section": "faq"}, "Put the FAQ before the reviews")["position"] == \
        "before testimonials"
    assert infer_from_wording("moveSection", {"section": "faq"}, "Put the FAQ at the bottom")["position"] == "bottom"
    assert infer_from_wording("setIcon", {}, "Put a star on the first benefit", icons) == \
        {"section": "benefits", "path": "items.0", "icon": "star"}
    assert infer_from_wording("setVariant", {}, "Make the hero full-bleed") == \
        {"section": "hero", "variant": "full-bleed"}
    assert infer_from_wording("addSection", {}, "Add a testimonials section") == {"type": "testimonials"}
    assert infer_from_wording("addSection", {}, "Can't you add more sections?") == {}
    assert infer_from_wording("addSection", {"type": "faq"}, "Add a testimonials section") == {"type": "faq"}

    page = [{"type": "hero", "headline": "Hi"},
            {"type": "process", "items": [{"title": "Order online"}, {"title": "We bake"}]},
            {"type": "faq", "items": [{"question": "Do you deliver?"}]}]
    assert section_holding(page, "items.order online") == {"section": "process"}
    assert section_holding(page, "items.do you deliver") == {"section": "faq"}
    assert section_holding(page, "items.1") == {}
    assert section_holding(page, "items.nothing here") == {}
