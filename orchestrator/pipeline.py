import copy
import logging
import re
from dataclasses import dataclass
from typing import Optional

from pydantic import ValidationError

import telemetry
from actions import REGISTRY, missing_args
from editor import (
    EditError,
    FIELD_ROLES,
    index_in,
    add_item,
    list_at,
    resolve_field,
    splice_path,
    add_section,
    edit_content,
    move_item,
    move_section,
    remove_item,
    set_variant,
    remove_section,
    replace_image,
    replace_image_at,
    replace_icons,
    replace_images,
    resolve_section,
    set_theme,
)
from layouts import DEFAULT_PACK, VARIANTS, fallback_pack, is_known, variant_for
from llm import DEFAULT_SCHEMA, ExtractedArgs, to_brief
from llm_client import LLMUnavailable
from mock_page import CLARIFICATIONS, VERSIONS
from providers import Providers, resolve
from session import DEFAULTS, FREE_TEXT, PendingIntent, field_question, question_for
from readiness import REVIEW_IF_GENERATED, needs_review
from schema import (
    LIST_FIELDS,
    PINNED_SECTIONS,
    contact_links,
    nav_links,
    GALLERY_SECTIONS,
    ICON_SECTIONS,
    Page,
    SECTION_MODELS,
    SECTION_ORDER,
    Theme,
    section_type_for,
    sections_named,
    summarize_errors,
)
from storage import RevisionConflict
from theme import ThemeChoice, build_theme

ALLOWED_ACTIONS = set(REGISTRY)

BUILDABLE_SECTIONS = [kind for kind in SECTION_ORDER
                      if kind in SECTION_MODELS and kind not in PINNED_SECTIONS]

CORE_SECTIONS = [kind for kind in BUILDABLE_SECTIONS if kind in DEFAULT_SCHEMA]

GALLERY_PHOTOS = 6

PHOTO_RANK = {"hero": 0, "about": 1, "contact": 2, "cta": 3}

CLAIM_SECTIONS = frozenset({"testimonials", "stats"})


def step_name(action: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", action).lower()


ORDINALS = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
            "ninth", "tenth")
COUNTS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
ENTRY_NOUNS = r"(?:step|question|benefit|item|entry|plan|review|member|photo|service|figure|detail|link)"
DIRECTIONS = (
    (r"\b(top|start|beginning)\b", "top"),
    (r"\b(bottom|end)\b", "bottom"),
    (r"\b(up|upwards?|higher|earlier|above|before)\b", "up"),
    (r"\b(down|downwards?|lower|later|below|after)\b", "down"),
)


def _ordinal_index(words: str) -> Optional[int]:
    hit = re.search(r"\b(" + "|".join(ORDINALS) + r")\b", words)
    if hit:
        return ORDINALS.index(hit.group(1))
    hit = re.search(ENTRY_NOUNS + r"s?\s+(?:number\s+)?(\d{1,2}|" + "|".join(COUNTS) + r")\b", words)
    if hit:
        value = hit.group(1)
        return int(value) - 1 if value.isdigit() else COUNTS.index(value)
    return None


def section_holding(sections: list[dict], path: str) -> dict:
    leaf = path.split(".")[-1].strip()
    if not leaf or leaf.isdigit():
        return {}
    holders = [s["type"] for s in sections if s.get("type") in LIST_FIELDS
               and index_in(s.get(LIST_FIELDS[s["type"]][0]) or [], leaf) is not None]
    if len(holders) != 1:
        return {}
    logger.info("section not extracted → %r names an entry on the %s section", leaf, holders[0])
    return {"section": holders[0]}


def _wording_slot(args: dict, slot: str, value, label: str) -> None:
    if value is not None and not args.get(slot):
        logger.info("%s not extracted → inferred %r from the wording", label, value)
        args[slot] = value


def infer_from_wording(hla: str, args: dict, transcript: str, icons=None) -> dict:
    spec = REGISTRY.get(hla)
    if spec is None or "section" not in spec.required and hla != "addSection":
        return args
    args = dict(args)
    words = (transcript or "").lower()
    named = sections_named(transcript)

    if hla == "addSection":
        _wording_slot(args, "type", named[0] if len(named) == 1 else None, "type")
        return args
    if not args.get("section") and len(named) == 1:
        _wording_slot(args, "section", named[0], "section")
    kind = args.get("section")

    if hla == "editContent" and not args.get("path"):
        parts = [role for role in FIELD_ROLES if re.search(rf"\b{re.escape(role)}\b", words)]
        if len({FIELD_ROLES[p] for p in parts}) == 1:
            _wording_slot(args, "field", parts[0], "field")

    if hla in ("removeItem", "moveItem", "setIcon") and kind in LIST_FIELDS and not args.get("path"):
        index = _ordinal_index(words)
        if index is not None:
            _wording_slot(args, "path", f"{LIST_FIELDS[kind][0]}.{index}", "path")

    if hla in ("moveSection", "moveItem") and not args.get("position") and (kind or hla == "moveItem"):
        others = [n for n in named if n != kind]
        anchor = re.search(r"\b(before|above|after|below)\b", words)
        if hla == "moveSection" and anchor and len(others) == 1:
            side = "before" if anchor.group(1) in ("before", "above") else "after"
            _wording_slot(args, "position", f"{side} {others[0]}", "position")
        else:
            for pattern, direction in DIRECTIONS:
                if re.search(pattern, words):
                    _wording_slot(args, "position", direction, "position")
                    break

    if hla == "setIcon" and icons is not None and not (args.get("icon") or args.get("query")):
        for word in re.findall(r"[a-z][a-z0-9-]+", words):
            if word not in ORDINALS and icons.resolve(word):
                _wording_slot(args, "icon", word, "icon")
                break

    if hla == "setVariant" and kind and not args.get("variant"):
        plain = re.sub(r"[-_]", " ", words)
        for variant in VARIANTS.get(kind, ()):
            if re.search(rf"\b{re.escape(variant.replace('-', ' '))}\b", plain):
                _wording_slot(args, "variant", variant, "variant")
                break
    return args


logger = logging.getLogger("mlp.pipeline")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [pipeline] %(message)s", "%H:%M:%S"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class PipelineError(Exception):
    stage = "pipeline"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
        self.trace: Optional[dict] = None


class CommandUnclear(PipelineError):
    stage = "command"


class IntentInvalid(PipelineError):
    stage = "intent"


class SchemaInvalid(PipelineError):
    stage = "schema"


class StaleRevision(PipelineError):
    stage = "conflict"

    def __init__(self, page_id: str, expected: int, current: int):
        super().__init__(
            f"The page has changed since you loaded it (you have v{expected}, "
            f"it is at v{current}) -- refresh to see the latest version.")
        self.page_id = page_id
        self.expected = expected
        self.current = current


class NeedsArgument(Exception):
    def __init__(self, name: str, options: list[str]):
        super().__init__(name)
        self.name = name
        self.options = options


class ServiceUnavailable(PipelineError):
    stage = "llm"


class TranscriptionUnavailable(ServiceUnavailable):
    stage = "stt"


class CommandCancelled(PipelineError):
    stage = "cancelled"


@dataclass
class Operation:
    kind: str
    target: Optional[str] = None
    index: Optional[int] = None

    def __str__(self) -> str:
        if self.index is not None:
            return f"{self.kind}:{self.target}#{self.index + 1}"
        return f"{self.kind}:{self.target}" if self.target else self.kind


class Trace:
    def __init__(self, instruction: str, on_step=None):
        self.instruction = instruction
        self.steps: list[dict] = []
        self.on_step = on_step

    def step(self, tool: str, args: dict, result=None, error: Optional[str] = None) -> None:
        self.steps.append({"call": {"tool": tool, "args": args}, "result": result, "error": error})
        if self.on_step is None:
            return
        event = {"index": len(self.steps), "tool": tool,
                 "section": args.get("section") or args.get("type")}
        if tool == "plan" and isinstance(result, list):
            event["total"] = len(self.steps) + len(result) + 1
        self.on_step(event)

    def to_dict(self, summary: str = "") -> dict:
        calls = telemetry.current()
        return {
            "instruction": self.instruction,
            "steps": self.steps,
            "initial_snapshot": None,
            "final_snapshot": None,
            "summary": summary,
            "telemetry": calls.summary() if calls is not None else None,
        }


MIN_COMMAND_CHARS = 6
MIN_COMMAND_WORDS = 2
ANSWER_MIN_CHARS = 2

HALLUCINATIONS = {
    "thank you",
    "thank you very much",
    "thank you for watching",
    "thanks",
    "thanks for watching",
    "please subscribe",
    "subscribe",
    "you",
    "bye",
    "okay",
    "ok",
    "uh",
    "um",
}


SECTION_SCOPED = {"editContent", "replaceImage", "removeSection",
                  "moveSection", "setVariant", "addItem", "removeItem",
                  "moveItem", "setIcon", "approveSection", "regenerateSection"}


@dataclass
class CommandContext:
    session_id: Optional[str] = None
    page_id: Optional[str] = None
    section: Optional[str] = None
    owner: Optional[str] = None
    answering: bool = False
    expected_version: Optional[int] = None
    model: Optional[str] = None


def run_command(transcript: str, language: str | None = None, store=None,
                ctx: "CommandContext | None" = None, sessions=None,
                forced: "tuple[str, dict] | None" = None, on_step=None,
                providers: Optional[Providers] = None) -> dict:
    ctx = ctx or CommandContext()
    trace = Trace(transcript, on_step)
    telemetry.start()
    try:
        return _run_command(transcript, language, store, ctx, sessions, trace,
                            resolve(providers), forced)
    except LLMUnavailable as e:
        error = ServiceUnavailable(f"The language model is unavailable -- {e}")
        error.trace = trace.to_dict(summary="failed: language model unavailable")
        logger.error("LLM unavailable: %s", e)
        raise error from e
    except PipelineError as e:
        e.trace = trace.to_dict(summary=f"rejected at {e.stage} gate")
        raise


def _run_command(transcript: str, language: str | None, store,
                 ctx: CommandContext, sessions, trace: Trace, providers: Providers,
                 forced: "tuple[str, dict] | None" = None) -> dict:
    logger.info("──────── command pipeline start ────────")
    logger.info("transcript: %r (lang=%s)", _short(transcript), language)

    if forced is not None:
        hla, args = forced
        logger.info("STEP 1 forced action=%r args=%s", hla, sorted(args))
        if hla not in ALLOWED_ACTIONS:
            raise IntentInvalid(f"Action '{hla}' isn't supported yet.")
        trace.step("interpret", {"forced": True}, {"intent": hla, "args": args})
        missing = missing_args(hla, args)
        if missing:
            raise IntentInvalid(f"Missing {', '.join(missing)} for {hla}.")
        return _edit_or_ask(hla, args, transcript, language, store, ctx, None,
                            trace, providers)

    pending = sessions.get(ctx.session_id, ctx.owner) if sessions else None

    _check_command(transcript, answering=pending is not None or ctx.answering)

    interp = providers.lang.interpret(transcript, pending)
    hla = interp.intent

    if pending is not None and hla in ("unsupported", pending.intent):
        pending.merge(interp.args.model_dump())
        hla = pending.intent
        args = dict(pending.args)
        logger.info("STEP 1 interpret → continuing %r (turn %d)", hla, pending.asked + 1)
    else:
        args = interp.args.model_dump()
        logger.info("STEP 1 interpret → action=%r", hla)

    if ctx.section and hla in SECTION_SCOPED and not args.get("section"):
        args["section"] = ctx.section
        logger.info("STEP 1 scoped to the selected %r section", ctx.section)

    if hla not in ALLOWED_ACTIONS:
        logger.warning(
            "GATE 1 (intent) REJECTED: %r not in allowed actions %s",
            hla, sorted(ALLOWED_ACTIONS),
        )
        trace.step("interpret", {"transcript": transcript}, {"intent": hla})
        if hla == "unsupported":
            if ctx.answering and pending is None:
                raise IntentInvalid(
                    "I've lost track of the question I asked -- could you give me "
                    "the whole request again?"
                )
            raise IntentInvalid(
                "I couldn't map that to a page command -- try describing the page you want."
            )
        raise IntentInvalid(
            f"Action '{hla}' isn't supported yet -- try describing a page to create."
        )
    logger.info("GATE 1 (intent) ok: %r is allowed", hla)
    trace.step("interpret", {"transcript": transcript}, {"intent": hla, "args": args})
    args = infer_from_wording(hla, args, transcript, providers.icons)

    missing = missing_args(hla, args)
    if missing and sessions is not None and ctx.session_id:
        answer = _clarify(hla, args, missing, ctx, sessions, transcript, trace, providers)
        if answer is not None:
            return answer
        stored = sessions.get(ctx.session_id, ctx.owner)
        args = dict(stored.args) if stored else args
    if sessions is not None:
        sessions.clear(ctx.session_id, ctx.owner)

    if hla != "createPage":
        return _edit_or_ask(hla, args, transcript, language, store, ctx, sessions,
                            trace, providers)

    return _run_create_page(transcript, language, args, store, trace, ctx.owner,
                            providers)


def _edit_or_ask(hla, args, transcript, language, store, ctx, sessions, trace,
                 providers: Providers):
    try:
        return run_edits([{"action": hla, "args": args}], transcript, language,
                         store, ctx, trace, providers)
    except NeedsArgument as need:
        logger.info("STEP 2 %s needs %r → asking", hla, need.name)
        if sessions is not None and ctx.session_id:
            answer = _clarify(hla, args, [need.name], ctx, sessions, transcript,
                              trace, providers, options={need.name: need.options})
            if answer is not None:
                return answer
        raise IntentInvalid(
            f"Which one would you like? {', '.join(need.options)}.") from need


def _clarify(hla, args, missing, ctx, sessions, transcript, trace,
             providers: Providers, options=None):
    pending = sessions.get(ctx.session_id, ctx.owner) or PendingIntent(
        intent=hla, args=args, page_id=ctx.page_id, owner=ctx.owner)
    pending.args = args
    pending.missing = missing
    pending.intent = hla

    if pending.exhausted:
        for name in missing:
            args.setdefault(name, DEFAULTS.get(name) or "Not specified")
        pending.args = args
        sessions.set(ctx.session_id, pending)
        logger.info("slot filling exhausted after %d turns → defaults applied", pending.asked)
        return None

    pending = sessions.ask(ctx.session_id, pending)
    question = question_for(missing)
    if options is None:
        choosable = [name for name in missing if name not in FREE_TEXT]
        options = (providers.lang.suggest_options(hla, args, choosable, transcript)
                   if choosable else {})
    fields = [{"name": name, "question": field_question(name),
               "options": options.get(name, [])} for name in missing]
    logger.info("STEP 2 clarification needed: %s (options for %s)",
                missing, sorted(options) or "none")
    trace.step("clarify", {"intent": hla, "missing": missing},
               {"question": question, "options": options})

    return {
        "_trace": trace.to_dict(summary=f"clarification: {', '.join(missing)}"),
        "recognizedCommand": transcript,
        "language": None,
        "message": question,
        "summary": _summary_so_far(args),
        "brief": {k: args.get(k) for k in ("business", "audience", "goal", "tone")},
        "clarification": {
            "needed": True,
            "question": question,
            "missing": missing,
            "fields": fields,
            "sessionId": ctx.session_id,
            "intent": hla,
            "asked": pending.asked,
            "limit": pending.limit,
        },
        "clarifications": [question],
        "versions": [],
        "plan": {"action": hla, "schema": [], "operations": []},
        "validation": {"valid": True, "gates": {"intent": "ok"}},
    }


def _summary_so_far(args: dict) -> str:
    business = args.get("business")
    if not business:
        return "Working out what to build."
    goal = args.get("goal")
    return (f"Building a landing page for {business} to {goal.lower()}."
            if goal else f"Building a landing page for {business}.")


def _run_create_page(transcript: str, language: str | None, args: dict,
                     store, trace: Trace, owner: Optional[str],
                     providers: Providers) -> dict:
    hla = "createPage"
    brief = to_brief(ExtractedArgs(**{
        k: v for k, v in args.items() if k in ExtractedArgs.model_fields
    }), transcript)
    logger.info(
        "STEP 2/4 brief extracted: business=%r audience=%r goal=%r",
        brief["business"], brief["audience"], brief["goal"],
    )

    schema = providers.lang.generate_schema(brief, transcript)
    logger.info("STEP 3/4 schema generated: %d sections %s", len(schema), schema)
    trace.step("generate_schema", {}, schema)

    operations = _plan_operations(schema)
    logger.info("STEP 4/4 planner produced %d atomic operations:", len(operations))
    for i, op in enumerate(operations, 1):
        logger.info("    OAO %02d/%02d  %s", i, len(operations), op)
    trace.step("plan", {"schema": schema}, [str(o) for o in operations])

    page, operations_status, theme_status, layout_status = _execute_operations(
        operations, brief, trace, providers)

    logger.info(
        "gates: intent=ok operations=%s theme=%s layout=%s schema=ok → "
        "page %s (%d sections)",
        operations_status, theme_status, layout_status, page.url,
        len(page.sections),
    )

    versions: list[dict] = []
    if store is not None:
        doc = store.create(page, owner, brief=brief)
        page = Page(id=doc["_id"], version=doc["version"], name=doc["name"],
                    url=doc["url"], sections=doc["sections"], theme=doc["theme"])
        versions = _versions(doc)
        trace.step("save_draft", {"url": page.url, "page_id": page.id}, "ok")
        logger.info("draft persisted %s as %s (unpublished)", page.url, page.id)

    logger.info("──────── pipeline done: VALID ────────")

    business = brief["business"]
    return {
        "_trace": trace.to_dict(summary=f"page {page.url} ({len(page.sections)} sections)"),
        "recognizedCommand": transcript,
        "language": language,
        "message": (
            f"Okay, understood -- I've drafted a {len(page.sections)}-section page "
            f"for {business}."
        ),
        "summary": f"Building a landing page for {business} to {brief['goal'].lower()}.",
        "brief": brief,
        "clarifications": CLARIFICATIONS,
        "versions": versions or VERSIONS,
        "page": page.model_dump(),
        "plan": {
            "action": hla,
            "schema": schema,
            "operations": [str(o) for o in operations],
        },
        "validation": {
            "valid": True,
            "gates": {"intent": "ok", "schema": "ok", "operations": operations_status,
                      "theme": theme_status, "layout": layout_status},
        },
    }


def run_edits(changes: list[dict], transcript: str, language: str | None,
              store, ctx: CommandContext, trace: Trace,
              providers: Optional[Providers] = None) -> dict:
    providers = resolve(providers)
    if store is None or not ctx.page_id:
        raise IntentInvalid("Create a page first, then I can edit it.")
    if not changes:
        raise IntentInvalid("There was nothing to save.")

    try:
        doc = store.get(ctx.page_id, ctx.owner)
    except KeyError:
        raise IntentInvalid("I can't find that page.") from None

    expected = ctx.expected_version if ctx.expected_version is not None else doc["version"]
    if expected != doc["version"]:
        raise StaleRevision(ctx.page_id, expected, doc["version"])

    sections = doc.get("sections", [])
    theme = doc.get("theme")
    name = doc.get("name", "Your Business")
    layout = (theme or {}).get("layout") or DEFAULT_PACK
    brief = {"business": name, "audience": "Local customers",
             "goal": "Generate enquiries", "tone": None,
             **{k: v for k, v in (doc.get("brief") or {}).items() if v}}
    brief["business"] = name
    trace.step("load_page", {"url": doc["url"], "page_id": ctx.page_id},
               {"sections": len(sections), "layout": layout, "version": doc["version"]})

    labels: list[str] = []
    for change in changes:
        action = change.get("action")
        args = change.get("args") or {}
        if action not in ALLOWED_ACTIONS:
            raise IntentInvalid(f"Action '{action}' isn't supported yet.")
        if not args.get("section") and args.get("path"):
            args = {**args, **section_holding(sections, args["path"])}

        try:
            sections, theme, name, label = _apply_edit(
                action, args, sections, theme, name, brief, doc, layout, trace,
                providers)
        except EditError as e:
            logger.warning("edit rejected: %s", e)
            trace.step(step_name(action), args, error=str(e))
            raise IntentInvalid(str(e)) from e

        labels.append(label)
        trace.step(step_name(action), args, {"sections": len(sections)})

    page_dict = {"id": ctx.page_id, "version": doc["version"], "name": name,
                 "url": doc["url"], "sections": sections, "theme": theme}
    try:
        page = Page(**page_dict)
    except ValidationError as e:
        message = summarize_errors(e)
        logger.warning("GATE 2 (schema) REJECTED after edit: %s", message)
        trace.step("assemble_page", {"url": doc["url"]}, error=message)
        raise SchemaInvalid(message) from e
    trace.step("assemble_page", {"url": doc["url"], "name": page.name},
               {"url": page.url, "sections": len(page.sections)})

    label = _summarize_edits(labels)
    saved = page.model_dump()
    note = _rewrite_note(changes, saved["sections"])
    try:
        version = store.append_version(ctx.page_id, ctx.owner, expected, label,
                                       saved["sections"], saved["theme"], saved["name"])
    except RevisionConflict as e:
        raise StaleRevision(e.page_id, e.expected, e.current) from e
    trace.step("save_draft", {"url": page.url, "page_id": ctx.page_id}, "ok")
    logger.info("%s → %s (v%d)", [c.get("action") for c in changes], label, version)

    stored = store.get(ctx.page_id, ctx.owner)
    brief["business"] = page.name
    return {
        "_trace": trace.to_dict(summary=f"{label} on {page.url}"),
        "recognizedCommand": transcript,
        "language": language,
        "message": f"Done -- {label[0].lower()}{label[1:]}.{note}",
        "summary": f"Editing {page.name}.",
        "brief": brief,
        "clarifications": [],
        "versions": _versions(stored),
        "page": {**page.model_dump(), "version": version},
        "plan": {"action": changes[0].get("action"),
                 "schema": [s["type"] for s in sections],
                 "operations": [str(c.get("action")) for c in changes]},
        "validation": {"valid": True,
                       "gates": {"intent": "ok", "schema": "ok", "operations": "ok"}},
    }


def _summarize_edits(labels: list[str]) -> str:
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1].lower()}"
    return f"{len(labels)} changes"


def _apply_edit(hla: str, args: dict, sections: list[dict], theme, name: str,
                brief: dict, doc: dict, layout: str, trace: Trace,
                providers: Providers):
    images, icons = providers.images, providers.icons

    if hla == "setTheme":
        theme, label = _retheme(theme, args, brief, trace, providers)

    elif hla == "setName":
        name, label = _rename_business(args.get("value"))
        sections = [{**s, "name": name} if s.get("type") in PINNED_SECTIONS else s
                    for s in sections]

    elif hla == "editContent":
        sections, label = edit_content(
            sections, args.get("section"), args.get("field"), args.get("value"),
            args.get("path"))

    elif hla == "replaceImage" and args.get("path"):
        query = args.get("query") or name
        choice = images.select("hero", query)
        trace.step("select_image",
                   {"section": args.get("section"), "path": args.get("path"),
                    "query": query}, {"id": choice.get("id")})
        sections, label = replace_image_at(
            sections, args.get("section"), args["path"], choice)

    elif hla == "replaceImage":
        target = sections[resolve_section(sections, args.get("section"))]
        if target["type"] in ICON_SECTIONS:
            replaced = _taken_icons(target.get("items", []))
            items = [{"title": item.get("title"), "caption": item.get("caption")}
                     for item in target.get("items", [])]
            for index, item in enumerate(items):
                _select_icon(item, brief, replaced + _taken_icons(items), trace,
                             target["type"], index, providers, hint=args.get("query"))
            sections, label = replace_icons(sections, args.get("section"),
                                            [item["icon"] for item in items])
        else:
            query = (args.get("query")
                     or f"{doc.get('name', '')} {args.get('section', '')}")
            field = GALLERY_SECTIONS.get(target["type"])
            if field is None:
                choice = images.select("hero", query)
                trace.step("select_image",
                           {"section": args.get("section"), "query": query},
                           {"id": choice.get("id")})
                sections, label = replace_image(sections, args.get("section"), choice)
            else:
                count = len(target.get(field, []))
                choices = [images.select("hero", query, index)
                           for index in range(count)]
                trace.step("select_image",
                           {"section": args.get("section"), "query": query,
                            "count": count},
                           {"ids": [c.get("id") for c in choices]})
                sections, label = replace_images(sections, args.get("section"), choices)

    elif hla in ("addSection", "removeSection") and (
            section_type_for(args.get("section") or args.get("type"))
            in PINNED_SECTIONS):
        target = section_type_for(args.get("section") or args.get("type"))
        raise EditError(
            f"Every page has a {target} and it sits where it sits -- "
            f"tell me what it should say instead.")

    elif hla == "addSection":
        if args.get("type"):
            kind = _section_type(args["type"])
            built = _build_section(kind, brief, trace, providers, layout,
                                   subject=_page_subject(sections))
            if built is None:
                raise EditError(
                    f"I couldn't write a {kind} section I'd stand behind -- "
                    f"add it once you have real {kind} to show.")
            sections, label = add_section(sections, kind, built, args.get("position"))
        else:
            sections, label = _fill_out(sections, brief, trace, providers, layout)

    elif hla == "addItem":
        kind = section_type_for(args.get("section"))
        sections, label = add_item(sections, args.get("section"),
                                   _default_entry(kind or "", icons, args.get("path")),
                                   args.get("path"))

    elif hla == "removeItem":
        sections, label = remove_item(sections, args.get("section"),
                                      args.get("path"))

    elif hla == "moveItem":
        sections, label = move_item(sections, args.get("section"),
                                    args.get("path"), args.get("position"))

    elif hla == "setIcon":
        chosen = icons.resolve(args.get("icon") or "") or icons.match(
            args.get("icon") or args.get("query") or "")
        if chosen is None:
            raise EditError(
                f"I don't know an icon called '{args.get('icon')}'.")
        trace.step("select_icon", {"section": args.get("section"),
                                   "path": args.get("path")},
                   {"icon": chosen["id"]})
        sections, label = replace_image_at(
            sections, args.get("section"), args.get("path") or "icon", chosen)

    elif hla == "moveSection":
        sections, label = move_section(
            sections, args.get("section"), args.get("position"))

    elif hla == "setVariant":
        sections, label = set_variant(
            sections, args.get("section"), args.get("variant"))

    elif hla == "removeSection":
        sections, label = remove_section(sections, args.get("section"))

    elif hla == "approveSection":
        sections, label = _approve_section(sections, args.get("section"))

    elif hla == "regenerateSection":
        sections, label = _regenerate_section(
            sections, args.get("section"), args.get("query"), brief, trace, providers,
            layout, field=args.get("field"), path=args.get("path"))

    else:  # pragma: no cover
        raise IntentInvalid(f"Action '{hla}' isn't supported yet.")

    if hla == "editContent" and args.get("section"):
        sections = _mark_edited(sections, args.get("section"), args)

    return sections, theme, name, label


def _regenerate_section(sections: list[dict], section: Optional[str],
                        hint: Optional[str], brief: dict, trace: Trace,
                        providers: Providers, layout: Optional[str],
                        field: Optional[str] = None, path: Optional[str] = None):
    index = resolve_section(sections, section)
    current = sections[index]
    kind = current["type"]
    if kind in PINNED_SECTIONS:
        raise EditError(
            f"The {kind} follows the rest of the page -- edit its links and name "
            f"in the panel instead.")
    steered = {**brief, "tone": " -- ".join(filter(None, [brief.get("tone"), hint]))
               or None}
    built = _build_section(kind, steered, trace, providers, layout,
                           variants={kind: current.get("variant")},
                           subject=_page_subject(sections))
    if built is None or built.get("provenance") == "placeholder":
        raise EditError(
            f"I couldn't write a usable {kind} section this time -- try again, "
            f"or edit it in the panel.")

    if not field and not path:
        updated = list(sections)
        updated[index] = {**built, "anchor": current.get("anchor") or built.get("anchor")}
        return updated, f"Rewrote {kind}"

    target = copy.deepcopy(current)
    if path:
        splice_path(target, built, path)
        scope = _scope_label(kind, path)
    else:
        name = resolve_field(kind, field)
        if name not in built:
            raise EditError(f"I can't rewrite '{field}' on the {kind} section.")
        target[name] = built[name]
        scope = f"{kind} {name}"
    target["provenance"] = "generated"
    target["reviewed"] = False
    updated = list(sections)
    updated[index] = target
    return updated, f"Rewrote {scope}"


def _scope_label(kind: str, path: str) -> str:
    steps = [step for step in path.split(".") if step]
    list_field, noun = LIST_FIELDS.get(kind, (None, "entry"))
    if steps[0] != list_field:
        return f"{kind} {steps[-1]}"
    if len(steps) == 1:
        return f"every {noun.lower()} in {kind}"
    which = str(int(steps[1]) + 1) if steps[1].isdigit() else steps[1]
    return f"{noun.lower()} {which} in {kind}"


def _rewrite_note(changes: list[dict], sections: list[dict]) -> str:
    rewritten = {section_type_for(c.get("args", {}).get("section"))
                 for c in changes if c.get("action") == "regenerateSection"}
    flagged = [s["type"] for s in sections if s["type"] in rewritten and needs_review(s)]
    if not flagged:
        return ""
    return (f" The {', '.join(flagged)} copy is still invented -- paste the real "
            f"thing in the panel, or approve it if it's fine as an example.")


def _approve_section(sections: list[dict], section: Optional[str]):
    index = resolve_section(sections, section)
    target = sections[index]
    if target.get("provenance") == "placeholder":
        raise EditError(
            f"The {target['type']} section is placeholder text -- it needs real "
            f"content, not approval.")
    if not needs_review(target):
        raise EditError("There is nothing to approve in that section.")
    updated = list(sections)
    updated[index] = {**target, "reviewed": True}
    return updated, f"Approved {target['type']}"


def _takes_ownership(section: dict, args: dict) -> bool:
    kind = section.get("type", "")
    if section.get("provenance") == "placeholder":
        return True
    if kind not in REVIEW_IF_GENERATED:
        return True
    claims = LIST_FIELDS.get(kind, (None, ""))[0]
    target = args.get("path") or resolve_field(kind, args.get("field"))
    return bool(claims) and (target or "").split(".")[0] == claims


def _mark_edited(sections: list[dict], section: Optional[str],
                 args: dict) -> list[dict]:
    try:
        index = resolve_section(sections, section)
    except EditError:
        return sections
    if not _takes_ownership(sections[index], args):
        return sections
    updated = list(sections)
    updated[index] = {**updated[index], "provenance": "edited"}
    return updated


def _rename_business(value: Optional[str]):
    business = (value or "").strip()
    if not business:
        raise EditError("What is the business called?")
    return business, f"Renamed to {business}"


def _retheme(current: Optional[dict], args: dict, brief: dict, trace: Trace,
             providers: Providers):
    if any(args.get(key) for key in ("primary", "accent", "background")):
        return set_theme(current, args)

    theme, status = _select_theme(brief, trace, providers, args.get("style"))
    if theme is None:
        raise EditError("I couldn't come up with a palette -- try naming a colour.")

    tokens = theme.model_dump()
    tokens["layout"] = (current or {}).get("layout") or tokens.get("layout")
    tokens["font"] = (current or {}).get("font") or tokens.get("font")

    label = f"Applied {theme.name} palette"
    return tokens, label if status != "repaired" else f"{label} (adjusted)"


def _section_type(name: Optional[str]) -> str:
    kind = section_type_for(name)
    if kind is None:
        raise EditError(f"I don't know how to add a '{name}' section.")
    if kind not in SECTION_MODELS:
        raise EditError(f"I can't build a {kind} section yet.")
    return kind


def _fill_out(sections: list[dict], brief: dict, trace: Trace, providers: Providers,
              layout: Optional[str] = None):
    present = {s.get("type") for s in sections}
    missing = [kind for kind in CORE_SECTIONS if kind not in present]
    if not missing:
        optional = [kind for kind in BUILDABLE_SECTIONS if kind not in present]
        if not optional:
            raise EditError("The page already has every section I can build.")
        raise NeedsArgument("type", optional)

    updated = sections
    added: list[str] = []
    for kind in missing:
        built = _build_section(kind, brief, trace, providers, layout,
                               subject=_page_subject(updated))
        if built is None:
            continue
        updated, _ = add_section(updated, kind, built)
        added.append(kind)

    if not added:
        raise EditError("I couldn't write any of the missing sections -- "
                        "try adding them one at a time.")
    label = (f"Added {added[0]} section" if len(added) == 1
             else f"Added {len(added)} sections")
    return updated, label


def _build_section(kind: str, brief: dict, trace: Trace, providers: Providers,
                   layout: Optional[str] = None,
                   variants: Optional[dict] = None,
                   subject: Optional[str] = None) -> Optional[dict]:
    raw = {"type": kind, **_recase(providers.lang.generate_copy(kind, brief),
                                   brief.get("business"))}
    trace.step("generate_copy", {"section": kind}, _copy_result(raw))
    if kind in ICON_SECTIONS:
        items = raw.get("items", [])
        for index, item in enumerate(items):
            _select_icon(item, brief, _taken_icons(items), trace, kind, index, providers)
    else:
        _attach_images(kind, raw, brief, providers, subject)
        trace.step("select_image", {"section": kind}, "attached")

    raw["variant"] = (variants or {}).get(kind) or variant_for(layout, kind)
    raw.setdefault("anchor", kind)
    raw["provenance"] = "generated"
    args = {"section": kind, "variant": raw["variant"]}
    try:
        model = SECTION_MODELS[kind](**raw)
        trace.step("assemble_section", args, "ok")
        return model.model_dump()
    except ValidationError as e:
        fallback = _default_section(kind, providers.icons, layout)
        trace.step("assemble_section", args,
                   "defaulted" if fallback is not None else "omitted",
                   error=summarize_errors(e))
        return fallback


def _versions(doc: dict) -> list[dict]:
    return [{"id": f"v{v['version']}", "label": v["label"], "when": v["when"]}
            for v in reversed(doc.get("versions", []))]


MIN_LATIN_RATIO = 0.5


def _check_command(transcript: str, answering: bool = False) -> None:
    text = (transcript or "").strip()
    words = re.findall(r"[A-Za-z]{2,}", text)
    normalized = re.sub(r"[^a-z ]", "", text.lower()).strip()

    min_chars = ANSWER_MIN_CHARS if answering else MIN_COMMAND_CHARS
    min_words = 1 if answering else MIN_COMMAND_WORDS
    if len(text) < min_chars or len(words) < min_words:
        logger.warning("GATE 0 (command) REJECTED: transcript too short/unclear: %r", text)
        raise CommandUnclear(
            "I didn't catch that -- could you say your answer again?"
            if answering else
            "That didn't sound like a command -- try saying something like "
            "\"a landing page for window installers\"."
        )

    letters = [c for c in text if c.isalpha()]
    if letters:
        latin = sum(1 for c in letters if c.isascii())
        if latin / len(letters) < MIN_LATIN_RATIO:
            logger.warning(
                "GATE 0 (command) REJECTED: non-Latin transcript (%.0f%% Latin): %r",
                100 * latin / len(letters), _short(text, 40))
            raise CommandUnclear(
                "That came through in another language -- try again in English."
            )

    if normalized in HALLUCINATIONS:
        logger.warning("GATE 0 (command) REJECTED: likely silence/hallucination: %r", text)
        raise CommandUnclear(
            "I didn't hear a command -- hold the mic and describe the page you want."
        )

    logger.info("GATE 0 (command) ok: %d words", len(words))


def _plan_operations(schema: list[str]) -> list[Operation]:
    operations: list[Operation] = [Operation("select_theme"),
                                   Operation("select_layout")]
    for section_type in schema:
        operations.append(Operation("generate_copy", section_type))
        operations.append(Operation(
            "select_icon" if section_type in ICON_SECTIONS else "select_image",
            section_type))
        operations.append(Operation("assemble_section", section_type))
    operations.append(Operation("assemble_page"))
    return operations


def _expand_icon_ops(operations: list[Operation], section: str, count: int) -> int:
    for i, op in enumerate(operations):
        if op.kind == "select_icon" and op.target == section and op.index is None:
            operations[i:i + 1] = [Operation("select_icon", section, index=n)
                                   for n in range(count)]
            return count
    return 0


def _execute_operations(operations: list[Operation], brief: dict, trace: Trace,
                        providers: Providers):
    drafts: dict[str, dict] = {}
    sections: list[dict] = []
    operations_status = "ok"
    theme: Theme | None = None
    theme_status = "skipped"
    layout = DEFAULT_PACK
    layout_status = "skipped"
    variants: dict[str, str] = {}
    page: Page | None = None

    i = 0
    while i < len(operations):
        op = operations[i]
        i += 1
        prefix = f"exec {i:02d}/{len(operations)} {op}"

        if op.kind == "select_theme":
            theme, theme_status = _select_theme(brief, trace, providers)
            layout = ((theme.layout if theme else None)
                      or fallback_pack(brief["business"]))
            logger.info("%s → %s, %s layout (%s)", prefix,
                        theme.name if theme else "default palette", layout,
                        theme_status)

        elif op.kind == "select_layout":
            variants, layout_status = _choose_layouts(
                brief, layout, [str(o.target) for o in operations
                                if o.kind == "assemble_section"], trace, providers)
            logger.info("%s → %d chosen (%s)", prefix, len(variants), layout_status)

        elif op.kind == "generate_copy":
            drafts[op.target] = {"type": op.target, **_recase(
                providers.lang.generate_copy(op.target, brief), brief.get("business"))}
            logger.info("%s → copy fields: %s", prefix, list(drafts[op.target].keys()))
            trace.step("generate_copy", {"section": op.target},
                       _copy_result(drafts[op.target]))
            if op.target in ICON_SECTIONS:
                count = _expand_icon_ops(
                    operations, op.target, len(drafts[op.target].get("items", [])))
                logger.info("     plan refined: select_icon:%s → %d item operation(s)",
                            op.target, count)

        elif op.kind == "select_image":
            _attach_images(op.target, drafts[op.target], brief, providers,
                           _page_subject(drafts.values()))
            logger.info("%s → images attached", prefix)
            trace.step("select_image", {"section": op.target}, "attached")

        elif op.kind == "select_icon":
            item = drafts[op.target]["items"][op.index]
            status = _select_icon(item, brief,
                                  _taken_icons(drafts[op.target]["items"]),
                                  trace, op.target, op.index, providers)
            if status == "defaulted":
                operations_status = "defaulted"
            logger.info("%s → %s (%s)", prefix, item["icon"]["id"], status)

        elif op.kind == "assemble_section":
            raw = {"anchor": op.target, **drafts[op.target],
                   "variant": variants.get(op.target) or variant_for(layout, op.target),
                   "provenance": "generated"}
            args = {"section": op.target, "variant": raw["variant"]}
            try:
                model = SECTION_MODELS[op.target](**raw)
                sections.append(model.model_dump())
                logger.info("%s → GATE 3 ok (%s)", prefix, raw["variant"])
                trace.step("assemble_section", args, "ok")
            except ValidationError as e:
                fallback = _default_section(op.target, providers.icons, layout,
                                            variants.get(op.target))
                operations_status = "defaulted"
                if fallback is None:
                    logger.warning(
                        "%s → GATE 3 failed (%d error(s)) → section omitted",
                        prefix, e.error_count(),
                    )
                    trace.step("assemble_section", args, "omitted",
                               error=summarize_errors(e))
                else:
                    sections.append(fallback)
                    logger.warning(
                        "%s → GATE 3 failed (%d error(s)) → applied placeholder",
                        prefix, e.error_count(),
                    )
                    trace.step("assemble_section", args, "defaulted",
                               error=summarize_errors(e))

        elif op.kind == "assemble_page":
            args = {"name": brief["business"], "sections": [s["type"] for s in sections],
                    "theme": theme.name if theme else None}
            try:
                if not sections:
                    message = "the page has no sections"
                    logger.warning("GATE 2 (schema) REJECTED: %s", message)
                    trace.step("assemble_page", args, error=message)
                    raise SchemaInvalid(message)

                header, footer = _build_chrome(brief, layout, trace, sections, providers)
                framed = [header, *sections, footer]
                page = _assemble_page(brief, framed, theme)
            except SchemaInvalid as e:
                trace.step("assemble_page", args, error=e.message)
                raise
            logger.info("%s → GATE 2 ok", prefix)
            trace.step("assemble_page", args,
                       {"url": page.url, "sections": len(page.sections)})

    assert page is not None, "planner must end with an assemble_page operation"
    return page, operations_status, theme_status, layout_status


_ADDRESS = re.compile(r"@|://")


def _recase(value, business: Optional[str]):
    if isinstance(value, list):
        return [_recase(item, business) for item in value]
    if isinstance(value, dict):
        return {key: _recase(item, business) for key, item in value.items()}
    if not isinstance(value, str) or _ADDRESS.search(value):
        return value

    value = re.sub(r"\bi\b", "I", value)
    if business:
        spelling = r"\s*".join(re.escape(c) for c in business if not c.isspace())
        value = re.sub(rf"\b{spelling}\b", business, value, flags=re.I)
    return re.sub(r"(^\W*|(?<=[.!?])\s+)([a-z])",
                  lambda m: m.group(1) + m.group(2).upper(), value)


def _page_subject(sections) -> Optional[str]:
    by_type = {s.get("type"): s for s in sections if isinstance(s, dict)}
    for kind in sorted(PHOTO_RANK, key=PHOTO_RANK.get):
        image = (by_type.get(kind) or {}).get("image")
        if image and image.get("category"):
            return image["category"]
    return None


def _attach_images(section_type: str, section: dict, brief: dict,
                   providers: Providers, subject: Optional[str] = None) -> None:
    images, icons = providers.images, providers.icons
    business = brief.get("business")
    rank = PHOTO_RANK.get(section_type, 0)

    if section_type == "hero":
        section["image"] = images.select("hero", " ".join(filter(None, [
            business, section.get("headline"), section.get("subhead"),
            brief.get("audience"),
        ])), rank)

    elif section_type == "about":
        body = section.get("body") or []
        section["image"] = images.select("hero", " ".join(filter(None, [
            business, section.get("heading"), body[0] if body else None,
        ])), rank)

    elif section_type == "services":
        for index, item in enumerate(section.get("items", [])):
            item["image"] = images.select("hero", " ".join(filter(None, [
                business, item.get("title"), item.get("caption"),
            ])), index)

    elif section_type == "gallery":
        query = " ".join(filter(None, [business, section.get("heading"),
                                       section.get("subhead")]))
        section["images"] = images.related(query, GALLERY_PHOTOS, subject)

    elif section_type == "contact":
        section["image"] = images.select("hero", " ".join(filter(None, [
            business, "premises storefront", brief.get("audience"),
        ])), rank)
        for detail in section.get("details", []):
            match = icons.match(detail.get("label", ""))
            if match is not None:
                detail["icon"] = match

    elif section_type == "cta":
        section["image"] = images.select("hero", " ".join(filter(None, [
            business, section.get("headline"), brief.get("goal"),
        ])), rank)


def _copy_result(draft: dict) -> dict:
    result = {"fields": list(draft.keys())}
    titles = [item["title"] for item in draft.get("items", []) if item.get("title")]
    if titles:
        result["titles"] = titles
    return result


def _taken_icons(items: list[dict]) -> list[str]:
    return [item["icon"]["id"] for item in items
            if isinstance(item.get("icon"), dict) and item["icon"].get("id")]


def _select_icon(item: dict, brief: dict, taken: list[str], trace: Trace,
                 section: str, index: int, providers: Providers,
                 hint: str | None = None) -> str:
    icons = providers.icons
    args = {"section": section, "item": index + 1,
            "title": item.get("title", ""), "taken": taken}
    requested = (providers.lang.choose_icon(item, brief, taken, hint) or {}).get("name", "")

    choice, status = icons.resolve(requested), "ok"
    if choice is not None and choice["id"] in taken:
        choice = None
    if choice is None:
        choice = (icons.match(requested, taken)
                  or icons.match(item.get("title", ""), taken))
        status = "repaired"
    if choice is None:
        choice = icons.default(index, taken)
        status = "defaulted"

    item["icon"] = choice
    trace.step("select_icon", args,
               {"icon": choice["id"], "requested": requested, "status": status})
    return status


def _choose_layouts(brief: dict, pack: str, section_types: list[str],
                    trace: Trace, providers: Providers) -> tuple[dict, str]:
    args = {"pack": pack, "sections": section_types}
    chosen = providers.lang.choose_layouts(brief, pack, section_types)

    accepted = {kind: variant for kind, variant in chosen.items()
                if is_known(kind, variant)}
    refused = sorted(set(chosen) - set(accepted))
    if refused:
        logger.info("layout: %s refused (not a variant of that section)", refused)

    if not accepted:
        trace.step("select_layout", args, "defaulted")
        return {}, "defaulted"

    status = "repaired" if refused else "ok"
    trace.step("select_layout", args,
               {"variants": accepted, "refused": refused, "status": status})
    return accepted, status


def _select_theme(brief: dict, trace: Trace, providers: Providers,
                  hint: str | None = None):
    args = {"business": brief["business"], "hint": hint}
    raw = providers.lang.generate_theme(brief, hint)
    if not raw:
        trace.step("select_theme", args, "defaulted")
        return None, "defaulted"

    try:
        theme, repairs = build_theme(ThemeChoice(**raw), refine=True)
    except ValidationError as e:
        logger.warning("theme rejected: %s", summarize_errors(e))
        trace.step("select_theme", args, "defaulted", error=summarize_errors(e))
        return None, "defaulted"

    if repairs:
        logger.info("theme %r repaired: %s", theme.name, "; ".join(repairs))
    status = "repaired" if repairs else "ok"
    trace.step("select_theme", args, {
        "name": theme.name,
        "layout": theme.layout,
        "primary": theme.primary,
        "accent": theme.accent,
        "background": theme.background,
        "repairs": repairs,
        "status": status,
    })
    return theme, status


def _build_chrome(brief: dict, layout: Optional[str], trace: Trace,
                  sections: list[dict], providers: Providers) -> tuple[dict, dict]:
    icons = providers.icons
    query = " ".join(filter(None, [brief.get("business"), brief.get("goal"),
                                   brief.get("audience")]))
    mark = icons.match(query) or icons.default(0)
    name = brief["business"]
    trace.step("select_brand_mark", {"business": name}, {"icon": mark["id"]})

    links = nav_links(sections)
    header = {"type": "header", "anchor": "header", "name": name, "icon": mark,
              "links": links, "variant": variant_for(layout, "header")}
    footer = {"type": "footer", "anchor": "footer", "name": name, "icon": mark,
              "links_label": "Page", "links": links,
              "contacts_label": "Get in touch", "contacts": contact_links(sections),
              "variant": variant_for(layout, "footer")}
    return header, footer


def _assemble_page(brief: dict, sections: list[dict],
                   theme: Theme | None = None) -> Page:
    page_dict = {
        "version": 1,
        "name": brief["business"],
        "url": _slugify(brief["business"]),
        "sections": sections,
        "theme": theme.model_dump() if theme else None,
    }
    try:
        return Page(**page_dict)
    except ValidationError as e:
        message = summarize_errors(e)
        logger.warning("GATE 2 (schema) REJECTED: %s", message)
        raise SchemaInvalid(message) from e


def _default_entry(kind: str, icons, path: Optional[str] = None) -> object:
    placeholder = {"src": "/images/hero-section.jpg", "alt": ""}
    field = list_at(kind, path)[0].split(".")[-1] if path else None
    by_list = {
        "links": lambda: {"label": "New link", "href": "#"},
        "contacts": lambda: {"label": "New contact", "href": "#contact"},
        "features": lambda: "What is included",
        "body": lambda: "A new paragraph about the business.",
    }
    if field in by_list:
        return by_list[field]()
    entries = {
        "benefits": lambda: {"icon": icons.default(0), "title": "New benefit",
                             "caption": "What this does for the customer."},
        "services": lambda: {"title": "New service", "image": placeholder,
                             "caption": "What it is and who it is for."},
        "process": lambda: {"title": "New step",
                            "caption": "What happens at this stage."},
        "stats": lambda: {"value": "0", "label": "New figure"},
        "testimonials": lambda: {"name": "Customer name", "rating": 5,
                                 "content": "What they said, in their words."},
        "faq": lambda: {"question": "A question customers ask?",
                        "answer": "The honest answer."},
        "pricing": lambda: {"name": "New plan", "price": "On request",
                            "features": ["What is included"],
                            "button": {"label": "Enquire"}},
        "team": lambda: {"name": "New member", "role": "Their role"},
        "contact": lambda: {"icon": icons.default(0), "label": "New detail",
                            "value": "How to reach us"},
        "gallery": lambda: dict(placeholder),
        "about": lambda: "A new paragraph about the business.",
    }
    if kind not in entries:
        raise EditError(f"A {kind} section has nothing to add to.")
    return entries[kind]()


def _default_section(section_type: str, icons, layout: Optional[str] = None,
                     variant: Optional[str] = None) -> Optional[dict]:
    if section_type in CLAIM_SECTIONS:
        return None
    chosen = variant or variant_for(layout, section_type)
    anchor = section_type
    placeholder = {"src": "/images/hero-section.jpg", "alt": ""}
    defaults = {
        "hero": {
            "type": "hero",
            "headline": "Welcome",
            "image": placeholder,
            "button": {"label": "Learn more"},
        },
        "about": {
            "type": "about",
            "heading": "About us",
            "body": ["Get in touch to find out more about what we do."],
            "image": placeholder,
        },
        "benefits": {
            "type": "benefits",
            "heading": "Benefits",
            "items": [
                {"icon": icons.default(i), "title": "Benefit", "caption": "Description."}
                for i in range(3)
            ],
        },
        "services": {
            "type": "services",
            "heading": "What we do",
            "items": [
                {"title": "Our service", "caption": "Get in touch to find out more.",
                 "image": placeholder},
                {"title": "Our work", "caption": "Ask us what we can do for you.",
                 "image": placeholder},
            ],
        },
        "process": {
            "type": "process",
            "heading": "How it works",
            "items": [
                {"title": "Get in touch", "caption": "Tell us what you need."},
                {"title": "We quote", "caption": "You get a price in writing."},
                {"title": "We do the work", "caption": "Booked for a day that suits you."},
            ],
        },
        "gallery": {
            "type": "gallery",
            "heading": "Our work",
            "images": [placeholder for _ in range(3)],
        },
        "pricing": {
            "type": "pricing",
            "heading": "Pricing",
            "plans": [{
                "name": "Standard",
                "price": "On request",
                "description": "Every job is priced on what it actually needs.",
                "features": ["Ask for a quote"],
                "button": {"label": "Ask for a price"},
            }],
        },
        "team": {
            "type": "team",
            "heading": "Our team",
            "members": [
                {"name": "Team member", "role": "Their role"},
                {"name": "Team member", "role": "Their role"},
            ],
        },
        "promotion": {
            "type": "promotion",
            "title": "Your offer",
            "description": "Describe the offer here.",
            "button": {"label": "Learn more"},
        },
        "faq": {
            "type": "faq",
            "heading": "FAQ",
            "items": [{"question": "Have a question?", "answer": "Contact us."}],
        },
        "contact": {
            "type": "contact",
            "heading": "Get in touch",
            "details": [{"label": "Enquiries", "value": "Contact us for details."}],
        },
        "cta": {
            "type": "cta",
            "headline": "Ready to get started?",
            "button": {"label": "Get in touch"},
        },
    }
    return {**defaults[section_type], "variant": chosen, "anchor": anchor,
            "provenance": "placeholder"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return "/" + (slug or "page")


def _short(text: str, limit: int = 80) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def run_create_page(transcript: str, language: str | None = None, store=None,
                    ctx: "CommandContext | None" = None, sessions=None,
                    providers: Optional[Providers] = None) -> dict:
    return run_command(transcript, language, store, ctx, sessions, providers=providers)
