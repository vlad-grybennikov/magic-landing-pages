from __future__ import annotations

from typing import Optional

VARIANTS: dict[str, tuple[str, ...]] = {
    "header": ("standard", "centered", "minimal"),
    "hero": (
        "stacked", "split-left", "split-right", "centered", "full-bleed",
        "overlay-card", "minimal", "collage", "banner",
    ),
    "about": (
        "image-left", "image-right", "image-offset", "text-centered",
        "two-column-text", "lead-paragraph", "photo-band",
    ),
    "benefits": (
        "grid-plain", "grid-cards", "alternating-rows", "numbered",
        "two-column-list", "bordered-split", "icon-inline", "tinted-cards",
        "compact-list",
    ),
    "services": (
        "photo-cards", "photo-rows", "overlay-tiles", "list-with-thumbs",
        "feature-first", "bordered-grid", "rail",
    ),
    "process": (
        "numbered-steps", "timeline-vertical", "timeline-horizontal", "cards",
        "two-column-steps", "icon-steps", "compact-numbers",
    ),
    "stats": (
        "band-plain", "band-tinted", "cards", "divided-row", "heading-left",
        "large-numerals",
    ),
    "gallery": (
        "grid-three", "grid-four", "masonry", "mosaic", "filmstrip", "two-up",
        "full-bleed",
    ),
    "testimonials": (
        "cards-grid", "single-quote", "quote-rail", "two-column-large",
        "bordered-list", "tinted-cards", "masonry-quotes", "rating-summary",
    ),
    "pricing": (
        "three-cards", "featured-center", "table-rows", "two-up",
        "bordered-columns", "single-offer", "compact-list",
    ),
    "team": (
        "photo-grid", "circle-avatars", "cards-with-bio", "rows-alternating",
        "compact-row", "overlay-names",
    ),
    "promotion": (
        "centered-band", "tinted-band", "split-rule", "boxed-accent",
        "inline-row", "ticket", "full-bleed-accent",
    ),
    "faq": (
        "accordion", "accordion-boxed", "two-column-static", "heading-left",
        "numbered-list", "tinted-accordion", "compact-pairs",
    ),
    "contact": (
        "details-and-cta", "centered-details", "cards", "with-photo",
        "inline-row", "boxed", "two-column-list",
    ),
    "cta": (
        "centered", "band-accent", "split", "boxed-outline", "with-image",
        "minimal-rule",
    ),
    "footer": ("columns", "simple", "centered"),
}

DEFAULT_VARIANTS: dict[str, str] = {
    "header": "standard",
    "hero": "stacked",
    "about": "image-right",
    "benefits": "grid-plain",
    "services": "photo-cards",
    "process": "numbered-steps",
    "stats": "band-plain",
    "gallery": "grid-three",
    "testimonials": "cards-grid",
    "pricing": "three-cards",
    "team": "photo-grid",
    "promotion": "centered-band",
    "faq": "accordion",
    "contact": "details-and-cta",
    "cta": "centered",
    "footer": "columns",
}

LAYOUT_PACKS: dict[str, dict[str, str]] = {
    "editorial": {
        "header": "minimal",
        "hero": "split-left",
        "about": "two-column-text",
        "benefits": "two-column-list",
        "services": "photo-rows",
        "process": "two-column-steps",
        "stats": "large-numerals",
        "gallery": "two-up",
        "testimonials": "two-column-large",
        "pricing": "table-rows",
        "team": "rows-alternating",
        "promotion": "split-rule",
        "faq": "heading-left",
        "contact": "two-column-list",
        "cta": "minimal-rule",
        "footer": "columns",
    },
    "bold": {
        "header": "standard",
        "hero": "full-bleed",
        "about": "photo-band",
        "benefits": "numbered",
        "services": "overlay-tiles",
        "process": "timeline-horizontal",
        "stats": "band-tinted",
        "gallery": "full-bleed",
        "testimonials": "single-quote",
        "pricing": "featured-center",
        "team": "overlay-names",
        "promotion": "full-bleed-accent",
        "faq": "accordion-boxed",
        "contact": "with-photo",
        "cta": "band-accent",
        "footer": "columns",
    },
    "minimal": {
        "header": "minimal",
        "hero": "minimal",
        "about": "image-right",
        "benefits": "grid-plain",
        "services": "photo-cards",
        "process": "numbered-steps",
        "stats": "band-plain",
        "gallery": "grid-three",
        "testimonials": "bordered-list",
        "pricing": "three-cards",
        "team": "photo-grid",
        "promotion": "inline-row",
        "faq": "accordion",
        "contact": "centered-details",
        "cta": "centered",
        "footer": "simple",
    },
    "warm": {
        "header": "standard",
        "hero": "split-right",
        "about": "image-left",
        "benefits": "tinted-cards",
        "services": "photo-cards",
        "process": "icon-steps",
        "stats": "cards",
        "gallery": "masonry",
        "testimonials": "tinted-cards",
        "pricing": "three-cards",
        "team": "circle-avatars",
        "promotion": "ticket",
        "faq": "tinted-accordion",
        "contact": "cards",
        "cta": "split",
        "footer": "columns",
    },
    "corporate": {
        "header": "standard",
        "hero": "stacked",
        "about": "image-right",
        "benefits": "grid-cards",
        "services": "bordered-grid",
        "process": "cards",
        "stats": "cards",
        "gallery": "grid-four",
        "testimonials": "cards-grid",
        "pricing": "featured-center",
        "team": "cards-with-bio",
        "promotion": "centered-band",
        "faq": "accordion-boxed",
        "contact": "boxed",
        "cta": "split",
        "footer": "columns",
    },
    "boutique": {
        "header": "centered",
        "hero": "collage",
        "about": "image-offset",
        "benefits": "alternating-rows",
        "services": "feature-first",
        "process": "timeline-vertical",
        "stats": "heading-left",
        "gallery": "mosaic",
        "testimonials": "single-quote",
        "pricing": "single-offer",
        "team": "rows-alternating",
        "promotion": "tinted-band",
        "faq": "two-column-static",
        "contact": "with-photo",
        "cta": "boxed-outline",
        "footer": "centered",
    },
    "technical": {
        "header": "standard",
        "hero": "banner",
        "about": "two-column-text",
        "benefits": "bordered-split",
        "services": "list-with-thumbs",
        "process": "compact-numbers",
        "stats": "divided-row",
        "gallery": "grid-four",
        "testimonials": "rating-summary",
        "pricing": "bordered-columns",
        "team": "compact-row",
        "promotion": "inline-row",
        "faq": "compact-pairs",
        "contact": "inline-row",
        "cta": "minimal-rule",
        "footer": "simple",
    },
    "organic": {
        "header": "centered",
        "hero": "centered",
        "about": "text-centered",
        "benefits": "icon-inline",
        "services": "photo-cards",
        "process": "icon-steps",
        "stats": "band-plain",
        "gallery": "masonry",
        "testimonials": "masonry-quotes",
        "pricing": "two-up",
        "team": "circle-avatars",
        "promotion": "tinted-band",
        "faq": "numbered-list",
        "contact": "centered-details",
        "cta": "centered",
        "footer": "centered",
    },
    "luxe": {
        "header": "centered",
        "hero": "overlay-card",
        "about": "lead-paragraph",
        "benefits": "compact-list",
        "services": "rail",
        "process": "timeline-vertical",
        "stats": "large-numerals",
        "gallery": "filmstrip",
        "testimonials": "quote-rail",
        "pricing": "compact-list",
        "team": "overlay-names",
        "promotion": "boxed-accent",
        "faq": "heading-left",
        "contact": "details-and-cta",
        "cta": "with-image",
        "footer": "simple",
    },
}

PACK_NAMES: tuple[str, ...] = tuple(LAYOUT_PACKS)

DEFAULT_PACK = "minimal"

PACK_DESCRIPTIONS: dict[str, str] = {
    "editorial": "type-led and ruled; headings held left, rules instead of cards",
    "bold": "large photography, full-bleed bands, strong accent colour",
    "minimal": "plain surfaces, generous whitespace, no decoration",
    "warm": "rounded and tinted, approachable; trades and family businesses",
    "corporate": "structured cards and predictable grids; professional services",
    "boutique": "offset frames and asymmetry; studios, salons, small ateliers",
    "technical": "dense and tabular, the most information in the least height",
    "organic": "soft shapes and uneven rhythm; wellbeing, food, craft",
    "luxe": "photography-forward and restrained; premium and hospitality",
}


def normalize_pack(name: Optional[str]) -> Optional[str]:
    if not isinstance(name, str):
        return None
    candidate = name.strip().lower().replace(" ", "-").replace("_", "-")
    return candidate if candidate in LAYOUT_PACKS else None


def fallback_pack(seed: str) -> str:
    total = sum(ord(c) * (i + 1) for i, c in enumerate(seed or ""))
    return PACK_NAMES[total % len(PACK_NAMES)]


def variants_for(section_type: str) -> tuple[str, ...]:
    return VARIANTS.get(section_type, ())


def variant_for(pack: Optional[str], section_type: str) -> Optional[str]:
    chosen = LAYOUT_PACKS.get(pack or "", {})
    return chosen.get(section_type) or DEFAULT_VARIANTS.get(section_type)


def normalize_variant(name: Optional[str]) -> Optional[str]:
    if not isinstance(name, str):
        return None
    return name.strip().lower().replace(" ", "-").replace("_", "-") or None


def is_known(section_type: str, variant: Optional[str]) -> bool:
    if variant is None:
        return True
    return variant in VARIANTS.get(section_type, ())
