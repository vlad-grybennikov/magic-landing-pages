from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, field_validator

from fonts import normalize_pair
from layouts import normalize_pack
from schema import HexColor, NonEmptyStr, Theme

BODY_CONTRAST = 4.5
LARGE_CONTRAST = 3.0

INK = "#0f172a"
PAPER = "#ffffff"

HEX_PATTERN = re.compile(r"#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _hex(rgb) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def mix(color: str, other: str, weight: float) -> str:
    a, b = _rgb(color), _rgb(other)
    weight = max(0.0, min(1.0, weight))
    return _hex(tuple(x + (y - x) * weight for x, y in zip(a, b)))


def lighten(color: str, amount: float) -> str:
    return mix(color, PAPER, amount)


def darken(color: str, amount: float) -> str:
    return mix(color, "#000000", amount)


def relative_luminance(color: str) -> float:
    channels = []
    for raw in _rgb(color):
        c = raw / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color: str, other: str) -> float:
    a, b = relative_luminance(color), relative_luminance(other)
    return round((max(a, b) + 0.05) / (min(a, b) + 0.05), 3)


def is_light(color: str) -> bool:
    return contrast_ratio(color, INK) > contrast_ratio(color, PAPER)


def readable_on(background: str, minimum: float = 0.0) -> str:
    neutral = INK if is_light(background) else PAPER
    if contrast_ratio(neutral, background) >= minimum:
        return neutral
    return max(("#000000", PAPER), key=lambda c: contrast_ratio(c, background))


def ensure_contrast(color: str, against: str, minimum: float) -> str:
    if contrast_ratio(color, against) >= minimum:
        return color
    target = readable_on(against, minimum)
    for step in range(1, 21):
        candidate = mix(color, target, step / 20)
        if contrast_ratio(candidate, against) >= minimum:
            return candidate
    return target


class ThemeChoice(BaseModel):
    name: NonEmptyStr
    mood: Optional[str] = None
    hue: NonEmptyStr
    primary: HexColor
    accent: HexColor
    background: HexColor
    layout: Optional[str] = None
    font: Optional[str] = None

    @field_validator("primary", "accent", "background", mode="before")
    @classmethod
    def _extract_hex(cls, value):
        if not isinstance(value, str):
            return value
        match = HEX_PATTERN.search(value.strip())
        return "#" + match.group(1).lower() if match else value

    @field_validator("layout", mode="before")
    @classmethod
    def _known_layout(cls, value):
        return normalize_pack(value) if value is not None else None

    @field_validator("font", mode="before")
    @classmethod
    def _known_font(cls, value):
        return normalize_pair(value) if value is not None else None


MAX_DARKEN = 0.45


def solid(color: str) -> tuple[str, str]:
    if contrast_ratio(color, PAPER) >= BODY_CONTRAST:
        return color, PAPER

    for step in range(1, 19):
        candidate = darken(color, step * MAX_DARKEN / 18)
        if contrast_ratio(candidate, PAPER) >= BODY_CONTRAST:
            return candidate, PAPER

    return color, readable_on(color, BODY_CONTRAST)


def expand(choice: ThemeChoice, refine: bool = False) -> Theme:
    primary = vivid(choice.primary) if refine else choice.primary
    accent = vivid(choice.accent) if refine else choice.accent
    background = choice.background

    primary, primary_foreground = solid(primary)
    accent, accent_foreground = solid(accent)
    light = is_light(background)
    foreground = mix(readable_on(background), primary, 0.10)

    return Theme(
        name=choice.name,
        mood=choice.mood,
        layout=choice.layout,
        font=choice.font,
        primary=primary,
        primary_strong=darken(primary, 0.18) if light else lighten(primary, 0.18),
        primary_light=mix(primary, background, 0.55),
        primary_foreground=primary_foreground,
        accent=accent,
        accent_foreground=accent_foreground,
        background=background,
        foreground=foreground,
        muted=mix(background, primary, 0.06) if light else lighten(background, 0.08),
        muted_foreground=mix(foreground, background, 0.22),
        border=mix(background, foreground, 0.14),
    )


NEUTRAL_SATURATION = 0.12
MIN_SATURATION = 0.38
LIGHTNESS_RANGE = (0.34, 0.56)


def vivid(color: str) -> str:
    hue, saturation, lightness = _to_hsl(color)
    if saturation <= NEUTRAL_SATURATION:
        return color

    low, high = LIGHTNESS_RANGE
    return _from_hsl(
        hue,
        max(saturation, MIN_SATURATION),
        min(max(lightness, low), high),
    )


CONTRAST_RULES: list[tuple[str, str, float]] = [
    ("primary", "background", LARGE_CONTRAST),
    ("accent", "background", LARGE_CONTRAST),
    ("foreground", "background", BODY_CONTRAST),
    ("muted_foreground", "muted", BODY_CONTRAST),
    ("primary_foreground", "primary", BODY_CONTRAST),
    ("accent_foreground", "accent", BODY_CONTRAST),
]


def validate_theme(theme: Theme) -> tuple[Theme, list[str]]:
    tokens = theme.model_dump()
    notes: list[str] = []

    for token, against, minimum in CONTRAST_RULES:
        before = tokens[token]
        fixed = ensure_contrast(before, tokens[against], minimum)
        if fixed == before:
            continue
        tokens[token] = fixed
        notes.append(f"{token} {before}→{fixed} for {minimum}:1 on {against}")
        if token in ("primary", "accent"):
            tokens[f"{token}_foreground"] = readable_on(fixed, BODY_CONTRAST)

    return Theme(**tokens), notes


def build_theme(choice: ThemeChoice, refine: bool = False) -> tuple[Theme, list[str]]:
    return validate_theme(expand(choice, refine))


def _to_hsl(color: str) -> tuple[float, float, float]:
    r, g, b = (c / 255 for c in _rgb(color))
    high, low = max(r, g, b), min(r, g, b)
    lightness = (high + low) / 2
    if high == low:
        return 0.0, 0.0, lightness

    span = high - low
    saturation = span / (2 - high - low if lightness > 0.5 else high + low)
    if high == r:
        hue = ((g - b) / span) % 6
    elif high == g:
        hue = (b - r) / span + 2
    else:
        hue = (r - g) / span + 4
    return hue * 60, saturation, lightness


def _from_hsl(hue: float, saturation: float, lightness: float) -> str:
    c = (1 - abs(2 * lightness - 1)) * saturation
    x = c * (1 - abs(((hue / 60) % 2) - 1))
    m = lightness - c / 2
    r, g, b = [
        (c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)
    ][int(hue // 60) % 6]
    return _hex(((r + m) * 255, (g + m) * 255, (b + m) * 255))


def from_hue(hue: float, layout: Optional[str] = None,
             font: Optional[str] = None) -> ThemeChoice:
    hue %= 360
    return ThemeChoice(
        name=f"Hue {round(hue)}",
        mood="deterministic stub palette",
        hue=f"hue {round(hue)}°",
        layout=layout,
        primary=_from_hsl(hue, 0.55, 0.38),
        accent=_from_hsl((hue + 24) % 360, 0.62, 0.32),
        background=_from_hsl(hue, 0.40, 0.985),
    )


def brand_colors(theme: Theme | dict) -> dict:
    tokens = theme if isinstance(theme, dict) else theme.model_dump()
    return {key: tokens[key] for key in ("primary", "accent", "background")}
