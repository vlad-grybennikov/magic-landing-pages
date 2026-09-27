from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from storage import FORMAT, new_page_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def migrate_pages(db, adopt: Optional[str] = None, dry_run: bool = False) -> dict:
    pages = db["pages"]
    builds = db["builds"]
    report = {"migrated": 0, "adopted": 0, "orphaned": 0, "published": 0,
              "builds": 0, "skipped": 0, "urls": []}

    by_url: dict[str, str] = {}
    for doc in list(pages.find({"$or": [{"format": {"$exists": False}},
                                        {"format": {"$lt": FORMAT}}]})):
        url = doc.get("url")
        if not url:
            report["skipped"] += 1
            continue
        owner = doc.get("owner")
        if owner is None:
            if adopt:
                owner = adopt
                report["adopted"] += 1
            else:
                report["orphaned"] += 1

        now = _now()
        versions = list(doc.get("versions") or [])
        version = doc.get("version") or (versions[-1]["version"] if versions else 1)
        sections = doc.get("sections") or []
        theme = doc.get("theme")
        name = doc.get("name") or ""
        if not versions:
            versions = [{"version": version, "label": "Migrated", "when": now,
                         "sections": sections, "theme": theme, "name": name}]
        for snap in versions:
            snap.setdefault("name", name)
            snap.setdefault("theme", theme)

        published = None
        if doc.get("publish"):
            published = {"version": version, "name": name, "sections": sections,
                         "theme": theme, "when": now}
            report["published"] += 1

        page_id = doc["_id"] if isinstance(doc.get("_id"), str) else new_page_id()
        migrated = {
            "_id": page_id,
            "format": FORMAT,
            "owner": owner,
            "url": url,
            "name": name,
            "version": version,
            "sections": sections,
            "theme": theme,
            "versions": versions,
            "published": published,
            "created": doc.get("created") or now,
            "updated": now,
        }
        by_url[url] = page_id
        report["migrated"] += 1
        report["urls"].append(url)
        if dry_run:
            continue
        if page_id == doc["_id"]:
            pages.replace_one({"_id": doc["_id"]}, migrated)
        else:
            pages.delete_one({"_id": doc["_id"]})
            pages.insert_one(migrated)

    for build in list(builds.find({"page_url": {"$exists": True}})):
        page_id = by_url.get(build.get("page_url"))
        if page_id is None and build.get("page_url"):
            found = pages.find_one({"url": build["page_url"]}, {"_id": 1})
            page_id = found["_id"] if found else None
        report["builds"] += 1
        if dry_run:
            continue
        builds.update_one({"_id": build["_id"]},
                          {"$set": {"page_id": page_id}, "$unset": {"page_url": ""}})

    if not dry_run:
        pages.create_index("url", unique=True)
    return report
