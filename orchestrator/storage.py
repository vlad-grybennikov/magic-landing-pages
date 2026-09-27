from __future__ import annotations

import itertools
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from pymongo.errors import DuplicateKeyError

from schema import LIST_FIELDS, Page, Theme
from theme import validate_theme

FORMAT = 2


class PageNotFound(KeyError):
    pass


class VersionNotFound(KeyError):
    pass


class UrlTaken(ValueError):
    pass


class RevisionConflict(ValueError):
    def __init__(self, page_id: str, expected: int, current: int):
        super().__init__(f"{page_id} is at version {current}, not {expected}")
        self.page_id = page_id
        self.expected = expected
        self.current = current


def slugify_url(wanted: str) -> str:
    parts = [re.sub(r"[^a-z0-9]+", "-", part.lower()).strip("-")
             for part in (wanted or "").split("/")]
    path = "/".join(part for part in parts if part)
    return "/" + (path or "page")


def new_page_id() -> str:
    return uuid.uuid4().hex[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


HEAD_FIELDS = ("title", "question", "name", "label", "value")
SECTION_HEAD_FIELDS = ("headline", "heading", "title")


def _head(entry) -> str:
    if isinstance(entry, dict):
        return next((str(entry[k]) for k in HEAD_FIELDS if entry.get(k)), "")
    return str(entry)


def _icon(entry) -> str:
    icon = entry.get("icon") if isinstance(entry, dict) else None
    return str(icon.get("src") or "") if isinstance(icon, dict) else ""


def describe_sections(sections: list[dict]) -> dict:
    variants, counts, heads, section_heads, icons, images = [], [], [], [], [], []
    for section in sections:
        kind = section.get("type", "?")
        variants.append(f"{kind}:{section.get('variant') or '-'}")
        section_heads.append(
            f"{kind}:{next((str(section[k]) for k in SECTION_HEAD_FIELDS if section.get(k)), '')}")
        image = section.get("image")
        if isinstance(image, dict) and image.get("src"):
            images.append(f"{kind}:{image['src']}")
        field = LIST_FIELDS.get(kind, (None,))[0]
        if field and isinstance(section.get(field), list):
            entries = section[field]
            counts.append(f"{kind}:{len(entries)}")
            heads.append(f"{kind}:{'|'.join(_head(e) for e in entries)}")
            if any(_icon(e) for e in entries):
                icons.append(f"{kind}:{'|'.join(_icon(e) for e in entries)}")
    return {"section_variants": ",".join(variants), "item_counts": ",".join(counts),
            "item_heads": ";".join(heads), "section_heads": ";".join(section_heads),
            "item_icons": ";".join(icons), "section_images": ",".join(images)}


def _snapshot(version: int, label: str, sections: list[dict],
              theme: Optional[dict], name: str, when: str) -> dict:
    return {"version": version, "label": label, "when": when,
            "sections": sections, "theme": theme, "name": name}


class PageStore:
    def __init__(self, collection):
        self._pages = collection

    def ensure_indexes(self) -> None:
        self._pages.create_index("url", unique=True)
        self._pages.create_index([("owner", 1), ("updated", -1)])

    def create(self, page: Page, owner: str, label: str = "Initial draft",
               brief: Optional[dict] = None) -> dict:
        dumped = page.model_dump(exclude={"id"})
        now = _now()
        for n in itertools.count(1):
            url = page.url if n == 1 else f"{page.url}-{n}"
            doc = {
                "_id": new_page_id(),
                "format": FORMAT,
                "owner": owner,
                "url": url,
                "name": dumped["name"],
                "brief": brief,
                "version": 1,
                "sections": dumped["sections"],
                "theme": dumped["theme"],
                "versions": [_snapshot(1, label, dumped["sections"], dumped["theme"],
                                       dumped["name"], now)],
                "published": None,
                "created": now,
                "updated": now,
            }
            try:
                self._pages.insert_one(doc)
                return doc
            except DuplicateKeyError:
                continue
        raise AssertionError("unreachable")

    def get(self, page_id: str, owner: str) -> dict:
        doc = self._pages.find_one({"_id": page_id, "owner": owner})
        if doc is None:
            raise PageNotFound(page_id)
        return doc

    def urls(self, page_ids: list[str], owner: str) -> dict[str, str]:
        if not page_ids:
            return {}
        return {doc["_id"]: doc["url"] for doc in self._pages.find(
            {"_id": {"$in": page_ids}, "owner": owner}, {"url": 1})}

    def published(self, url: str) -> Optional[dict]:
        doc = self._pages.find_one({"url": url, "published": {"$ne": None}},
                                   {"published": 1, "url": 1})
        if doc is None:
            return None
        return {"url": doc["url"], **doc["published"]}

    def rename(self, page_id: str, owner: str, wanted: str) -> str:
        doc = self.get(page_id, owner)
        target = slugify_url(wanted)
        if target == doc["url"]:
            return target
        try:
            self._pages.update_one({"_id": page_id, "owner": owner},
                                   {"$set": {"url": target, "updated": _now()}})
        except DuplicateKeyError:
            raise UrlTaken(target) from None
        return target

    def append_version(self, page_id: str, owner: str, expected_version: int,
                       label: str, sections: list[dict],
                       theme: Optional[dict] = None,
                       name: Optional[str] = None) -> int:
        number = expected_version + 1
        now = _now()
        changed = {"version": number, "sections": sections, "updated": now}
        if theme is not None:
            changed["theme"] = theme
        if name is not None:
            changed["name"] = name

        current = self._pages.find_one(
            {"_id": page_id, "owner": owner}, {"theme": 1, "name": 1})
        if current is None:
            raise PageNotFound(page_id)
        snapshot = _snapshot(
            number, label, sections,
            theme if theme is not None else current.get("theme"),
            name if name is not None else current.get("name", ""), now)

        result = self._pages.update_one(
            {"_id": page_id, "owner": owner, "version": expected_version},
            {"$set": changed, "$push": {"versions": snapshot}},
        )
        if result.matched_count == 0:
            doc = self.get(page_id, owner)
            raise RevisionConflict(page_id, expected_version, doc["version"])
        return number

    def version_snapshot(self, page_id: str, owner: str, version: int) -> dict:
        doc = self.get(page_id, owner)
        snap = self.find_version(doc, version)
        return {
            "version": version,
            "label": snap["label"],
            "when": snap["when"],
            "sections": snap["sections"],
            "theme": snap.get("theme"),
            "name": snap.get("name") or doc.get("name", ""),
        }

    def restore_version(self, page_id: str, owner: str, version: int,
                        expected_version: Optional[int] = None) -> Page:
        doc = self.get(page_id, owner)
        snap = self.find_version(doc, version)
        theme = snap.get("theme")
        name = snap.get("name") or doc["name"]
        number = self.append_version(
            page_id, owner,
            doc["version"] if expected_version is None else expected_version,
            f"Restored v{version}", snap["sections"], theme, name)
        return Page(id=page_id, version=number, name=name, url=doc["url"],
                    sections=snap["sections"], theme=theme)

    def publish(self, page_id: str, owner: str,
                version: Optional[int] = None) -> dict:
        doc = self.get(page_id, owner)
        target = doc["version"] if version is None else version
        snap = self.find_version(doc, target)
        palette = snap.get("theme")
        if palette is not None:
            palette = validate_theme(Theme(**palette))[0].model_dump()
        page = Page(
            id=page_id,
            version=target,
            name=snap.get("name") or doc.get("name", ""),
            url=doc["url"],
            sections=snap["sections"],
            theme=palette,
        )
        dumped = page.model_dump()
        published = {"version": target, "name": dumped["name"],
                     "sections": dumped["sections"], "theme": dumped["theme"],
                     "when": _now()}
        result = self._pages.update_one(
            {"_id": page_id, "owner": owner},
            {"$set": {"published": published, "updated": published["when"]}})
        if result.matched_count == 0:
            raise PageNotFound(page_id)
        return published

    def unpublish(self, page_id: str, owner: str) -> None:
        result = self._pages.update_one(
            {"_id": page_id, "owner": owner},
            {"$set": {"published": None, "updated": _now()}})
        if result.matched_count == 0:
            raise PageNotFound(page_id)

    def snapshot(self) -> dict:
        rows = []
        for doc in self._pages.find({}):
            published = doc.get("published")
            sections = doc.get("sections", [])
            rows.append({
                "id": doc.get("url"),
                "url": doc.get("url"),
                "name": doc.get("name"),
                "owner": doc.get("owner"),
                "sections": sections,
                "theme": doc.get("theme"),
                "versions": doc.get("versions", []),
                "publish": published is not None,
                "published_version": (published or {}).get("version"),
                **describe_sections(sections),
            })
        rows.sort(key=lambda r: r["id"] or "")
        return {"tables": {"pages": rows}}

    @staticmethod
    def find_version(doc: dict, version: int) -> dict:
        for snap in doc.get("versions", []):
            if snap["version"] == version:
                return snap
        raise VersionNotFound(f"{doc.get('url')} has no version {version}")
