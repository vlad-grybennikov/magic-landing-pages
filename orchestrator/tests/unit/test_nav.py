import pytest
from pydantic import ValidationError

from editor import EditError, _sync_nav, edit_at_path
from schema import NOT_IN_NAV, SECTION_LABELS, SECTION_ORDER, Button, nav_links


def page(*types: str) -> list[dict]:
    return [{"type": kind, "anchor": kind} for kind in types]


def header_with(links: list[dict]) -> dict:
    return {"type": "header", "anchor": "header", "links": links}


def test_links_point_at_the_sections_the_page_has():
    links = nav_links(page("hero", "about", "faq"))
    assert links == [{"label": "About", "href": "#about"},
                     {"label": "FAQ", "href": "#faq"}]


def test_the_frame_and_the_asks_are_not_in_the_navigation():
    links = nav_links(page(*SECTION_ORDER))
    assert not {link["href"].lstrip("#") for link in links} & NOT_IN_NAV


def test_a_section_anchored_by_another_name_is_linked_by_that_name():
    sections = [{"type": "process", "anchor": "roasting"}]
    assert nav_links(sections) == [{"label": "How it works",
                                    "href": "#roasting"}]


def test_every_section_type_has_a_label():
    assert set(SECTION_LABELS) == set(SECTION_ORDER)


def test_a_removed_section_takes_its_link_with_it():
    sections = [header_with(nav_links(page("about", "faq"))), *page("about")]
    assert _sync_nav(sections)[0]["links"] == [{"label": "About",
                                               "href": "#about"}]


def test_an_added_section_gains_a_link_in_page_order():
    sections = [header_with([{"label": "FAQ", "href": "#faq"}]),
                *page("about", "faq")]
    links = _sync_nav(sections, added="about")[0]["links"]
    assert [link["href"] for link in links] == ["#about", "#faq"]


def test_a_renamed_link_keeps_its_name():
    sections = [header_with([{"label": "Our roasting", "href": "#process"},
                             {"label": "FAQ", "href": "#faq"}]),
                *page("process", "faq", "contact")]
    labels = [link["label"]
              for link in _sync_nav(sections, added="contact")[0]["links"]]
    assert labels == ["Our roasting", "FAQ", "Contact"]


def test_a_page_that_wants_no_navigation_keeps_none():
    sections = [header_with([]), *page("about")]
    assert _sync_nav(sections)[0]["links"] == []


def test_a_link_the_user_deleted_does_not_come_back():
    sections = [header_with([{"label": "FAQ", "href": "#faq"}]),
                *page("about", "faq", "contact")]
    links = _sync_nav(sections, added="contact")[0]["links"]
    assert [link["href"] for link in links] == ["#faq", "#contact"]


def test_renaming_an_anchor_moves_the_links_with_it():
    sections = [header_with([{"label": "About", "href": "#about"}]),
                *page("about")]
    updated, _ = edit_at_path(sections, "about", "anchor", "our-story")
    assert updated[0]["links"] == [{"label": "About", "href": "#our-story"}]


def test_renaming_an_anchor_leaves_other_links_alone():
    sections = [header_with([{"label": "About", "href": "#about"},
                             {"label": "FAQ", "href": "#faq"}]),
                *page("about", "faq")]
    updated, _ = edit_at_path(sections, "about", "anchor", "our-story")
    assert updated[0]["links"][1] == {"label": "FAQ", "href": "#faq"}


def test_an_anchor_a_page_never_had_can_be_given():
    sections = [header_with([{"label": "About", "href": "#about"}]),
                {"type": "about", "anchor": None}]
    updated, _ = edit_at_path(sections, "about", "anchor", "our-story")
    assert updated[1]["anchor"] == "our-story"
    assert updated[0]["links"][0]["href"] == "#our-story"


def test_two_sections_cannot_share_an_anchor():
    sections = [header_with([]), *page("about", "faq")]
    with pytest.raises(EditError):
        edit_at_path(sections, "about", "anchor", "faq")


@pytest.mark.parametrize("href", [
    "https://coffeehug.co.uk/shop", "mailto:hello@coffeehug.co.uk",
    "tel:+44 113 975 8822", "#contact", "#", "/menu", "/",
])
def test_a_link_may_go_to_the_web_an_address_or_this_page(href):
    assert Button(label="Go", href=href).href == href


@pytest.mark.parametrize("href", [
    "javascript:alert(1)", "data:text/html,x", "about", "http://x y", "",
])
def test_a_link_may_not_run_or_go_nowhere_in_particular(href):
    with pytest.raises(ValidationError):
        Button(label="Go", href=href)
