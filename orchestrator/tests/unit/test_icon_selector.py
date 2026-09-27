import json
import re

import pytest

import icon_selector
from icon_selector import BundledIcons, LucideIcons


@pytest.fixture
def vocabulary(tmp_path, monkeypatch):
    monkeypatch.setattr(icon_selector, "MIN_SIMILARITY", 0.0)
    library = tmp_path / "index.json"
    library.write_text(json.dumps({
        "source": "test", "version": "0.0.0",
        "icons": {
            "piggy-bank": ["money", "savings", "budget"],
            "heart-handshake": ["care", "support", "trust"],
            "venus-and-mars": ["gender", "symbol"],
            "bell-off": ["silence", "care", "support", "trust", "muted"],
        },
    }))
    return LucideIcons(library=library)


@pytest.fixture
def lucide():
    if not icon_selector.LIBRARY.exists():
        pytest.skip("no icon vocabulary built (scripts/fetch_icons.py)")
    return LucideIcons()


def test_resolves_however_the_model_spelled_it(vocabulary):
    for spelling in ("piggy-bank", "PiggyBank", "piggy_bank", "Piggy Bank",
                     "lucide-piggy-bank", "piggy-bank-icon"):
        assert vocabulary.resolve(spelling)["id"] == "piggy-bank"


def test_resolves_a_plural_onto_the_real_name(vocabulary):
    assert vocabulary.resolve("piggy-banks")["id"] == "piggy-bank"


def test_unknown_name_does_not_resolve(vocabulary):
    assert vocabulary.resolve("energy-saving") is None
    assert vocabulary.resolve("") is None


def test_resolved_icon_is_an_image_the_frontend_can_serve(vocabulary):
    choice = vocabulary.resolve("heart-handshake")
    assert choice["src"] == "/icons/heart-handshake.svg"
    assert choice["id"] == "heart-handshake"


def test_matches_on_tags_not_just_names(vocabulary):
    assert vocabulary.match("money-save")["id"] == "piggy-bank"


def test_never_picks_a_disabled_variant(vocabulary):
    assert vocabulary.match("care support trust")["id"] == "heart-handshake"


def test_match_skips_icons_already_taken(vocabulary):
    assert vocabulary.match("money-save", taken=["piggy-bank"])["id"] != "piggy-bank"


def test_match_is_deterministic(vocabulary):
    assert {vocabulary.match("support and care")["id"] for _ in range(5)} == \
        {"heart-handshake"}


def test_real_names_resolve(lucide):
    assert len(lucide) > 1000
    assert lucide.resolve("shield-check")["id"] == "shield-check"
    assert lucide.resolve("ShieldCheck")["id"] == "shield-check"


def test_invented_names_repair_to_real_ones(lucide):
    assert lucide.match("security-shield")["id"].endswith("shield")
    assert lucide.match("leaf-eco")["id"] == "leaf"
    assert lucide.match("handshake-heart")["id"] == "heart-handshake"


def test_common_words_cannot_decide_a_match(lucide, monkeypatch):
    chosen = lucide.match("trust and support")["id"]
    monkeypatch.setattr(icon_selector, "STOP_WORDS", frozenset())
    assert "and" not in chosen.split("-")
    assert lucide.match("trust and support")["id"] != chosen


def test_disabled_variants_are_never_chosen(lucide, monkeypatch):
    query = "soy free legume food seed allergy"
    assert lucide.match(query)["id"] == "bean"
    monkeypatch.setattr(icon_selector, "NEGATED", re.compile(r"$^"))
    assert lucide.match(query)["id"] == "bean-off"


def test_copy_that_names_nothing_concrete_matches_nothing(lucide):
    assert lucide.match("Quality Guaranteed") is None


def test_defaults_cycle_so_a_section_never_repeats(lucide):
    picks = [lucide.default(i)["id"] for i in range(3)]
    assert len(set(picks)) == 3
    assert all(lucide.resolve(name) for name in picks)


def test_bundled_icons_cycle_the_shipped_set():
    bundled = BundledIcons()
    picks = [bundled.default(i)["src"] for i in range(3)]
    assert len(set(picks)) == 3
    assert all(src.startswith("/images/") and src.endswith(".svg") for src in picks)


def test_bundled_icons_ignore_a_lucide_name():
    assert BundledIcons().resolve("shield-check") is None


def test_bundled_match_walks_the_set():
    bundled = BundledIcons()
    first = bundled.match("anything")["id"]
    assert bundled.match("anything", taken=[first])["id"] != first


def test_factory_returns_bundled_when_asked(monkeypatch):
    monkeypatch.setenv("MLP_ICONS", "bundled")
    icon_selector.build_icon_service.cache_clear()
    assert isinstance(icon_selector.build_icon_service(), BundledIcons)
    icon_selector.build_icon_service.cache_clear()


def test_factory_falls_back_when_no_vocabulary(monkeypatch, tmp_path):
    monkeypatch.delenv("MLP_ICONS", raising=False)
    monkeypatch.setattr(icon_selector, "LIBRARY", tmp_path / "missing.json")
    icon_selector.build_icon_service.cache_clear()
    assert isinstance(icon_selector.build_icon_service(), BundledIcons)
    icon_selector.build_icon_service.cache_clear()


def test_factory_errors_when_lucide_requested_without_vocabulary(monkeypatch, tmp_path):
    monkeypatch.setenv("MLP_ICONS", "lucide")
    monkeypatch.setattr(icon_selector, "LIBRARY", tmp_path / "missing.json")
    icon_selector.build_icon_service.cache_clear()
    with pytest.raises(RuntimeError, match="fetch_icons"):
        icon_selector.build_icon_service()
    icon_selector.build_icon_service.cache_clear()
