import mongomock
import pytest
from pydantic import ValidationError

import providers
from editor import EditError, set_theme
from pipeline import CommandContext, run_command, run_create_page
from storage import PageStore
from theme import (
    BODY_CONTRAST,
    LARGE_CONTRAST,
    ThemeChoice,
    brand_colors,
    build_theme,
    contrast_ratio,
    expand,
    from_hue,
    relative_luminance,
    validate_theme,
    _to_hsl,
)


def saturation(color: str) -> float:
    return _to_hsl(color)[1]


def lightness(color: str) -> float:
    return _to_hsl(color)[2]

BLUE = ThemeChoice(hue="test", name="Test Blue", primary="#0369a1", accent="#075985",
                   background="#ffffff")


@pytest.fixture
def store():
    return PageStore(mongomock.MongoClient()["vlp-theme"]["pages"])


def create(store, command="Create a page for Nordvik Dental with a hero and an FAQ"):
    return run_command(command, "en", store, CommandContext(), None)


def test_three_colours_become_a_full_token_set():
    theme = expand(BLUE)
    assert theme.primary == "#0369a1"
    colors = {key: value for key, value in theme.model_dump().items()
              if key.endswith(("primary", "accent", "foreground", "background",
                               "muted", "border", "light", "strong"))}
    assert len(colors) == 11
    assert all(value.startswith("#") for value in colors.values())


def test_brand_colours_round_trip_through_the_tokens():
    assert brand_colors(expand(BLUE)) == {
        "primary": "#0369a1", "accent": "#075985", "background": "#ffffff"}


def test_derived_shades_sit_either_side_of_the_primary():
    theme = expand(BLUE)
    assert contrast_ratio(theme.primary_strong, "#ffffff") > \
        contrast_ratio(theme.primary, "#ffffff")
    assert contrast_ratio(theme.primary_light, "#ffffff") < \
        contrast_ratio(theme.primary, "#ffffff")


def test_a_dark_background_flips_the_neutrals():
    theme, _ = build_theme(ThemeChoice(hue="test", name="Night", primary="#8ab4f8",
                                       accent="#f0b429", background="#0b1020"))
    assert contrast_ratio(theme.foreground, theme.background) >= BODY_CONTRAST
    assert relative_luminance(theme.foreground) > relative_luminance(theme.background)


def test_unreadable_brand_colour_is_repaired_not_rejected():
    theme, notes = build_theme(ThemeChoice(hue="test", name="Neon", primary="#ffe600",
                                           accent="#fffb8f", background="#ffffff"))
    assert notes
    assert contrast_ratio(theme.primary, theme.background) >= LARGE_CONTRAST
    assert contrast_ratio(theme.accent, theme.background) >= LARGE_CONTRAST


def test_repairing_a_brand_colour_refreshes_its_foreground():
    theme, _ = build_theme(ThemeChoice(hue="test", name="Neon", primary="#ffe600",
                                       accent="#ffe600", background="#ffffff"))
    assert contrast_ratio(theme.accent_foreground, theme.accent) >= BODY_CONTRAST


def test_every_hue_produces_a_legible_palette():
    for hue in range(0, 360, 15):
        theme, _ = build_theme(from_hue(hue))
        tokens = theme.model_dump()
        for fg, bg, minimum in [
            ("foreground", "background", BODY_CONTRAST),
            ("muted_foreground", "muted", BODY_CONTRAST),
            ("primary_foreground", "primary", BODY_CONTRAST),
            ("accent_foreground", "accent", BODY_CONTRAST),
            ("primary", "background", LARGE_CONTRAST),
        ]:
            ratio = contrast_ratio(tokens[fg], tokens[bg])
            assert ratio >= minimum, f"hue {hue}: {fg} on {bg} is {ratio}"


def test_a_muddy_model_palette_is_made_to_look_chosen():
    muddy = ThemeChoice(hue="test", name="Default-ish", primary="#2e4053", accent="#2f4f4f",
                        background="#ffffff")
    theme, _ = build_theme(muddy, refine=True)

    assert theme.primary != "#2e4053"
    assert saturation(theme.primary) >= 0.3
    assert 0.3 <= lightness(theme.primary) <= 0.6


def test_a_colour_the_user_typed_is_left_alone():
    theme, _ = build_theme(ThemeChoice(hue="test", name="Mine", primary="#2e4053",
                                       accent="#2f4f4f", background="#ffffff"))
    assert theme.primary == "#2e4053"


def test_a_deliberate_neutral_survives_refinement():
    theme, _ = build_theme(ThemeChoice(hue="test", name="Slate", primary="#6b7280",
                                       accent="#374151", background="#ffffff"),
                           refine=True)
    assert theme.primary == "#6b7280"


def test_a_validated_theme_is_stable():
    once, _ = build_theme(BLUE)
    twice, notes = validate_theme(once)
    assert twice == once and notes == []


def test_hex_is_extracted_from_a_sloppy_response():
    choice = ThemeChoice(hue="test", name="Loose", primary="0369A1", accent=" #075985 ",
                         background="the page is #FFF")
    assert (choice.primary, choice.accent, choice.background) == \
        ("#0369a1", "#075985", "#fff")


def test_a_colour_name_is_not_a_colour():
    with pytest.raises(ValidationError):
        ThemeChoice(hue="test", name="Words", primary="blue", accent="#075985",
                    background="#ffffff")


def test_a_created_page_carries_a_validated_theme(store):
    result = create(store)
    theme = result["page"]["theme"]
    assert theme["name"]
    assert result["validation"]["gates"]["theme"] in ("ok", "repaired")
    assert contrast_ratio(theme["foreground"], theme["background"]) >= BODY_CONTRAST


def test_the_theme_is_chosen_before_the_page_is_assembled():
    result = run_create_page("Create a page for Nordvik Dental with a hero")
    tools = [s["call"]["tool"] for s in result["_trace"]["steps"]]
    assert tools.index("select_theme") < tools.index("assemble_page")
    assert "select_theme" in result["plan"]["operations"]


def test_a_failed_theme_leaves_the_page_themeless(monkeypatch, store):
    monkeypatch.setattr(providers.DEFAULT.lang, "generate_theme",
                        lambda brief, hint=None: {})
    result = create(store)
    assert result["page"]["theme"] is None
    assert result["validation"]["gates"]["theme"] == "defaulted"


def test_an_unusable_theme_is_defaulted_not_raised(monkeypatch, store):
    monkeypatch.setattr(providers.DEFAULT.lang, "generate_theme",
                        lambda brief, hint=None: {"name": "Bad", "primary": "green",
                                                  "accent": "#fff", "background": "#fff"})
    result = create(store)
    assert result["page"]["theme"] is None
    assert result["validation"]["gates"]["theme"] == "defaulted"


def test_the_theme_is_snapshotted_with_the_version(store):
    result = create(store)
    doc = store.get(result["page"]["id"], None)
    assert doc["versions"][0]["theme"] == result["page"]["theme"]


def test_an_explicit_colour_is_applied_and_versioned(store):
    url = create(store)["page"]["id"]
    result = run_command("[setTheme]", "en", store, CommandContext(page_id=url),
                         None, forced=("setTheme", {"primary": "#2f6f4e"}))

    assert result["page"]["theme"]["primary"] == "#2f6f4e"
    assert result["page"]["theme"]["name"] == "Custom"
    assert store.get(url, None)["theme"]["primary"] == "#2f6f4e"
    assert len(store.get(url, None)["versions"]) == 2


def test_changing_one_colour_rederives_the_others(store):
    url = create(store)["page"]["id"]
    before = store.get(url, None)["theme"]
    after = run_command("[setTheme]", "en", store, CommandContext(page_id=url),
                        None, forced=("setTheme", {"primary": "#2f6f4e"}))["page"]["theme"]

    assert after["background"] == before["background"]
    assert after["primary_strong"] != before["primary_strong"]
    assert after["muted"] != before["muted"]


def test_a_spoken_style_asks_the_model_for_a_new_palette(store):
    url = create(store)["page"]["id"]
    before = store.get(url, None)["theme"]
    after = run_command("make the page greener", "en", store,
                        CommandContext(page_id=url), None,
                        forced=("setTheme", {"style": "greener"}))["page"]["theme"]
    assert after != before


def test_a_colour_that_is_not_a_colour_is_refused():
    with pytest.raises(EditError):
        set_theme({"primary": "#0369a1", "accent": "#075985", "background": "#ffffff"},
                  {"primary": "forest green"})


def test_an_empty_edit_is_refused():
    with pytest.raises(EditError):
        set_theme(None, {})


def test_publishing_applies_the_contrast_gate_to_the_stored_theme(store):
    url = create(store)["page"]["id"]
    doc = store.get(url, None)
    shouting = {**doc["theme"], "primary": "#ffe600", "background": "#ffffff"}
    store.append_version(url, None, 1, "Shouting", doc["sections"], shouting)
    store.publish(url, None)

    published = store.published(doc["url"])["theme"]
    assert published["primary"] != "#ffe600"
    assert contrast_ratio(published["primary"], published["background"]) >= LARGE_CONTRAST


def test_restoring_a_version_restores_its_palette(store):
    url = create(store)["page"]["id"]
    original = store.get(url, None)["theme"]
    run_command("[setTheme]", "en", store, CommandContext(page_id=url), None,
                forced=("setTheme", {"primary": "#2f6f4e"}))

    restored = store.restore_version(url, None, 1)
    assert restored.theme.model_dump() == original
