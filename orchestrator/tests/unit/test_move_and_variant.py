import pytest

from editor import EditError, add_item, move_item, move_section, remove_item, set_variant
from layouts import VARIANTS


def page():
    return [
        {"type": "header", "name": "Fernside", "icon": {"src": "/i.svg"}},
        {"type": "hero", "headline": "H", "image": {"src": "/a.jpg"},
         "button": {"label": "Go"}, "variant": "stacked"},
        {"type": "benefits", "heading": "B", "items": [], "variant": "grid-plain"},
        {"type": "gallery", "images": [], "variant": "grid-three"},
        {"type": "faq", "heading": "Q", "items": [], "variant": "accordion"},
        {"type": "footer", "name": "Fernside", "icon": {"src": "/i.svg"}},
    ]


def order(sections):
    return [s["type"] for s in sections]


@pytest.mark.parametrize("said,expected", [
    ("up", ["header", "hero", "gallery", "benefits", "faq", "footer"]),
    ("down", ["header", "hero", "benefits", "faq", "gallery", "footer"]),
    ("to the top", ["header", "gallery", "hero", "benefits", "faq", "footer"]),
    ("to the bottom", ["header", "hero", "benefits", "faq", "gallery", "footer"]),
])
def test_a_section_moves_where_it_was_told(said, expected):
    updated, _ = move_section(page(), "gallery", said)
    assert order(updated) == expected


def test_a_named_neighbour_beats_the_direction_word():
    updated, _ = move_section(page(), "hero", "before faq")
    assert order(updated) == ["header", "benefits", "gallery", "hero", "faq", "footer"]


def test_moving_to_the_top_stops_below_the_header():
    updated, _ = move_section(page(), "faq", "top")
    assert order(updated)[0] == "header"
    assert order(updated)[1] == "faq"


def test_moving_to_the_bottom_stops_above_the_footer():
    updated, _ = move_section(page(), "hero", "bottom")
    assert order(updated)[-1] == "footer"
    assert order(updated)[-2] == "hero"


def test_moving_up_from_the_top_is_refused_rather_than_silently_ignored():
    at_top, _ = move_section(page(), "faq", "top")
    with pytest.raises(EditError, match="already there"):
        move_section(at_top, "faq", "up")


@pytest.mark.parametrize("pinned", ["header", "footer"])
def test_the_frame_cannot_be_moved(pinned):
    with pytest.raises(EditError, match="always in the same place"):
        move_section(page(), pinned, "up")


def test_an_unrecognised_position_is_refused_not_guessed():
    with pytest.raises(EditError, match="try up, down"):
        move_section(page(), "hero", "sideways")


def test_no_position_asks_rather_than_guessing():
    with pytest.raises(EditError, match="Where should it go"):
        move_section(page(), "hero", None)


def test_moving_does_not_mutate_the_original():
    original = page()
    move_section(original, "gallery", "top")
    assert order(original) == ["header", "hero", "benefits", "gallery", "faq",
                               "footer"]


def test_a_named_layout_is_applied():
    updated, label = set_variant(page(), "hero", "full-bleed")
    assert updated[1]["variant"] == "full-bleed"
    assert "full-bleed" in label


def test_a_layout_name_tolerates_spelling():
    updated, _ = set_variant(page(), "hero", " Full_Bleed ")
    assert updated[1]["variant"] == "full-bleed"


def test_no_layout_named_steps_to_the_next_one():
    updated, _ = set_variant(page(), "hero", None)
    assert updated[1]["variant"] == VARIANTS["hero"][1]


def test_cycling_wraps_round_the_end():
    sections = page()
    sections[1]["variant"] = VARIANTS["hero"][-1]
    updated, _ = set_variant(sections, "hero", None)
    assert updated[1]["variant"] == VARIANTS["hero"][0]


def test_another_types_layout_is_refused_with_the_real_ones():
    with pytest.raises(EditError, match="isn't a hero layout"):
        set_variant(page(), "hero", "three-cards")


def test_the_layout_it_already_uses_is_refused():
    with pytest.raises(EditError, match="already uses"):
        set_variant(page(), "hero", "stacked")


def test_the_frame_has_layouts_of_its_own():
    updated, _ = set_variant(page(), "header", "minimal")
    assert updated[0]["variant"] == "minimal"


def test_changing_a_layout_leaves_the_copy_alone():
    updated, _ = set_variant(page(), "hero", "full-bleed")
    assert updated[1]["headline"] == "H"
    assert updated[1]["button"] == {"label": "Go"}


def steps():
    return [{"type": "process", "heading": "How", "items": [
        {"title": "One", "caption": "First."},
        {"title": "Two", "caption": "Second."},
        {"title": "Three", "caption": "Third."},
    ]}]


def test_an_entry_moves_down_past_its_neighbour():
    updated, label = move_item(steps(), "process", "items.0", "down")
    assert [i["title"] for i in updated[0]["items"]] == ["Two", "One", "Three"]
    assert label == "Moved step 1 to 2"


def test_an_entry_moves_to_the_top():
    updated, _ = move_item(steps(), "process", "items.2", "to the top")
    assert [i["title"] for i in updated[0]["items"]] == ["Three", "One", "Two"]


def test_the_builder_names_the_place_outright():
    updated, _ = move_item(steps(), "process", "items.0", "2")
    assert [i["title"] for i in updated[0]["items"]] == ["Two", "Three", "One"]


def test_moving_past_the_end_is_refused_as_already_there():
    with pytest.raises(EditError, match="already there"):
        move_item(steps(), "process", "items.2", "down")


def test_a_section_without_a_list_cannot_reorder():
    with pytest.raises(EditError, match="There is no"):
        move_item([{"type": "hero", "headline": "Hi", "image": {"src": "/a.jpg"},
                    "button": {"label": "Go"}}], "hero", "items.0", "up")


def footer():
    return [{"type": "footer", "name": "Marlow", "icon": {"src": "/i.svg"},
             "links": [{"label": "About", "href": "#about"}],
             "contacts": [{"label": "0161 881 4042", "href": "tel:0161 881 4042"},
                          {"label": "hi@marlow.co.uk", "href": "mailto:hi@marlow.co.uk"}]}]


def test_a_footer_has_no_list_of_its_own():
    with pytest.raises(EditError, match="no list"):
        add_item(footer(), "footer", {"label": "x", "href": "#"})


def test_an_entry_is_added_to_the_list_the_path_names():
    updated, label = add_item(footer(), "footer", {"label": "Map", "href": "#contact"},
                              "contacts")
    assert [c["label"] for c in updated[0]["contacts"]][-1] == "Map"
    assert label == "Added contact 3"


def test_an_entry_is_moved_within_the_list_the_path_names():
    updated, _ = move_item(footer(), "footer", "contacts.1", "up")
    assert updated[0]["contacts"][0]["label"] == "hi@marlow.co.uk"
    assert [l["label"] for l in updated[0]["links"]] == ["About"]


def test_an_entry_is_removed_from_the_list_the_path_names():
    updated, label = remove_item(footer(), "footer", "contacts.0")
    assert [c["label"] for c in updated[0]["contacts"]] == ["hi@marlow.co.uk"]
    assert label == "Removed contact 1"


def test_a_list_inside_an_entry_is_reachable_too():
    plans = [{"type": "pricing", "heading": "Plans", "plans": [
        {"name": "Loaf", "price": "£16", "features": ["Bread", "Pastry"],
         "button": {"label": "Go"}}]}]
    updated, _ = move_item(plans, "pricing", "plans.0.features.1", "up")
    assert updated[0]["plans"][0]["features"] == ["Pastry", "Bread"]
    updated, _ = add_item(plans, "pricing", "Coffee", "plans.0.features")
    assert updated[0]["plans"][0]["features"][-1] == "Coffee"


def test_entries_can_be_named_instead_of_counted():
    updated, label = move_item(steps(), "process", "items.one", "after items.two")
    assert [i["title"] for i in updated[0]["items"]] == ["Two", "One", "Three"]
    assert label == "Moved step 1 to 2"

    updated, _ = move_item(steps(), "process", "items.Three", "before One")
    assert [i["title"] for i in updated[0]["items"]] == ["Three", "One", "Two"]

    updated, _ = move_item(steps(), "process", "items.0", "below Two")
    assert [i["title"] for i in updated[0]["items"]] == ["Two", "One", "Three"]

    four = steps()
    four[0]["items"].append({"title": "Four", "caption": "Fourth."})
    updated, label = remove_item(four, "process", "items.two")
    assert [i["title"] for i in updated[0]["items"]] == ["One", "Three", "Four"]
    assert label == "Removed step 2"

    with pytest.raises(EditError, match="There is no step at"):
        move_item(steps(), "process", "items.four", "up")
    updated, _ = move_item(steps(), "process", "items.0", "after items.four")
    assert [i["title"] for i in updated[0]["items"]] == ["Two", "One", "Three"]


def test_named_entries_tolerate_punctuation_and_partial_names():
    faq = [{"type": "faq", "heading": "Q", "items": [
        {"question": "Do you deliver?", "answer": "Yes."},
        {"question": "Gluten free?", "answer": "Some."},
        {"question": "Do you cater?", "answer": "No."},
    ]}]
    updated, _ = remove_item(faq, "faq", "items.gluten free")
    assert [i["question"] for i in updated[0]["items"]] == ["Do you deliver?", "Do you cater?"]
    updated, _ = remove_item(faq, "faq", "items.cater")
    assert [i["question"] for i in updated[0]["items"]] == ["Do you deliver?", "Gluten free?"]
    with pytest.raises(EditError, match="There is no"):
        remove_item(faq, "faq", "items.do you")
