from __future__ import annotations

from typing import Optional

from builds import BuildStore, summary as build_summary
from pipeline import CommandContext, Trace, run_edits
from providers import Providers
from readiness import assess, enforce
from storage import PageStore


class PageService:
    def __init__(self, pages: PageStore, builds: BuildStore):
        self.pages = pages
        self.builds = builds

    @staticmethod
    def view(doc: dict) -> dict:
        published = doc.get("published")
        return {
            "id": doc["_id"],
            "version": doc.get("version", 1),
            "name": doc.get("name"),
            "url": doc["url"],
            "sections": doc.get("sections", []),
            "theme": doc.get("theme"),
            "published": ({"version": published["version"], "when": published["when"]}
                          if published else None),
            "readiness": assess(doc.get("sections", [])),
        }

    @staticmethod
    def versions(doc: dict) -> list[dict]:
        published = (doc.get("published") or {}).get("version")
        return [{"id": f"v{v['version']}", "version": v["version"], "label": v["label"],
                 "when": v["when"], "published": v["version"] == published}
                for v in reversed(doc.get("versions", []))]

    def open(self, page_id: str, owner: str) -> dict:
        doc = self.pages.get(page_id, owner)
        return {"page": self.view(doc), "versions": self.versions(doc)}

    def enrich(self, result: dict, owner: str) -> dict:
        page = result.get("page")
        if page and page.get("id"):
            doc = self.pages.get(page["id"], owner)
            result["page"] = self.view(doc)
            result["versions"] = self.versions(doc)
        return result

    def edit(self, page_id: str, owner: str, changes: list[dict],
             expected_version: Optional[int], providers: Providers) -> dict:
        ctx = CommandContext(page_id=page_id, owner=owner, expected_version=expected_version)
        trace = Trace(f"[{', '.join(str(c.get('action')) for c in changes)}]")
        result = run_edits(changes, trace.instruction, "en", self.pages, ctx, trace,
                           providers)
        result.pop("_trace", None)
        return self.enrich(result, owner)

    def publish(self, page_id: str, owner: str, version: Optional[int] = None) -> dict:
        doc = self.pages.get(page_id, owner)
        target = doc["version"] if version is None else version
        snap = self.pages.find_version(doc, target)
        readiness = enforce(snap["sections"])
        published = self.pages.publish(page_id, owner, target)
        return {"id": page_id, "url": doc["url"], "published": True,
                "version": published["version"], "when": published["when"],
                "readiness": readiness}

    def unpublish(self, page_id: str, owner: str) -> dict:
        self.pages.unpublish(page_id, owner)
        return {"id": page_id, "published": False}

    def rename(self, page_id: str, owner: str, wanted: str) -> dict:
        url = self.pages.rename(page_id, owner, wanted)
        doc = self.pages.get(page_id, owner)
        return {"id": page_id, "url": url, "published": doc.get("published") is not None}

    def version(self, page_id: str, owner: str, version: int) -> dict:
        return self.pages.version_snapshot(page_id, owner, version)

    def restore(self, page_id: str, owner: str, version: int,
                expected_version: Optional[int] = None) -> dict:
        page = self.pages.restore_version(page_id, owner, version, expected_version)
        doc = self.pages.get(page_id, owner)
        return {
            "page": self.view(doc),
            "versions": self.versions(doc),
            "message": f"Restored version {version} as v{page.version}.",
        }

    def public(self, url: str) -> Optional[dict]:
        return self.pages.published(url)

    def attach(self, build_id: str, page_id: str, owner: str) -> dict:
        self.pages.get(page_id, owner)
        return self.builds.attach(build_id, owner, page_id)

    def list_builds(self, owner: str) -> list[dict]:
        builds = self.builds.list(owner)
        urls = self.pages.urls([b["pageId"] for b in builds if b.get("pageId")], owner)
        return [{**b, "pageUrl": urls.get(b.get("pageId"))} for b in builds]

    def open_build(self, build_id: str, owner: str) -> dict:
        build = self.builds.get(build_id, owner)
        page = None
        versions: list[dict] = []
        if build.get("page_id"):
            try:
                opened = self.open(build["page_id"], owner)
            except KeyError:
                opened = None
            if opened:
                page, versions = opened["page"], opened["versions"]
        return {
            "build": {**build_summary(build),
                      "messages": build.get("messages", []),
                      "brief": build.get("brief"),
                      "summary": build.get("summary")},
            "page": page,
            "versions": versions,
        }
