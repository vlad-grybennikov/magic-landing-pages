from __future__ import annotations

import copy
import re
from typing import Annotated, Optional, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError

from schema import (
    LIST_FIELDS,
    PINNED_SECTIONS,
    nav_links,
    Button,
    GALLERY_SECTIONS,
    ICON_SECTIONS,
    PHOTO_SECTIONS,
    SECTION_MODELS,
    SECTION_ORDER_INDEX,
    section_type_for,
)
from fonts import normalize_pair
from layouts import VARIANTS, normalize_variant
from theme import PAPER, ThemeChoice, brand_colors, build_theme, darken

def _plain_text_fields(model: type[BaseModel]) -> set[str]:
    editable = set()
    for name, field in model.model_fields.items():
        if name in ("type", "variant"):
            continue
        inner = [arg for arg in get_args(field.annotation) or (field.annotation,)
                 if arg is not type(None)]
        if any(arg is str or arg is Button for arg in inner):
            editable.add(name)
    return editable


EDITABLE_FIELDS: dict[str, set[str]] = {
    section_type: _plain_text_fields(model)
    for section_type, model in SECTION_MODELS.items()
}

HEADING_FIELDS = ("headline", "title", "heading", "name")

BODY_FIELDS = ("subhead", "description", "tagline")

FIELD_ROLES = {
    "headline": "title", "title": "title", "heading": "title", "header": "title",
    "subhead": "description", "subheading": "description",
    "subtitle": "description", "description": "description",
    "text": "description", "body": "description", "copy": "description",
    "eyebrow": "eyebrow", "kicker": "eyebrow",
    "button": "button", "cta": "button", "label": "button",
    "call to action": "button",
}


def resolve_field(kind: str, field: Optional[str]) -> str:
    name = (field or "").strip().lower()
    fields = EDITABLE_FIELDS.get(kind, set())
    if name in fields:
        return name

    role = FIELD_ROLES.get(name, name)
    if role in ("title", "description"):
        candidates = HEADING_FIELDS if role == "title" else BODY_FIELDS
        return next((f for f in candidates if f in fields), role)
    return role


class EditError(Exception):
    pass


def resolve_section(sections: list[dict], name: Optional[str]) -> int:
    if not name:
        raise EditError("Which section did you mean?")

    target = section_type_for(name)
    if target is None:
        raise EditError(f"I don't know a '{name}' section.")

    for index, section in enumerate(sections):
        if section.get("type") == target:
            return index
    raise EditError(f"This page has no {target} section.")


MAX_PATH_DEPTH = 6


ENTRY_NAMES = ("label", "title", "name", "question")


def _plain(text) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def index_in(entries: list, step: str) -> Optional[int]:
    if step.isdigit():
        at = int(step)
        return at if at < len(entries) else None

    wanted = _plain(step)
    if not wanted:
        return None
    names = [[_plain(entry.get(key)) for key in ENTRY_NAMES if entry.get(key)]
             if isinstance(entry, dict) else [] for entry in entries]
    for at, candidates in enumerate(names):
        if wanted in candidates:
            return at
    partial = [at for at, candidates in enumerate(names)
               if any(wanted in name for name in candidates)]
    return partial[0] if len(partial) == 1 else None


def _walk(target: dict, path: str) -> tuple[dict | list, str | int]:
    steps = [step for step in path.split(".") if step]
    if not steps or len(steps) > MAX_PATH_DEPTH:
        raise EditError(f"I can't find '{path}' on this section.")

    node: object = target
    for step in steps[:-1]:
        if isinstance(node, list):
            at = index_in(node, step)
            if at is None:
                raise EditError(f"There is no '{path}' on this section.")
            node = node[at]
        elif isinstance(node, dict) and step in node:
            node = node[step]
        else:
            raise EditError(f"There is no '{path}' on this section.")

    leaf = steps[-1]
    if isinstance(node, list):
        at = index_in(node, leaf)
        if at is None:
            raise EditError(f"There is no '{path}' on this section.")
        return node, at
    if isinstance(node, dict) and leaf in node:
        return node, leaf
    raise EditError(f"There is no '{path}' on this section.")


def _unwrap(annotation) -> tuple[object, bool]:
    if get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    if get_origin(annotation) is Union:
        rest = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(rest) < len(get_args(annotation)):
            return _unwrap(rest[0])[0], True
    return annotation, False


def _schema_at(kind: str, steps: list[str]) -> tuple[object, list[int]]:
    node: object = SECTION_MODELS[kind]
    optional_at = []
    for i, step in enumerate(steps):
        if isinstance(node, type) and issubclass(node, BaseModel):
            field = node.model_fields.get(step)
            if field is None:
                raise EditError(f"There is no '{'.'.join(steps)}' on this section.")
            node, optional = _unwrap(field.annotation)
            if optional:
                optional_at.append(i)
        elif get_origin(node) is list:
            node = _unwrap(get_args(node)[0])[0]
        else:
            raise EditError(f"There is no '{'.'.join(steps)}' on this section.")
    return node, optional_at


def splice_path(target: dict, source: dict, path: str) -> str:
    steps = [step for step in path.split(".") if step]
    container, leaf = _walk(target, path)
    node: object = target
    fresh: object = source
    for step in steps[:-1]:
        if isinstance(node, list):
            at = index_in(node, step)
            node = node[at]
            fresh = fresh[min(at, len(fresh) - 1)] if isinstance(fresh, list) and fresh else None
        else:
            node = node[step]
            fresh = fresh.get(step) if isinstance(fresh, dict) else None
    if isinstance(container, list) and isinstance(fresh, list) and fresh:
        container[leaf] = fresh[min(leaf, len(fresh) - 1)]
    elif isinstance(container, dict) and isinstance(fresh, dict) and leaf in fresh:
        container[leaf] = fresh[leaf]
    else:
        raise EditError(f"The rewrite produced nothing for '{path}'.")
    return steps[-1]


def edit_at_path(sections: list[dict], section: Optional[str], path: str,
                 value: str):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    container, leaf = _walk(target, path)
    current = container[leaf]
    steps = [step for step in path.split(".") if step]
    leaf_type, optional_at = _schema_at(kind, steps)

    if not value.strip():
        if not optional_at:
            noun = LIST_FIELDS.get(kind, ("", "section"))[1].lower()
            what = noun if len(steps) > 1 else "section"
            raise EditError(
                f"That part can't be empty -- remove the {what} instead.")
        cleared = steps[:max(optional_at) + 1]
        holder, key = _walk(target, ".".join(cleared))
        holder[key] = None
        return updated, f"Cleared {kind} {' '.join(cleared)}"

    if leaf_type is int and not isinstance(current, bool):
        if not value.strip().lstrip("-").isdigit():
            raise EditError(f"'{path}' is a number.")
        container[leaf] = int(value)
        return updated, f"Edited {kind} {path.replace('.', ' ')}"

    if current is not None and not isinstance(current, str):
        raise EditError(f"'{path}' isn't a piece of text I can change.")

    if isinstance(container, dict) and "src" in container:
        raise EditError(
            "Pictures are replaced rather than typed -- ask me to replace it.")

    if path == "anchor" and container is target:
        if any(o is not target and (o.get("anchor") or o["type"]) == value
               for o in updated):
            raise EditError(f"Another section is already reached by #{value}.")

    container[leaf] = value
    if path == "anchor" and container is target:
        was = f"#{current or kind}"
        for other in updated:
            for link in other.get("links") or []:
                if link["href"] == was:
                    link["href"] = f"#{value}"

    return updated, f"Edited {kind} {path.replace('.', ' ')}"


def edit_content(sections: list[dict], section: str, field: str, value: str,
                 path: Optional[str] = None):
    if path:
        return edit_at_path(sections, section, path, value)

    if not value:
        index = resolve_section(sections, section)
        kind = sections[index]["type"]
        return edit_at_path(sections, section, resolve_field(kind, field), "")

    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    name = resolve_field(kind, field)
    allowed = EDITABLE_FIELDS.get(kind, set())
    if name not in allowed:
        choices = ", ".join(sorted(allowed - {"anchor"}))
        if not (field or "").strip():
            raise EditError(
                f"Which part of the {kind} section should change ({choices})? "
                f"Or say \"rewrite the {kind}\" and I'll redo the whole section.")
        raise EditError(
            f"I can't change '{field}' on the {kind} section -- try {choices}.")

    if name == "button":
        target["button"] = {**(target.get("button") or {}), "label": value}
    else:
        target[name] = value

    return updated, f"Edited {kind} {name}"


def replace_image(sections: list[dict], section: str, choice: dict):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    field = PHOTO_SECTIONS.get(kind)
    if field is None:
        if kind in GALLERY_SECTIONS:
            raise EditError(
                f"The {kind} section has several photos -- say which, or ask me "
                f"to replace them all.")
        raise EditError(f"The {kind} section doesn't have a photo to replace.")

    target[field] = choice
    return updated, f"Replaced {kind} image"


def replace_image_at(sections: list[dict], section: Optional[str], path: str,
                     choice: dict):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]

    container, leaf = _walk(target, path)
    current = container[leaf]
    if isinstance(current, dict) and "src" not in current:
        picture = next((key for key in ("icon", "image", "photo")
                        if isinstance(current.get(key), dict) or key in current), None)
        if picture is None:
            raise EditError(f"'{path}' isn't a picture on this section.")
        container, leaf, path = current, picture, f"{path}.{picture}"
        current = container.get(leaf)
    if current is not None and (not isinstance(current, dict) or "src" not in current):
        raise EditError(f"'{path}' isn't a picture on this section.")

    container[leaf] = choice
    return updated, f"Replaced {target['type']} {path.replace('.', ' ')}"


def replace_images(sections: list[dict], section: str, choices: list[dict]):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    field = GALLERY_SECTIONS.get(kind)
    if field is None:
        raise EditError(f"The {kind} section doesn't have a set of photos.")

    entries = target.get(field, [])
    if len(choices) != len(entries):
        raise EditError("I couldn't find a photo for every slot.")

    if field == "images":
        target[field] = choices
    else:
        for entry, choice in zip(entries, choices):
            entry["image"] = choice

    return updated, f"Replaced {kind} images"


def replace_icons(sections: list[dict], section: str, choices: list[dict]):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    if kind not in ICON_SECTIONS:
        raise EditError(f"The {kind} section doesn't have icons.")
    if len(choices) != len(target.get("items", [])):
        raise EditError("I couldn't pick an icon for every item.")

    for item, choice in zip(target["items"], choices):
        item["icon"] = choice
    return updated, f"Replaced {kind} icons"


def _movable(sections: list[dict], index: int) -> tuple[int, int]:
    first = 1 if sections and sections[0].get("type") == "header" else 0
    last = len(sections) - 1
    if sections and sections[-1].get("type") == "footer":
        last -= 1
    return first, last


def move_section(sections: list[dict], section: Optional[str],
                 position: Optional[str]):
    index = resolve_section(sections, section)
    kind = sections[index]["type"]
    if kind in PINNED_SECTIONS:
        raise EditError(
            f"The {kind} is always in the same place -- it cannot be moved.")

    said = (position or "").strip().lower()
    if not said:
        raise EditError("Where should it go? Try up, down, top or bottom.")

    updated = copy.deepcopy(sections)
    first, last = _movable(updated, index)

    if re.search(r"\btop\b|\bstart\b|\bbeginning\b|\bfirst\b", said):
        target = first
    elif re.search(r"\bbottom\b|\bend\b|\blast\b", said):
        target = last
    elif re.search(r"\bup(?:wards?)?\b|\bhigher\b|\bearlier\b|\bbefore\b|\babove\b", said):
        target = index - 1
    elif re.search(r"\bdown(?:wards?)?\b|\blower\b|\blater\b|\bafter\b|\bbelow\b", said):
        target = index + 1
    else:
        raise EditError(
            f"I don't know where '{position}' is -- try up, down, top or bottom.")

    neighbour = section_type_for(re.sub(r"^(before|after|above|below)\s+", "", said))
    if neighbour and neighbour != kind:
        for i, existing in enumerate(updated):
            if existing.get("type") != neighbour:
                continue
            landing = i - 1 if index < i else i
            target = (landing if re.search(r"\bbefore\b|\babove\b", said)
                      else landing + 1)
            break

    target = max(first, min(target, last))
    if target == index:
        raise EditError(f"The {kind} section is already there.")

    moved = updated.pop(index)
    updated.insert(target, moved)
    return updated, f"Moved {kind} section"


def set_variant(sections: list[dict], section: Optional[str],
                variant: Optional[str]):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    available = VARIANTS.get(kind, ())
    if not available:
        raise EditError(f"The {kind} section has only one layout.")

    if variant:
        chosen = normalize_variant(variant)
        if chosen not in available:
            raise EditError(
                f"'{variant}' isn't a {kind} layout -- try "
                f"{', '.join(available[:4])}.")
    else:
        current = target.get("variant")
        at = available.index(current) if current in available else -1
        chosen = available[(at + 1) % len(available)]

    if chosen == target.get("variant"):
        raise EditError(f"The {kind} section already uses that layout.")

    target["variant"] = chosen
    return updated, f"Changed {kind} layout to {chosen}"


def list_at(kind: str, path: Optional[str]) -> tuple[str, str]:
    steps = [step for step in (path or "").split(".") if step]
    if steps and steps[-1].isdigit():
        steps = steps[:-1]
    if not steps:
        if kind not in LIST_FIELDS:
            raise EditError(f"A {kind} section has no list to add to.")
        return LIST_FIELDS[kind]

    field = ".".join(steps)
    if kind in LIST_FIELDS and field == LIST_FIELDS[kind][0]:
        return LIST_FIELDS[kind]
    leaf, _ = _schema_at(kind, steps)
    if get_origin(leaf) is not list:
        raise EditError(f"'{field}' is not a list on a {kind} section.")
    return field, LIST_NOUNS.get(steps[-1], steps[-1].rstrip("s").title())


LIST_NOUNS = {"links": "Link", "contacts": "Contact", "features": "Feature",
              "body": "Paragraph"}


def list_limits(kind: str, field: Optional[str] = None) -> tuple[int, int]:
    steps = (field or LIST_FIELDS[kind][0]).split(".")
    node: object = SECTION_MODELS[kind]
    meta: list = []
    for step in steps:
        if step.isdigit():
            continue
        info = node.model_fields[step]  # type: ignore[union-attr]
        meta = list(info.metadata)
        node, _ = _unwrap(info.annotation)
        if get_origin(node) is Annotated:
            meta += list(get_args(node)[1:])
            node = get_args(node)[0]
        if get_origin(node) is list:
            node = _unwrap(get_args(node)[0])[0]
    low = next((m.min_length for m in meta if hasattr(m, "min_length")), 1)
    high = next((m.max_length for m in meta if hasattr(m, "max_length")), 99)
    return low, high


def add_item(sections: list[dict], section: Optional[str], entry,
             path: Optional[str] = None):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    field, noun = list_at(kind, path)
    holder, key = _walk(target, field) if "." in field else (target, field)
    entries = holder[key] = list(holder.get(key) or [])
    _, high = list_limits(kind, field)
    if len(entries) >= high:
        raise EditError(
            f"That list holds at most {high} -- remove one first.")

    entries.append(entry)
    return updated, f"Added {noun.lower()} {len(entries)}"


ANCHOR = re.compile(r"\b(before|above|after|below)\s+(.+)$")


def _entry_at(kind: str, target: dict, path: Optional[str]) -> tuple[list, int, str, str]:
    steps = [step for step in (path or "").split(".") if step]
    leaf = steps.pop() if steps and (steps[-1].isdigit() or len(steps) > 1) else None
    field, noun = list_at(kind, ".".join(steps) or None)
    holder, key = _walk(target, field) if "." in field else (target, field)
    entries = holder.get(key) or []
    at = index_in(entries, leaf) if leaf is not None else None
    if at is None:
        raise EditError(f"There is no {noun.lower()} at '{path}'.")
    return entries, at, field, noun


def move_item(sections: list[dict], section: Optional[str],
              path: Optional[str], position: Optional[str]):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    entries, at, _, noun = _entry_at(kind, target, path)

    said = (position or "").strip().lower()
    anchor = ANCHOR.search(said)
    ref = index_in(entries, anchor.group(2).split(".")[-1].strip()) if anchor else None
    if ref is not None:
        to = ref if anchor.group(1) in ("before", "above") else ref + 1
        if at < to:
            to -= 1
    elif said.isdigit():
        to = int(said)
    elif re.search(r"\btop\b|\bfirst\b|\bstart\b", said):
        to = 0
    elif re.search(r"\bbottom\b|\blast\b|\bend\b", said):
        to = len(entries) - 1
    elif re.search(r"\bup(?:wards?)?\b|\bhigher\b|\bearlier\b|\bbefore\b|\babove\b", said):
        to = at - 1
    elif re.search(r"\bdown(?:wards?)?\b|\blower\b|\blater\b|\bafter\b|\bbelow\b", said):
        to = at + 1
    else:
        raise EditError("Where should it go? Try up, down, top or bottom.")

    to = max(0, min(len(entries) - 1, to))
    if to == at:
        raise EditError(f"That {noun.lower()} is already there.")
    entries.insert(to, entries.pop(at))
    return updated, f"Moved {noun.lower()} {at + 1} to {to + 1}"


def remove_item(sections: list[dict], section: Optional[str],
                path: Optional[str]):
    index = resolve_section(sections, section)
    updated = copy.deepcopy(sections)
    target = updated[index]
    kind = target["type"]

    entries, at, field, noun = _entry_at(kind, target, path)
    low, _ = list_limits(kind, field)
    if len(entries) <= low:
        raise EditError(
            f"That list needs at least {low} -- this is the last one.")

    entries.pop(at)
    return updated, f"Removed {noun.lower()} {at + 1}"


def _sync_nav(sections: list[dict], added: Optional[str] = None) -> list[dict]:
    anchors = {f"#{s.get('anchor') or s['type']}" for s in sections}
    fresh = next((link for link in nav_links(sections)
                  if added and link["href"] == f"#{added}"), None)
    order = [link["href"] for link in nav_links(sections)]

    for section in sections:
        if section["type"] not in PINNED_SECTIONS or "links" not in section:
            continue
        links = [link for link in section["links"] if link["href"] in anchors]
        if fresh and all(link["href"] != fresh["href"] for link in links):
            at = len([link for link in links
                      if order.index(link["href"]) < order.index(fresh["href"])])
            links.insert(at, dict(fresh))
        section["links"] = links
    return sections


def add_section(sections: list[dict], section_type: str, built: dict,
                position: Optional[str] = None):
    kind = built["type"]
    if any(s.get("type") == kind for s in sections):
        raise EditError(
            f"This page already has a {kind} section -- say \"rewrite the {kind}\" "
            f"to redo it, or edit it in the panel.")

    updated = copy.deepcopy(sections)
    if position and "top" in position.lower():
        updated.insert(0, built)
    elif position and ("bottom" in position.lower() or "end" in position.lower()):
        updated.append(built)
    else:
        rank = SECTION_ORDER_INDEX[kind]
        at = len(updated)
        for i, existing in enumerate(updated):
            if SECTION_ORDER_INDEX[existing["type"]] > rank:
                at = i
                break
        updated.insert(at, built)

    return _sync_nav(updated, added=kind), f"Added {kind} section"


THEME_COLORS = ("primary", "accent", "background")


def set_theme(current: Optional[dict], args: dict):
    overrides = {key: value.strip() for key in THEME_COLORS
                 if isinstance(value := args.get(key), str) and value.strip()}
    font = normalize_pair(args.get("font"))
    if not overrides and not font:
        raise EditError("Which colour should I change?")

    if not overrides:
        if current is None:
            raise EditError("Set the page's colours first.")
        return {**current, "font": font}, "Changed the typeface"

    colors = {**(brand_colors(current) if current else {}), **overrides}
    primary = colors.get("primary") or colors.get("accent")
    if not primary:
        raise EditError("Set the main colour first.")

    try:
        theme, _ = build_theme(ThemeChoice(
            name="Custom",
            hue="chosen by hand",
            layout=(current or {}).get("layout"),
            font=font or (current or {}).get("font"),
            primary=primary,
            accent=colors.get("accent") or darken(primary, 0.18),
            background=colors.get("background") or PAPER,
        ))
    except ValidationError as e:
        bad = ", ".join(sorted({str(err["loc"][0]) for err in e.errors()}))
        raise EditError(
            f"That isn't a colour I can use for {bad} -- try a hex value like #2f6f4e."
        ) from e

    return theme.model_dump(), "Updated colour scheme"


def remove_section(sections: list[dict], section: str):
    index = resolve_section(sections, section)
    if len(sections) == 1:
        raise EditError("That's the only section left -- a page needs at least one.")

    updated = copy.deepcopy(sections)
    removed = updated.pop(index)
    return _sync_nav(updated), f"Removed {removed['type']} section"
