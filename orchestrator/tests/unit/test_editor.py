import pytest

from editor import (
    EditError,
    add_section,
    edit_content,
    remove_section,
    replace_image,
    resolve_section,
)

HERO = {"type": "hero", "headline": "Old headline", "subhead": "Old subhead",
        "image": {"src": "/a.jpg", "alt": ""}, "button": {"label": "Go"}}
FAQ = {"type": "faq", "heading": "Questions", "items": [{"question": "Q", "answer": "A"}]}
PROMO = {"type": "promotion", "title": "Offer", "description": "D",
         "button": {"label": "Claim"}}


def page():
    return [dict(HERO), dict(FAQ)]


@pytest.mark.parametrize("spoken", ["hero", "Hero", "the banner", "banner"])
def test_section_names_tolerate_speech(spoken):
    assert resolve_section(page(), spoken) == 0


@pytest.mark.parametrize("spoken", ["faq", "FAQs", "questions"])
def test_plurals_and_synonyms_resolve(spoken):
    assert resolve_section(page(), spoken) == 1


def test_the_header_is_its_own_section():
    from schema import section_type_for
    assert section_type_for("the header") == "header"
    with pytest.raises(EditError, match="no header section"):
        resolve_section(page(), "the header")


def test_unknown_section_name_is_refused():
    with pytest.raises(EditError, match="don't know"):
        resolve_section(page(), "carousel")


def test_section_absent_from_this_page_is_refused():
    with pytest.raises(EditError, match="no promotion section"):
        resolve_section(page(), "promotion")


def test_missing_section_name_asks_rather_than_guessing():
    with pytest.raises(EditError, match="Which section"):
        resolve_section(page(), None)


def test_edit_headline():
    updated, label = edit_content(page(), "hero", "headline", "New headline")
    assert updated[0]["headline"] == "New headline"
    assert label == "Edited hero headline"


def test_edit_does_not_mutate_the_original():
    original = page()
    edit_content(original, "hero", "headline", "New")
    assert original[0]["headline"] == "Old headline"


def test_button_label_is_reached_through_its_object():
    updated, _ = edit_content(page(), "hero", "cta", "Book now")
    assert updated[0]["button"]["label"] == "Book now"


def test_title_means_the_sections_own_headline():
    assert edit_content(page(), "hero", "title", "X")[0][0]["headline"] == "X"
    assert edit_content(page(), "faq", "title", "X")[0][1]["heading"] == "X"
    assert edit_content([dict(PROMO)], "promotion", "headline", "X")[0][0]["title"] == "X"


def test_field_the_section_does_not_have_is_refused():
    with pytest.raises(EditError, match="can't change"):
        edit_content(page(), "faq", "button", "X")


def test_empty_value_on_a_required_field_is_refused():
    with pytest.raises(EditError, match="can't be empty"):
        edit_content(page(), "hero", "headline", "")


def test_replace_hero_image():
    choice = {"src": "/new.jpg", "alt": "New", "category": "bakery"}
    updated, label = replace_image(page(), "hero", choice)
    assert updated[0]["image"] == choice
    assert label == "Replaced hero image"


def test_sections_without_a_photo_are_refused():
    with pytest.raises(EditError, match="doesn't have a photo"):
        replace_image(page(), "faq", {"src": "/x.jpg"})


def test_added_section_lands_in_canonical_order():
    updated, label = add_section(page(), "benefits", {"type": "benefits"})
    assert [s["type"] for s in updated] == ["hero", "benefits", "faq"]
    assert label == "Added benefits section"


def test_explicit_position_overrides_canonical_order():
    updated, _ = add_section(page(), "benefits", {"type": "benefits"}, "at the bottom")
    assert [s["type"] for s in updated] == ["hero", "faq", "benefits"]
    updated, _ = add_section(page(), "benefits", {"type": "benefits"}, "at the top")
    assert [s["type"] for s in updated] == ["benefits", "hero", "faq"]


def test_duplicate_section_is_refused():
    with pytest.raises(EditError, match="already has"):
        add_section(page(), "hero", {"type": "hero"})


def test_remove_section():
    updated, label = remove_section(page(), "faq")
    assert [s["type"] for s in updated] == ["hero"]
    assert label == "Removed faq section"


def test_removing_the_last_section_is_refused_with_a_reason():
    with pytest.raises(EditError, match="at least one"):
        remove_section([dict(HERO)], "hero")


def test_a_button_can_be_added_where_the_section_had_none():
    contact = {"type": "contact", "heading": "Find us", "button": None,
               "details": [{"label": "Phone", "value": "0161 496 0000"}]}
    updated, label = edit_content([contact], "contact", "button", "Call us")

    assert updated[0]["button"] == {"label": "Call us"}
    assert label == "Edited contact button"


def test_setting_a_button_keeps_its_link():
    hero = {**HERO, "button": {"label": "Go", "href": "/book"}}
    updated, _ = edit_content([hero], "hero", "button", "Book now")
    assert updated[0]["button"] == {"label": "Book now", "href": "/book"}


CONTACT = {"type": "contact", "heading": "Find us", "details": [
    {"label": "Phone", "value": "0161 496 0000"},
    {"label": "Email", "value": "hello@example.com"},
]}


def test_an_entry_can_be_addressed_by_position():
    updated, _ = edit_content([dict(CONTACT)], "contact", None,
                              "order@openfarm.com", path="details.1.value")
    assert updated[0]["details"][1]["value"] == "order@openfarm.com"


def test_an_entry_can_be_addressed_by_what_it_is_called():
    updated, label = edit_content([dict(CONTACT)], "contact", None,
                                  "order@openfarm.com", path="details.email.value")

    assert updated[0]["details"][1]["value"] == "order@openfarm.com"
    assert updated[0]["details"][0]["value"] == "0161 496 0000"
    assert label == "Edited contact details email value"


def test_an_entry_that_is_not_there_is_refused():
    with pytest.raises(EditError, match="no 'details.fax.value'"):
        edit_content([dict(CONTACT)], "contact", None, "x", path="details.fax.value")
