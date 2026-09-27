import mongomock
import pytest
from bson import ObjectId

import auth
from migrations import migrate_pages
from page_service import PageService
from builds import BuildStore
from storage import PageStore

HERO = {"type": "hero", "headline": "Live headline",
        "image": {"src": "/images/hero-section.jpg", "alt": ""},
        "button": {"label": "Go"}}
DRAFT_HERO = {**HERO, "headline": "Newer draft headline"}


@pytest.fixture
def db():
    return mongomock.MongoClient()["vlp-migrate"]


def legacy(db, url, owner="user-1", publish=True, versions=None, sections=None):
    doc = {"_id": ObjectId(), "url": url, "name": "Maria's Bakery", "version": 2,
           "sections": sections or [DRAFT_HERO], "theme": None, "publish": publish,
           "owner": owner,
           "versions": versions if versions is not None else [
               {"version": 1, "label": "Initial draft", "when": "2026-01-01T00:00:00+00:00",
                "sections": [HERO], "theme": None},
               {"version": 2, "label": "Edited hero headline",
                "when": "2026-01-02T00:00:00+00:00", "sections": [DRAFT_HERO],
                "theme": None}]}
    db["pages"].insert_one(doc)
    return doc


def test_a_published_legacy_page_keeps_its_live_content_public(db):
    legacy(db, "/maria-s-bakery")
    report = migrate_pages(db)
    assert report["migrated"] == 1 and report["published"] == 1

    store = PageStore(db["pages"])
    public = store.published("/maria-s-bakery")
    assert public["version"] == 2
    assert public["sections"] == [DRAFT_HERO]

    doc = db["pages"].find_one({"url": "/maria-s-bakery"})
    assert isinstance(doc["_id"], str) and len(doc["_id"]) == 16
    assert doc["format"] == 2
    assert doc["version"] == 2
    assert [v["version"] for v in doc["versions"]] == [1, 2]
    assert all(v["name"] == "Maria's Bakery" for v in doc["versions"])
    assert db["pages"].count_documents({}) == 1


def test_an_unpublished_legacy_page_stays_private(db):
    legacy(db, "/draft-only", publish=False)
    migrate_pages(db)
    assert PageStore(db["pages"]).published("/draft-only") is None


def test_build_references_move_from_urls_to_page_ids(db):
    legacy(db, "/maria-s-bakery")
    db["builds"].insert_one({"_id": "b1", "owner": "user-1", "page_url": "/maria-s-bakery",
                             "messages": [], "title": "Maria's Bakery"})
    db["builds"].insert_one({"_id": "b2", "owner": "user-1", "page_url": None,
                             "messages": [], "title": "Empty"})

    report = migrate_pages(db)
    assert report["builds"] == 2
    page_id = db["pages"].find_one({"url": "/maria-s-bakery"})["_id"]
    linked = db["builds"].find_one({"_id": "b1"})
    assert linked["page_id"] == page_id and "page_url" not in linked
    assert db["builds"].find_one({"_id": "b2"})["page_id"] is None

    opened = PageService(PageStore(db["pages"]), BuildStore(db["builds"])).open_build(
        "b1", "user-1")
    assert opened["page"]["id"] == page_id
    assert opened["page"]["published"]["version"] == 2


def test_ownerless_pages_are_orphaned_unless_adopted(db):
    legacy(db, "/orphan", owner=None)
    report = migrate_pages(db)
    assert report["orphaned"] == 1 and report["adopted"] == 0
    store = PageStore(db["pages"])
    page_id = db["pages"].find_one({"url": "/orphan"})["_id"]
    for owner in ("user-1", "local", auth.LOCAL_USER["id"]):
        with pytest.raises(KeyError):
            store.get(page_id, owner)


def test_adopting_ownerless_pages_names_one_owner(db):
    legacy(db, "/orphan", owner=None)
    report = migrate_pages(db, adopt="local")
    assert report["adopted"] == 1
    page_id = db["pages"].find_one({"url": "/orphan"})["_id"]
    assert PageStore(db["pages"]).get(page_id, "local")["url"] == "/orphan"


def test_a_page_without_history_gets_a_migrated_version(db):
    legacy(db, "/bare", versions=[])
    migrate_pages(db)
    doc = db["pages"].find_one({"url": "/bare"})
    assert [v["label"] for v in doc["versions"]] == ["Migrated"]
    assert doc["versions"][0]["sections"] == doc["sections"]


def test_migration_is_idempotent_and_dry_run_writes_nothing(db):
    legacy(db, "/maria-s-bakery")
    dry = migrate_pages(db, dry_run=True)
    assert dry["migrated"] == 1
    assert db["pages"].find_one({"url": "/maria-s-bakery"})["publish"] is True

    migrate_pages(db)
    again = migrate_pages(db)
    assert again["migrated"] == 0
    assert db["pages"].count_documents({}) == 1
