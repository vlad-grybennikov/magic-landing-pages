import json

import pytest

from layouts import (
    DEFAULT_PACK,
    DEFAULT_VARIANTS,
    LAYOUT_PACKS,
    PACK_DESCRIPTIONS,
    VARIANTS,
    is_known,
    normalize_pack,
    variant_for,
)
from schema import SECTION_MODELS, SECTION_ORDER

def test_every_section_type_has_layouts():
    assert set(VARIANTS) == set(SECTION_ORDER)


def test_every_section_type_can_be_built():
    assert set(VARIANTS) == set(SECTION_MODELS)


def test_default_variant_of_every_type_is_one_of_its_own():
    for section_type, variant in DEFAULT_VARIANTS.items():
        assert variant in VARIANTS[section_type], section_type


def test_packs_cover_every_section_type():
    for name, pack in LAYOUT_PACKS.items():
        assert set(pack) == set(VARIANTS), f"{name} is missing types"


def test_packs_only_name_variants_that_exist():
    for name, pack in LAYOUT_PACKS.items():
        for section_type, variant in pack.items():
            assert variant in VARIANTS[section_type], f"{name}/{section_type}"


def test_every_variant_is_reachable_from_some_pack():
    used = {(section_type, variant)
            for pack in LAYOUT_PACKS.values()
            for section_type, variant in pack.items()}
    unreachable = [(section_type, variant)
                   for section_type, variants in VARIANTS.items()
                   for variant in variants
                   if (section_type, variant) not in used]
    assert unreachable == []


def test_every_pack_is_described_for_the_model():
    assert set(PACK_DESCRIPTIONS) == set(LAYOUT_PACKS)


def test_default_pack_exists():
    assert DEFAULT_PACK in LAYOUT_PACKS


@pytest.mark.parametrize("spelling", ["luxe", "Luxe", " LUXE ", "luxe"])
def test_pack_names_tolerate_model_casing(spelling):
    assert normalize_pack(spelling) == "luxe"


@pytest.mark.parametrize("value", [None, "", "artisanal", "pack-3", 7])
def test_unknown_pack_is_not_guessed_at(value):
    assert normalize_pack(value) is None


def test_variant_comes_from_the_named_pack():
    assert variant_for("bold", "hero") == LAYOUT_PACKS["bold"]["hero"]


def test_unknown_pack_falls_back_to_the_type_default():
    assert variant_for("nonesuch", "hero") == DEFAULT_VARIANTS["hero"]
    assert variant_for(None, "faq") == DEFAULT_VARIANTS["faq"]


def test_a_type_no_pack_covers_still_resolves():
    assert variant_for("bold", "not-a-section") is None


def test_absent_variant_is_allowed_so_older_pages_still_load():
    assert is_known("hero", None)


def test_a_variant_from_another_type_is_rejected():
    assert not is_known("hero", "three-cards")
    assert not is_known("faq", "invented")


def test_the_variant_count_is_what_the_report_claims():
    assert sum(len(v) for v in VARIANTS.values()) == 106
    assert json.dumps(sorted(VARIANTS)), "types are serialisable for the report"
