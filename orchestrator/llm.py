import copy
import logging
import os
import re
import zlib
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

import telemetry
from actions import REGISTRY, missing_args
from icon_selector import build_icon_service
from llm_client import LLMResponseInvalid, OllamaClient, OpenRouterClient
from mock_page import COPY_TEMPLATES
from prompts import (
    ANSWER_CONTEXT,
    LAYOUT_SYSTEM,
    LAYOUT_USER,
    COPY_SYSTEM,
    COPY_USER,
    ICON_HINT,
    ICON_SYSTEM,
    ICON_USER,
    INTERPRET_SYSTEM,
    SCHEMA_SYSTEM,
    SUGGEST_SYSTEM,
    SUGGEST_USER,
    THEME_HINT,
    THEME_SYSTEM,
    THEME_USER,
)
from fonts import PAIR_NAMES, describe_pairs
from layouts import PACK_DESCRIPTIONS, PACK_NAMES, variants_for
from schema import (
    SECTION_ORDER_INDEX,
    NonEmptyStr,
    sections_named,
)
from settings import LLM_PROVIDERS, listed
from theme import ThemeChoice, from_hue

logger = logging.getLogger("mlp.pipeline")

ATTEMPTS = 2

DEFAULT_SCHEMA = ["hero", "benefits", "testimonials", "promotion", "faq"]

SectionType = Literal[
    "hero", "about", "benefits", "services", "process", "stats", "gallery",
    "testimonials", "pricing", "team", "promotion", "faq", "contact", "cta",
]

FieldName = Literal["title", "description", "eyebrow", "button"]
Intent = Literal[
    "createPage", "editContent", "replaceImage", "addSection", "removeSection",
    "moveSection", "setVariant", "addItem", "removeItem", "moveItem", "setIcon",
    "setTheme", "regenerateSection",
    "unsupported",
]


class ExtractedArgs(BaseModel):
    business: Optional[str] = None
    audience: Optional[str] = None
    goal: Optional[str] = None
    tone: Optional[str] = None
    sections: Optional[list[SectionType]] = None
    section: Optional[SectionType] = None
    type: Optional[SectionType] = None
    field: Optional[FieldName] = None
    path: Optional[str] = None
    value: Optional[str] = None
    query: Optional[str] = None
    position: Optional[str] = None
    variant: Optional[str] = None
    icon: Optional[str] = None
    style: Optional[str] = None
    primary: Optional[str] = None
    accent: Optional[str] = None
    background: Optional[str] = None
    font: Optional[str] = None


class Interpretation(BaseModel):
    intent: Intent
    args: ExtractedArgs = Field(default_factory=ExtractedArgs)
    missing: list[str] = Field(default_factory=list)


def _no_arguments(interp: "Interpretation") -> bool:
    spec = REGISTRY.get(interp.intent)
    return bool(spec and spec.required) and not any(interp.args.model_dump().values())



def to_brief(args: ExtractedArgs, transcript: str) -> dict:
    return {
        "business": args.business or StubLanguageService._guess_business(transcript) or "Your Business",
        "audience": args.audience or "Local customers",
        "goal": args.goal or "Generate enquiries",
        "tone": args.tone,
    }


class ButtonCopy(BaseModel):
    label: NonEmptyStr


class HeroCopy(BaseModel):
    headline: NonEmptyStr
    subhead: NonEmptyStr
    button: ButtonCopy


class BenefitItemCopy(BaseModel):
    title: NonEmptyStr
    caption: NonEmptyStr


class BenefitsCopy(BaseModel):
    heading: NonEmptyStr
    items: list[BenefitItemCopy] = Field(min_length=3, max_length=6)


class TestimonialItemCopy(BaseModel):
    name: NonEmptyStr
    rating: int = Field(ge=1, le=5)
    content: NonEmptyStr


class TestimonialsCopy(BaseModel):
    heading: Optional[str] = None
    items: list[TestimonialItemCopy] = Field(min_length=1)


class PromotionCopy(BaseModel):
    title: NonEmptyStr
    description: NonEmptyStr
    button: ButtonCopy


class FAQItemCopy(BaseModel):
    question: NonEmptyStr
    answer: NonEmptyStr


class FAQCopy(BaseModel):
    heading: NonEmptyStr
    items: list[FAQItemCopy] = Field(min_length=1)


class AboutCopy(BaseModel):
    heading: NonEmptyStr
    eyebrow: Optional[str] = None
    body: list[NonEmptyStr] = Field(min_length=1, max_length=3)
    button: Optional[ButtonCopy] = None


class ServiceItemCopy(BaseModel):
    title: NonEmptyStr
    caption: NonEmptyStr
    button: Optional[ButtonCopy] = None


class ServicesCopy(BaseModel):
    heading: NonEmptyStr
    subhead: Optional[str] = None
    items: list[ServiceItemCopy] = Field(min_length=2, max_length=6)


class ProcessStepCopy(BaseModel):
    title: NonEmptyStr
    caption: NonEmptyStr


class ProcessCopy(BaseModel):
    heading: NonEmptyStr
    subhead: Optional[str] = None
    items: list[ProcessStepCopy] = Field(min_length=3, max_length=5)


class StatItemCopy(BaseModel):
    value: NonEmptyStr
    label: NonEmptyStr
    caption: Optional[str] = None


class StatsCopy(BaseModel):
    heading: Optional[str] = None
    subhead: Optional[str] = None
    items: list[StatItemCopy] = Field(min_length=3, max_length=4)


class GalleryCopy(BaseModel):
    heading: Optional[str] = None
    subhead: Optional[str] = None


class PricingPlanCopy(BaseModel):
    name: NonEmptyStr
    price: NonEmptyStr
    period: Optional[str] = None
    description: Optional[str] = None
    features: list[NonEmptyStr] = Field(min_length=1, max_length=8)
    button: ButtonCopy
    featured: bool = False


class PricingCopy(BaseModel):
    heading: NonEmptyStr
    subhead: Optional[str] = None
    plans: list[PricingPlanCopy] = Field(min_length=1, max_length=4)


class TeamMemberCopy(BaseModel):
    name: NonEmptyStr
    role: NonEmptyStr
    bio: Optional[str] = None


class TeamCopy(BaseModel):
    heading: NonEmptyStr
    subhead: Optional[str] = None
    members: list[TeamMemberCopy] = Field(min_length=2, max_length=6)


class ContactDetailCopy(BaseModel):
    label: NonEmptyStr
    value: NonEmptyStr


class ContactCopy(BaseModel):
    heading: NonEmptyStr
    description: Optional[str] = None
    details: list[ContactDetailCopy] = Field(min_length=1, max_length=5)
    button: Optional[ButtonCopy] = None


class CtaCopy(BaseModel):
    headline: NonEmptyStr
    subhead: Optional[str] = None
    button: ButtonCopy
    secondary: Optional[ButtonCopy] = None


COPY_MODELS: dict[str, type[BaseModel]] = {
    "hero": HeroCopy,
    "about": AboutCopy,
    "benefits": BenefitsCopy,
    "services": ServicesCopy,
    "process": ProcessCopy,
    "stats": StatsCopy,
    "gallery": GalleryCopy,
    "testimonials": TestimonialsCopy,
    "pricing": PricingCopy,
    "team": TeamCopy,
    "promotion": PromotionCopy,
    "faq": FAQCopy,
    "contact": ContactCopy,
    "cta": CtaCopy,
}


class SectionPlan(BaseModel):
    sections: list[SectionType]


class SlotOptions(BaseModel):
    slot: str
    options: list[NonEmptyStr] = Field(min_length=2, max_length=4)


class Suggestions(BaseModel):
    slots: list[SlotOptions]


class SectionLayout(BaseModel):
    section: str
    variant: str


class LayoutPlan(BaseModel):
    sections: list[SectionLayout]


class IconChoice(BaseModel):
    name: NonEmptyStr


PACK_LINES = "\n".join(f"    {name} -- {description}"
                       for name, description in PACK_DESCRIPTIONS.items())

FONT_LINES = describe_pairs()


def _seed(text: str) -> int:
    return zlib.crc32(text.encode("utf-8")) & 0x7FFFFFFF


class ModelLanguageService:
    def __init__(self, client):
        self.client = client
        self._stub = StubLanguageService()

    @property
    def model(self) -> str:
        return self.client.model

    @property
    def id(self) -> str:
        return f"{self.client.provider}:{self.client.model}"

    def _validated(self, system: str, user: str, model_cls: type[BaseModel],
                   options: dict | None = None):
        last_error = None
        for attempt in range(1, ATTEMPTS + 1):
            prompt = user if last_error is None else (
                f"{user}\n\nYour previous response was invalid: {last_error}\n"
                "Respond again with corrected JSON."
            )
            try:
                data = self.client.complete_json(
                    system, prompt, model_cls.model_json_schema(), options)
                result = model_cls(**data)
            except (LLMResponseInvalid, ValidationError) as e:
                last_error = str(e)[:300]
                logger.warning("LLM output invalid for %s, retrying: %s",
                               model_cls.__name__, last_error)
                continue
            telemetry.record(model_cls.__name__, attempt, True)
            return result
        telemetry.record(model_cls.__name__, ATTEMPTS, False)
        return None

    def interpret(self, transcript: str, pending=None) -> Interpretation:
        system = INTERPRET_SYSTEM
        if pending is not None and pending.missing:
            known = ", ".join(f"{k}={v!r}" for k, v in pending.args.items() if v) or "nothing yet"
            system += "\n\n" + ANSWER_CONTEXT.format(
                intent=pending.intent, known=known, missing=", ".join(pending.missing))

        interp = self._validated(system, transcript, Interpretation)
        if interp is not None and _no_arguments(interp):
            logger.warning("interpret returned %r with no arguments, asking once more", interp.intent)
            again = self._validated(
                system, f"{transcript}\n\nYour previous answer gave no arguments at all. "
                "Extract every argument the instruction states, verbatim where possible.",
                Interpretation)
            if again is not None and not _no_arguments(again):
                interp = again
        if interp is None:
            intent = self._stub.classify_intent(transcript)
            logger.warning("interpret failed twice -> %r by keyword, asking for the rest", intent)
            return Interpretation(intent=intent, missing=missing_args(intent, {}))
        interp.missing = missing_args(interp.intent, interp.args.model_dump())
        return interp

    def generate_schema(self, brief: dict, transcript: str) -> list[str]:
        user = (
            f"Brief: business={brief['business']!r}, audience={brief['audience']!r}, "
            f"goal={brief['goal']!r}.\nInstruction: {transcript}"
        )
        plan = self._validated(SCHEMA_SYSTEM, user, SectionPlan)
        if plan is None:
            logger.warning("generate_schema failed twice → falling back to stub heuristics")
            return self._stub.generate_schema(brief, transcript)
        return sorted(dict.fromkeys(plan.sections), key=SECTION_ORDER_INDEX.get)

    def generate_copy(self, section_type: str, brief: dict) -> dict:
        system = COPY_SYSTEM.format(
            business=brief["business"],
            audience=brief["audience"],
            goal=brief["goal"],
            tone=brief.get("tone") or "clear and friendly",
        )
        result = self._validated(system, COPY_USER[section_type], COPY_MODELS[section_type])
        if result is None:
            logger.warning("generate_copy(%s) failed twice → Gate 3 will default", section_type)
            return {}
        return result.model_dump()

    def choose_icon(self, item: dict, brief: dict, taken: list[str] | None = None,
                    hint: str | None = None) -> dict:
        user = ICON_USER.format(
            business=brief["business"],
            title=item.get("title", ""),
            caption=item.get("caption", ""),
            taken=", ".join(taken or []) or "none",
            hint=ICON_HINT.format(hint=hint) if hint else "",
        )
        choice = self._validated(ICON_SYSTEM, user, IconChoice)
        if choice is None:
            logger.warning("choose_icon failed twice → the icon stage will match on copy")
            return {}
        return choice.model_dump()

    def generate_theme(self, brief: dict, hint: str | None = None) -> dict:
        user = THEME_USER.format(
            business=brief["business"],
            audience=brief["audience"],
            goal=brief["goal"],
            tone=brief.get("tone") or "clear and friendly",
            hint=THEME_HINT.format(hint=hint) if hint else "",
        )
        choice = self._validated(
            THEME_SYSTEM.format(packs=PACK_LINES, fonts=FONT_LINES),
            user, ThemeChoice)
        if choice is None:
            logger.warning("generate_theme failed twice → page keeps the default palette")
            return {}
        return choice.model_dump()

    def choose_layouts(self, brief: dict, pack: str,
                       section_types: list[str]) -> dict:
        listing = "\n".join(
            f"- {kind}: {', '.join(variants_for(kind))}"
            for kind in section_types if variants_for(kind)
        )
        if not listing:
            return {}

        user = LAYOUT_USER.format(
            business=brief["business"],
            audience=brief["audience"],
            goal=brief["goal"],
            pack=pack,
            pack_description=PACK_DESCRIPTIONS.get(pack, "the page's own family"),
            sections=listing,
        )
        plan = self._validated(LAYOUT_SYSTEM, user, LayoutPlan, options={
            "temperature": 0.6,
            "seed": _seed(f"{brief['business']}|{pack}|{','.join(section_types)}"),
        })
        if plan is None:
            logger.warning("choose_layouts failed twice → the pack decides")
            return {}

        return {row.section: row.variant for row in plan.sections
                if row.section in section_types}

    def suggest_options(self, intent: str, args: dict, missing: list[str],
                        request: str = "") -> dict:
        known = ", ".join(f"{k}={v!r}" for k, v in args.items() if v) or "nothing yet"
        user = SUGGEST_USER.format(
            intent=intent, request=request, known=known, missing=", ".join(missing))
        result = self._validated(SUGGEST_SYSTEM, user, Suggestions)
        if result is None:
            logger.warning("suggest_options failed twice → asking without options")
            return {}
        return {
            slot.slot: [text.strip() for text in slot.options if text.strip()][:4]
            for slot in result.slots
            if slot.slot in missing
        }


class StubLanguageService:
    def interpret(self, transcript: str, pending=None) -> Interpretation:
        intent = self.classify_intent(transcript)
        brief = self.extract_brief(transcript)
        args = ExtractedArgs(
            business=brief["business"], audience=brief["audience"],
            goal=brief["goal"], tone=brief["tone"],
        )
        return Interpretation(intent=intent, args=args,
                              missing=missing_args(intent, args.model_dump()))

    def classify_intent(self, transcript: str) -> str:
        if re.search(r"\b(rewrite|regenerate|redo|rephrase)\b", transcript or "", re.IGNORECASE):
            return "regenerateSection"
        if re.search(r"\b(edit|change|update|replace|remove|delete)\b", transcript or "", re.IGNORECASE):
            return "editContent"
        return "createPage"

    def extract_brief(self, transcript: str) -> dict:
        return {
            "business": self._guess_business(transcript),
            "audience": "Local homeowners",
            "goal": "Collect enquiries",
            "tone": None,
        }

    def generate_schema(self, brief: dict, transcript: str) -> list[str]:
        text = (transcript or "").lower()

        if re.search(r"\b(break|invalid|corrupt)\b", text):
            return []

        return sections_named(text) or list(DEFAULT_SCHEMA)

    def generate_copy(self, section_type: str, brief: dict) -> dict:
        template = COPY_TEMPLATES.get(section_type, {})
        result = copy.deepcopy(template)
        if section_type == "hero":
            result["headline"] = brief["business"]
        return result

    def choose_icon(self, item: dict, brief: dict, taken: list[str] | None = None,
                    hint: str | None = None) -> dict:
        icons = build_icon_service()
        text = " ".join(filter(None, [hint, item.get("title")]))
        choice = (icons.match(text, taken or [])
                  or icons.default(len(taken or [])))
        return {"name": choice["id"]}

    def generate_theme(self, brief: dict, hint: str | None = None) -> dict:
        seed = f"{brief.get('business', '')}{hint or ''}"
        total = sum(ord(c) * (i + 1) for i, c in enumerate(seed))
        return from_hue(total % 360,
                        layout=PACK_NAMES[total % len(PACK_NAMES)],
                        font=PAIR_NAMES[total % len(PAIR_NAMES)]).model_dump()

    def choose_layouts(self, brief: dict, pack: str,
                       section_types: list[str]) -> dict:
        listing = "\n".join(
            f"- {kind}: {', '.join(variants_for(kind))}"
            for kind in section_types if variants_for(kind)
        )
        if not listing:
            return {}

        user = LAYOUT_USER.format(
            business=brief["business"],
            audience=brief["audience"],
            goal=brief["goal"],
            pack=pack,
            pack_description=PACK_DESCRIPTIONS.get(pack, "the page's own family"),
            sections=listing,
        )
        plan = self._validated(LAYOUT_SYSTEM, user, LayoutPlan, options={
            "temperature": 0.6,
            "seed": _seed(f"{brief['business']}|{pack}|{','.join(section_types)}"),
        })
        if plan is None:
            logger.warning("choose_layouts failed twice → the pack decides")
            return {}

        return {row.section: row.variant for row in plan.sections
                if row.section in section_types}

    def suggest_options(self, intent: str, args: dict, missing: list[str],
                        request: str = "") -> dict:
        return {}

    def choose_layouts(self, brief: dict, pack: str,
                       section_types: list[str]) -> dict:
        return {}

    @staticmethod
    def _guess_business(transcript: str) -> Optional[str]:
        match = re.search(r"\bfor\s+([A-Z][\w&'’]*(?:\s+[A-Z][\w&'’]*){0,3})", (transcript or "").strip())
        return match.group(1).strip(" .,") if match else None


CLIENTS = {"ollama": OllamaClient, "openrouter": OpenRouterClient}


class ModelUnknown(ValueError):
    pass


def build_language_service(provider: str | None = None, model: str | None = None):
    provider = (provider or os.environ.get("MLP_LLM") or "ollama").strip().lower()
    if provider == "stub":
        return StubLanguageService()
    if provider not in CLIENTS:
        raise ValueError(f"MLP_LLM must be one of {', '.join(LLM_PROVIDERS)}, not {provider!r}")
    return ModelLanguageService(CLIENTS[provider](model=model))


class LanguageModels:
    def __init__(self, default, choices: tuple[str, ...] = ()):
        self.default = default
        self.default_id = getattr(default, "id", "stub")
        self.ids = list(dict.fromkeys((self.default_id, *choices)))
        self._services = {self.default_id: default}

    @classmethod
    def from_env(cls, default=None) -> "LanguageModels":
        if default is None:
            default = build_language_service(os.environ.get("MLP_LLM"),
                                             os.environ.get("MLP_LLM_MODEL") or None)
        return cls(default, listed(os.environ.get("MLP_LLM_MODELS", "")))

    def check(self, model_id: str | None) -> str | None:
        if model_id and model_id not in self.ids:
            raise ModelUnknown(f"Unknown model {model_id!r}.")
        return model_id or None

    def get(self, model_id: str | None = None):
        model_id = self.check(model_id) or self.default_id
        if model_id not in self._services:
            provider, _, model = model_id.partition(":")
            self._services[model_id] = build_language_service(provider, model or None)
        return self._services[model_id]

    def describe(self) -> list[dict]:
        rows = []
        for model_id in self.ids:
            provider, _, model = model_id.partition(":")
            client = CLIENTS.get(provider)
            rows.append({"id": model_id, "label": model or provider,
                         "hint": client.hint if client else "Deterministic stub",
                         "default": model_id == self.default_id})
        return rows
