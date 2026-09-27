import pytest

from editor import EditError, edit_at_path


def page():
    return [
        {"type": "hero", "headline": "H", "subhead": "S",
         "image": {"src": "/a.jpg", "alt": "A photo"},
         "button": {"label": "Go", "href": "#"}},
        {"type": "benefits", "heading": "B", "items": [
            {"icon": {"src": "/i.svg", "alt": ""}, "title": "One",
             "caption": "First"},
            {"icon": {"src": "/j.svg", "alt": ""}, "title": "Two",
             "caption": "Second"},
        ]},
    ]


def test_a_section_field():
    updated, _ = edit_at_path(page(), "hero", "headline", "New")
    assert updated[0]["headline"] == "New"


def test_a_value_inside_a_list():
    updated, _ = edit_at_path(page(), "benefits", "items.1.caption", "Changed")
    assert updated[1]["items"][1]["caption"] == "Changed"
    assert updated[1]["items"][0]["caption"] == "First"


def test_a_button_label():
    updated, _ = edit_at_path(page(), "hero", "button.label", "Book")
    assert updated[0]["button"]["label"] == "Book"


def test_markdown_is_stored_as_written():
    updated, _ = edit_at_path(page(), "benefits", "items.0.title", "**Bold**")
    assert updated[1]["items"][0]["title"] == "**Bold**"


def test_editing_does_not_mutate_the_original():
    original = page()
    edit_at_path(original, "hero", "headline", "New")
    assert original[0]["headline"] == "H"


@pytest.mark.parametrize("path", ["image.src", "image.alt"])
def test_a_picture_is_replaced_rather_than_typed(path):
    with pytest.raises(EditError, match="replaced rather than typed"):
        edit_at_path(page(), "hero", path, "http://example.com/x.jpg")


def test_an_icon_inside_an_item_is_refused_too():
    with pytest.raises(EditError, match="replaced rather than typed"):
        edit_at_path(page(), "benefits", "items.0.icon.src", "/evil.svg")


def test_a_path_onto_an_object_is_refused():
    with pytest.raises(EditError, match="isn't a piece of text"):
        edit_at_path(page(), "hero", "button", "x")


def test_a_path_onto_a_list_is_refused():
    with pytest.raises(EditError, match="isn't a piece of text"):
        edit_at_path(page(), "benefits", "items", "x")


def test_an_index_past_the_end_is_refused():
    with pytest.raises(EditError, match="There is no"):
        edit_at_path(page(), "benefits", "items.9.title", "x")


def test_a_field_the_section_does_not_have_is_refused():
    with pytest.raises(EditError, match="There is no"):
        edit_at_path(page(), "hero", "nonesuch", "x")


def test_attributes_are_not_reachable():
    for path in ("__class__", "__dict__", "items.0.__class__"):
        with pytest.raises(EditError):
            edit_at_path(page(), "benefits", path, "x")


def test_a_path_deeper_than_the_data_is_refused():
    with pytest.raises(EditError, match="can't find"):
        edit_at_path(page(), "hero", "a.b.c.d.e.f.g", "x")


def test_an_empty_value_on_a_required_field_is_refused():
    with pytest.raises(EditError, match="can't be empty"):
        edit_at_path(page(), "hero", "headline", "")


def test_clearing_an_optional_field_leaves_it_out():
    updated, label = edit_at_path(page(), "hero", "subhead", "")
    assert updated[0]["subhead"] is None
    assert label == "Cleared hero subhead"


def test_clearing_a_required_field_inside_an_optional_part_drops_the_part():
    sections = [{"type": "services", "heading": "What we do", "items": [
        {"title": "Bread", "caption": "Daily.", "image": {"src": "/a.jpg"},
         "button": {"label": "See bakes"}},
        {"title": "Cakes", "caption": "To order.", "image": {"src": "/b.jpg"}},
    ]}]
    updated, _ = edit_at_path(sections, "services", "items.0.button.label", "")
    assert updated[0]["items"][0]["button"] is None


def test_clearing_a_required_entry_field_says_to_remove_the_entry():
    sections = [{"type": "benefits", "heading": "Why", "items": [
        {"icon": {"src": "/i.svg"}, "title": "Fast", "caption": "Quick."}] * 3}]
    with pytest.raises(EditError, match="remove the benefit"):
        edit_at_path(sections, "benefits", "items.0.title", "")


def test_a_rating_is_written_as_a_number():
    sections = [{"type": "testimonials", "items": [
        {"name": "Ann", "rating": 5, "content": "Great."}]}]
    updated, _ = edit_at_path(sections, "testimonials", "items.0.rating", "3")
    assert updated[0]["items"][0]["rating"] == 3


def test_a_rating_refuses_words():
    sections = [{"type": "testimonials", "items": [
        {"name": "Ann", "rating": 5, "content": "Great."}]}]
    with pytest.raises(EditError, match="is a number"):
        edit_at_path(sections, "testimonials", "items.0.rating", "five")
