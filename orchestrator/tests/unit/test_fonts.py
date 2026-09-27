import re
from pathlib import Path

import pytest

from fonts import (
    DEFAULT_PAIR,
    FONT_PAIRS,
    PAIR_NAMES,
    describe_pairs,
    fallback_pair,
    normalize_pair,
)

FONTS_TS = (Path(__file__).resolve().parents[3]
            / "frontend" / "src" / "lib" / "fonts.ts")


def test_default_pairing_exists():
    assert DEFAULT_PAIR in FONT_PAIRS


def test_every_pairing_names_two_families():
    for name, pair in FONT_PAIRS.items():
        assert pair.heading and pair.body, name


def test_every_pairing_says_what_it_is_for():
    for name, pair in FONT_PAIRS.items():
        assert len(pair.character) > 20, name


def test_the_prompt_lists_every_pairing():
    listed = describe_pairs()
    for name in PAIR_NAMES:
        assert f"    {name} -- " in listed


@pytest.mark.parametrize("spelling", ["lora", "Lora", " LORA ", "lora"])
def test_names_tolerate_model_casing(spelling):
    assert normalize_pair(spelling) == "lora"


@pytest.mark.parametrize("value", [None, "", "Comic Sans", "helvetica", 7])
def test_unknown_pairing_is_not_guessed_at(value):
    assert normalize_pair(value) is None


def test_fallback_is_stable_and_real():
    assert fallback_pair("Ridgeway Roofing") == fallback_pair("Ridgeway Roofing")
    assert fallback_pair("Ridgeway Roofing") in FONT_PAIRS


def test_fallback_varies_between_businesses():
    names = {fallback_pair(n) for n in
             ("Ridgeway Roofing", "Marlow & Fern", "Halcyon Counselling",
              "Bellweather & Co", "Apex Plumbing", "Fernside Joinery")}
    assert len(names) > 1


def test_every_family_the_front_end_names_is_actually_loaded():
    if not FONTS_TS.exists():
        pytest.skip("front end not present")
    source = FONTS_TS.read_text(encoding="utf-8")

    defined = set(re.findall(r'variable:\s*"(--f-[\w-]+)"', source))
    used = set(re.findall(r'":\s*"(--f-[\w-]+)"', source))
    assert used <= defined, f"undeclared families: {sorted(used - defined)}"


def test_every_loaded_family_is_used_by_some_pairing():
    if not FONTS_TS.exists():
        pytest.skip("front end not present")
    source = FONTS_TS.read_text(encoding="utf-8")

    defined = set(re.findall(r'variable:\s*"(--f-[\w-]+)"', source))
    used = set(re.findall(r'":\s*"(--f-[\w-]+)"', source))
    assert defined <= used, f"loaded but unused: {sorted(defined - used)}"


def test_every_pairing_in_the_manifest_names_a_loaded_family():
    if not FONTS_TS.exists():
        pytest.skip("front end not present")
    source = FONTS_TS.read_text(encoding="utf-8")
    families = set(re.findall(r'"([^"]+)":\s*"--f-[\w-]+"', source))
    for pair in FONT_PAIRS.values():
        assert pair.heading in families, pair.heading
        assert pair.body in families, pair.body
