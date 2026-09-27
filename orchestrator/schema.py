import re
from typing import Annotated, Literal, Optional, Union, get_args

from pydantic import BaseModel, Field, ValidationError, model_validator

from layouts import is_known

NonEmptyStr = Annotated[str, Field(min_length=1)]

HexColor = Annotated[str, Field(pattern=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")]


class Theme(BaseModel):
    name: NonEmptyStr
    mood: Optional[str] = None
    primary: HexColor
    primary_strong: HexColor
    primary_light: HexColor
    primary_foreground: HexColor
    accent: HexColor
    accent_foreground: HexColor
    background: HexColor
    foreground: HexColor
    muted: HexColor
    muted_foreground: HexColor
    border: HexColor
    layout: Optional[str] = None
    font: Optional[str] = None


class Image(BaseModel):
    src: NonEmptyStr
    alt: str = ""
    id: Optional[str] = None
    category: Optional[str] = None
    photographer: Optional[str] = None
    photographer_url: Optional[str] = None
    source_url: Optional[str] = None


Href = Annotated[str, Field(
    pattern=r"^(?:https?://\S+|mailto:\S+|tel:\+?[\d\s().-]+|#[\w-]*|/[^\s/][^\s]*|/)$")]


class Button(BaseModel):
    label: NonEmptyStr
    href: Optional[Href] = None


class NavLink(BaseModel):
    label: NonEmptyStr
    href: Href


class Brief(BaseModel):
    business: NonEmptyStr
    audience: NonEmptyStr
    goal: NonEmptyStr
    tone: Optional[str] = None


Provenance = Literal["generated", "placeholder", "edited"]


class SectionBase(BaseModel):
    variant: Optional[str] = None
    anchor: Optional[str] = None
    provenance: Optional[Provenance] = None
    reviewed: bool = False

    @model_validator(mode="after")
    def _variant_exists(self):
        section_type = getattr(self, "type", "")
        if not is_known(section_type, self.variant):
            raise ValueError(
                f"'{self.variant}' is not a layout for a {section_type} section")
        return self


class HeaderSection(SectionBase):
    type: Literal["header"]
    name: NonEmptyStr
    icon: Image
    links: Annotated[list[NavLink],
                     Field(min_length=0, max_length=12)] = []
    button: Optional[Button] = None


class FooterSection(SectionBase):
    type: Literal["footer"]
    name: NonEmptyStr
    icon: Image
    tagline: Optional[str] = None
    links_label: Optional[str] = None
    links: Annotated[list[NavLink],
                     Field(min_length=0, max_length=12)] = []
    contacts_label: Optional[str] = None
    contacts: Annotated[list[NavLink],
                        Field(min_length=0, max_length=6)] = []
    copyright: Optional[str] = None


class HeroSection(SectionBase):
    type: Literal["hero"]
    headline: NonEmptyStr
    subhead: Optional[str] = None
    image: Image
    button: Button


class AboutSection(SectionBase):
    type: Literal["about"]
    heading: NonEmptyStr
    eyebrow: Optional[str] = None
    body: Annotated[list[NonEmptyStr], Field(min_length=1, max_length=3)]
    image: Image
    button: Optional[Button] = None


class BenefitItem(BaseModel):
    icon: Image
    title: NonEmptyStr
    caption: NonEmptyStr


class BenefitsSection(SectionBase):
    type: Literal["benefits"]
    heading: NonEmptyStr
    subhead: Optional[str] = None
    items: Annotated[list[BenefitItem], Field(min_length=3, max_length=6)]


class ServiceItem(BaseModel):
    title: NonEmptyStr
    caption: NonEmptyStr
    image: Image
    button: Optional[Button] = None


class ServicesSection(SectionBase):
    type: Literal["services"]
    heading: NonEmptyStr
    subhead: Optional[str] = None
    items: Annotated[list[ServiceItem], Field(min_length=2, max_length=6)]


class ProcessStep(BaseModel):
    title: NonEmptyStr
    caption: NonEmptyStr
    icon: Optional[Image] = None


class ProcessSection(SectionBase):
    type: Literal["process"]
    heading: NonEmptyStr
    subhead: Optional[str] = None
    items: Annotated[list[ProcessStep], Field(min_length=3, max_length=5)]


class StatItem(BaseModel):
    value: NonEmptyStr
    label: NonEmptyStr
    caption: Optional[str] = None


class StatsSection(SectionBase):
    type: Literal["stats"]
    heading: Optional[str] = None
    subhead: Optional[str] = None
    items: Annotated[list[StatItem], Field(min_length=2, max_length=4)]


class GallerySection(SectionBase):
    type: Literal["gallery"]
    heading: Optional[str] = None
    subhead: Optional[str] = None
    images: Annotated[list[Image], Field(min_length=3, max_length=8)]


class TestimonialItem(BaseModel):
    name: NonEmptyStr
    rating: Annotated[int, Field(ge=1, le=5)]
    content: NonEmptyStr


class TestimonialsSection(SectionBase):
    type: Literal["testimonials"]
    heading: Optional[str] = None
    subhead: Optional[str] = None
    items: Annotated[list[TestimonialItem], Field(min_length=1)]


class PricingPlan(BaseModel):
    name: NonEmptyStr
    price: NonEmptyStr
    period: Optional[str] = None
    description: Optional[str] = None
    features: Annotated[list[NonEmptyStr], Field(min_length=1, max_length=8)]
    button: Button
    featured: bool = False


class PricingSection(SectionBase):
    type: Literal["pricing"]
    heading: NonEmptyStr
    subhead: Optional[str] = None
    plans: Annotated[list[PricingPlan], Field(min_length=1, max_length=4)]


class TeamMember(BaseModel):
    name: NonEmptyStr
    role: NonEmptyStr
    photo: Optional[Image] = None
    bio: Optional[str] = None


class TeamSection(SectionBase):
    type: Literal["team"]
    heading: NonEmptyStr
    subhead: Optional[str] = None
    members: Annotated[list[TeamMember], Field(min_length=2, max_length=6)]


class PromotionSection(SectionBase):
    type: Literal["promotion"]
    title: NonEmptyStr
    description: NonEmptyStr
    button: Button


class FAQItem(BaseModel):
    question: NonEmptyStr
    answer: NonEmptyStr


class FAQSection(SectionBase):
    type: Literal["faq"]
    heading: Optional[str] = None
    subhead: Optional[str] = None
    items: Annotated[list[FAQItem], Field(min_length=1)]


class ContactDetail(BaseModel):
    label: NonEmptyStr
    value: NonEmptyStr
    icon: Optional[Image] = None


class ContactSection(SectionBase):
    type: Literal["contact"]
    heading: NonEmptyStr
    description: Optional[str] = None
    details: Annotated[list[ContactDetail], Field(min_length=1, max_length=5)]
    button: Optional[Button] = None
    image: Optional[Image] = None


class CtaSection(SectionBase):
    type: Literal["cta"]
    headline: NonEmptyStr
    subhead: Optional[str] = None
    button: Button
    secondary: Optional[Button] = None
    image: Optional[Image] = None


Section = Annotated[
    Union[
        HeaderSection,
        HeroSection,
        AboutSection,
        BenefitsSection,
        ServicesSection,
        ProcessSection,
        StatsSection,
        GallerySection,
        TestimonialsSection,
        PricingSection,
        TeamSection,
        PromotionSection,
        FAQSection,
        ContactSection,
        CtaSection,
        FooterSection,
    ],
    Field(discriminator="type"),
]


SECTION_MODELS: dict[str, type[BaseModel]] = {
    model.model_fields["type"].annotation.__args__[0]: model
    for model in get_args(get_args(Section)[0])
}


class Page(BaseModel):
    id: Optional[str] = None
    version: int = 1
    name: NonEmptyStr
    url: NonEmptyStr
    sections: Annotated[list[Section], Field(min_length=1)]
    theme: Optional[Theme] = None


SECTION_ORDER = [
    "header",
    "hero",
    "about",
    "benefits",
    "services",
    "process",
    "stats",
    "gallery",
    "testimonials",
    "pricing",
    "team",
    "promotion",
    "faq",
    "contact",
    "cta",
    "footer",
]
SECTION_ORDER_INDEX = {name: i for i, name in enumerate(SECTION_ORDER)}

SECTION_ALIASES: dict[str, str] = {
    "header": r"\bheader\b|\bnav\b|\bnavigation\b|\btop bar\b|\blogo\b|\bbrand\b|\bmasthead\b",
    "footer": r"\bfooter\b|\bbottom bar\b",
    "hero": r"\bheroe?s?\b|\bbanner\b",
    "about": r"\babout\b|\bour story\b|\bwho we are\b|\bour history\b",
    "benefits": r"\bbenefits?\b|\badvantages?\b|\bwhy (?:choose|us)\b|"
                r"\bfeatures? section\b",
    "services": r"\bservices? section\b|\bservices?\b|"
                r"\blist of (?:services|treatments)\b|"
                r"\bwhat we (?:do|offer|sell|make)\b",
    "process": r"\bhow it works\b|\bprocess\b|\bsteps?\b|\bwhat to expect\b",
    "stats": r"\bstats?\b|\bstatistics\b|\bby the numbers\b|\bkey figures\b",
    "gallery": r"\bgallery\b|\bgalleries\b|\bportfolio\b|\bour work\b",
    "testimonials": r"\btestimonials?\b|\breviews?\b|\bratings?\b",
    "pricing": r"\bpricing\b|\bprices\b|\bprice list\b|\bpackages\b|\bplans\b|"
               r"\bhow much\b|\brate card\b",
    "team": r"\bteam\b|\bstaff\b|\bour people\b",
    "promotion": r"\bpromotions?\b|\bpromo\b|\bspecial offer\b|\bdiscount\b|"
                 r"\bdeal\b|\bsale\b|\bintroductory offer\b",
    "faq": r"\bfaqs?\b|\bq ?and ?a\b|\bq&a\b|\bquestions?\b",
    "contact": r"\bcontacts?\b|\bget in touch\b|\bopening hours\b|"
               r"\bhow to (?:find|reach)\b|\bdirections\b",
    "cta": r"\bcall to action\b|\bcta\b",
}


PHOTO_SECTIONS: dict[str, str] = {
    "hero": "image",
    "about": "image",
    "contact": "image",
    "cta": "image",
}

ICON_SECTIONS: frozenset[str] = frozenset({"benefits", "process"})

SECTION_LABELS: dict[str, str] = {
    "header": "Header",
    "hero": "Hero",
    "about": "About",
    "benefits": "Benefits",
    "services": "Services",
    "process": "How it works",
    "stats": "Stats",
    "gallery": "Gallery",
    "testimonials": "Testimonials",
    "pricing": "Pricing",
    "team": "Team",
    "promotion": "Promotion",
    "faq": "FAQ",
    "contact": "Contact",
    "cta": "Call to action",
    "footer": "Footer",
}

NOT_IN_NAV: frozenset[str] = frozenset(
    {"header", "footer", "hero", "cta", "promotion"})


def contact_links(sections: list[dict]) -> list[dict]:
    contact = next((s for s in sections if s.get("type") == "contact"), None)
    links = []
    for detail in (contact or {}).get("details", [])[:6]:
        value = str(detail.get("value", "")).strip()
        if not value:
            continue
        if "@" in value and " " not in value:
            href = f"mailto:{value}"
        elif re.fullmatch(r"\+?[\d\s().-]{7,}", value):
            href = f"tel:{value}"
        else:
            href = f"#{contact.get('anchor') or 'contact'}"
        links.append({"label": value, "href": href})
    return links


def nav_links(sections: list[dict]) -> list[dict]:
    return [{"label": SECTION_LABELS.get(s["type"], s["type"].title()),
             "href": f"#{s.get('anchor') or s['type']}"}
            for s in sections if s.get("type") not in NOT_IN_NAV]


LIST_FIELDS: dict[str, tuple[str, str]] = {
    "header": ("links", "Link"),
    "benefits": ("items", "Benefit"),
    "services": ("items", "Service"),
    "process": ("items", "Step"),
    "stats": ("items", "Figure"),
    "testimonials": ("items", "Testimonial"),
    "faq": ("items", "Question"),
    "pricing": ("plans", "Plan"),
    "team": ("members", "Member"),
    "contact": ("details", "Detail"),
    "gallery": ("images", "Photo"),
    "about": ("body", "Paragraph"),
}


GALLERY_SECTIONS: dict[str, str] = {"gallery": "images", "services": "items"}


PINNED_SECTIONS: frozenset[str] = frozenset({"header", "footer"})

CHROME_TARGETS = PINNED_SECTIONS

def section_type_for(name: Optional[str]) -> Optional[str]:
    text = (name or "").strip().lower()
    if text in SECTION_ORDER_INDEX:
        return text

    text = re.sub(r"^(the|a|an|my|our)\s+", "", text)
    text = re.sub(r"\s+section$", "", text).strip()
    if not text:
        return None

    for section_type, pattern in SECTION_ALIASES.items():
        if re.search(pattern, text):
            return section_type
    return None


def sections_named(text: Optional[str]) -> list[str]:
    haystack = (text or "").lower()
    return [section_type for section_type in SECTION_ORDER
            if re.search(SECTION_ALIASES[section_type], haystack)]


def summarize_errors(error: ValidationError) -> str:
    count = error.error_count()
    first = error.errors()[0]
    loc = ".".join(str(part) for part in first["loc"]) or "page"
    return f"{count} schema error(s); first at '{loc}': {first['msg']}"
