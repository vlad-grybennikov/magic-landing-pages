from pipeline import _slugify


def test_basic_name():
    assert _slugify("Maria's Bakery") == "/maria-s-bakery"


def test_symbols_collapse_to_single_dash():
    assert _slugify("Hendricks & Pearce  Law") == "/hendricks-pearce-law"


def test_empty_and_symbol_only_fall_back():
    assert _slugify("") == "/page"
    assert _slugify("!!!") == "/page"
