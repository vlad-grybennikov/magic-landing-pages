from __future__ import annotations

from typing import Optional


class Pairing:
    __slots__ = ("heading", "body", "character")

    def __init__(self, heading: str, body: str, character: str):
        self.heading = heading
        self.body = body
        self.character = character


FONT_PAIRS: dict[str, Pairing] = {
    "inter": Pairing(
        "Inter", "Inter",
        "neutral and contemporary; the safe modern default, and never wrong"),
    "outfit": Pairing(
        "Outfit", "Inter",
        "geometric and friendly; startups, studios, anything forward-looking"),
    "playfair": Pairing(
        "Playfair Display", "Source Sans 3",
        "high-contrast serif headings; editorial, formal, established"),
    "fraunces": Pairing(
        "Fraunces", "Nunito Sans",
        "characterful soft serif; craft, food, makers, anything hand-made"),
    "space": Pairing(
        "Space Grotesk", "Inter",
        "technical and precise; engineering, trades, anything measured"),
    "libre": Pairing(
        "Libre Baskerville", "Lato",
        "traditional book serif; law, finance, advice you are trusted with"),
    "poppins": Pairing(
        "Poppins", "Poppins",
        "rounded and approachable; family businesses, care, children"),
    "cormorant": Pairing(
        "Cormorant Garamond", "Montserrat",
        "fine and restrained; premium, hospitality, beauty"),
    "bitter": Pairing(
        "Bitter", "Open Sans",
        "sturdy slab; construction, motor, anything hard-wearing"),
    "lora": Pairing(
        "Lora", "Karla",
        "calm literary serif; wellbeing, therapy, slow and considered work"),
}

PAIR_NAMES: tuple[str, ...] = tuple(FONT_PAIRS)

DEFAULT_PAIR = "inter"


def normalize_pair(name: Optional[str]) -> Optional[str]:
    if not isinstance(name, str):
        return None
    candidate = name.strip().lower().replace(" ", "-").replace("_", "-")
    return candidate if candidate in FONT_PAIRS else None


def fallback_pair(seed: str) -> str:
    total = sum(ord(c) * (i + 1) for i, c in enumerate(seed or ""))
    return PAIR_NAMES[total % len(PAIR_NAMES)]


def describe_pairs() -> str:
    return "\n".join(
        f"    {name} -- {pair.heading}/{pair.body}: {pair.character}"
        for name, pair in FONT_PAIRS.items()
    )
