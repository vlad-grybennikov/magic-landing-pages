from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

EDITABLE = ("title", "messages", "brief", "summary")


class BuildNotFound(KeyError):
    pass


class BuildStore:
    def __init__(self, collection):
        self._builds = collection

    def ensure_indexes(self) -> None:
        self._builds.create_index([("owner", 1), ("updated", -1)])

    def create(self, owner: str, title: str = "New page") -> dict:
        now = datetime.now(timezone.utc)
        build = {
            "_id": uuid.uuid4().hex[:16],
            "owner": owner,
            "title": title,
            "page_id": None,
            "messages": [],
            "brief": None,
            "summary": None,
            "created": now,
            "updated": now,
        }
        self._builds.insert_one(build)
        return summary(build)

    def list(self, owner: str, limit: int = 50) -> list[dict]:
        rows = self._builds.find({"owner": owner}).sort("updated", -1).limit(limit)
        return [summary(row) for row in rows]

    def get(self, build_id: str, owner: str) -> dict:
        build = self._builds.find_one({"_id": build_id, "owner": owner})
        if build is None:
            raise BuildNotFound(build_id)
        return build

    def update(self, build_id: str, owner: str, changes: dict) -> dict:
        allowed = {k: v for k, v in changes.items() if k in EDITABLE and v is not None}
        allowed["updated"] = datetime.now(timezone.utc)

        result = self._builds.update_one(
            {"_id": build_id, "owner": owner}, {"$set": allowed})
        if result.matched_count == 0:
            raise BuildNotFound(build_id)
        return summary(self.get(build_id, owner))

    def attach(self, build_id: str, owner: str, page_id: str) -> dict:
        result = self._builds.update_one(
            {"_id": build_id, "owner": owner},
            {"$set": {"page_id": page_id, "updated": datetime.now(timezone.utc)}})
        if result.matched_count == 0:
            raise BuildNotFound(build_id)
        return summary(self.get(build_id, owner))

    def delete(self, build_id: str, owner: str) -> None:
        if self._builds.delete_one({"_id": build_id, "owner": owner}).deleted_count == 0:
            raise BuildNotFound(build_id)


def summary(build: dict) -> dict:
    return {
        "id": build["_id"],
        "title": build.get("title") or "New page",
        "pageId": build.get("page_id"),
        "updated": _iso(build.get("updated")),
        "turns": len(build.get("messages") or []),
    }


def _iso(when) -> Optional[str]:
    return when.isoformat(timespec="seconds") if isinstance(when, datetime) else when
