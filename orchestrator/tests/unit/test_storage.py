import mongomock
import pytest
from pydantic import ValidationError

from pipeline import run_create_page
from schema import Page
from storage import (
    PageNotFound,
    PageStore,
    RevisionConflict,
    UrlTaken,
    VersionNotFound,
)

HERO = {
    "type": "hero",
    "headline": "Welcome",
    "image": {"src": "/images/hero-section.jpg", "alt": ""},
    "button": {"label": "Go"},
}
FAQ = {"type": "faq", "items": [{"question": "Q?", "answer": "A."}]}
ME = "user-1"
THEM = "user-2"


@pytest.fixture
def store():
    store = PageStore(mongomock.MongoClient()["vlp-test"]["pages"])
    store.ensure_indexes()
    return store


def make_page(url="/test-page", sections=None):
    return Page(version=1, name="Test Page", url=url, sections=sections or [HERO])


def create(store, url="/test-page", sections=None, owner=ME) -> str:
    return store.create(make_page(url, sections), owner)["_id"]


def test_a_new_page_has_an_id_a_first_version_and_no_public_copy(store):
    doc = store.create(make_page(), ME)
    assert len(doc["_id"]) == 16
    assert doc["owner"] == ME
    assert doc["version"] == 1
    assert [v["label"] for v in doc["versions"]] == ["Initial draft"]
    assert doc["published"] is None
    assert store.published("/test-page") is None


def test_colliding_slugs_are_suffixed_on_insert(store):
    first = store.create(make_page("/maria"), ME)
    second = store.create(make_page("/maria"), ME)
    third = store.create(make_page("/maria"), THEM)
    assert (first["url"], second["url"], third["url"]) == ("/maria", "/maria-2", "/maria-3")


def test_pages_are_only_visible_to_their_owner(store):
    page_id = create(store)
    assert store.get(page_id, ME)["url"] == "/test-page"
    with pytest.raises(PageNotFound):
        store.get(page_id, THEM)
    with pytest.raises(PageNotFound):
        store.get(page_id, None)


def test_every_private_operation_is_owner_scoped(store):
    page_id = create(store)
    with pytest.raises(PageNotFound):
        store.append_version(page_id, THEM, 1, "Hijack", [HERO, FAQ])
    with pytest.raises(PageNotFound):
        store.rename(page_id, THEM, "stolen")
    with pytest.raises(PageNotFound):
        store.version_snapshot(page_id, THEM, 1)
    with pytest.raises(PageNotFound):
        store.restore_version(page_id, THEM, 1)
    with pytest.raises(PageNotFound):
        store.publish(page_id, THEM)
    with pytest.raises(PageNotFound):
        store.unpublish(page_id, THEM)
    assert store.get(page_id, ME)["version"] == 1


def test_an_edit_advances_only_the_draft(store):
    page_id = create(store)
    store.publish(page_id, ME)
    assert store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ]) == 2

    doc = store.get(page_id, ME)
    assert len(doc["sections"]) == 2
    assert doc["published"]["version"] == 1
    assert len(store.published("/test-page")["sections"]) == 1


def test_publishing_selects_exactly_one_version(store):
    page_id = create(store)
    store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ])
    store.append_version(page_id, ME, 2, "Removed FAQ", [HERO])

    published = store.publish(page_id, ME, version=2)
    assert published["version"] == 2
    public = store.published("/test-page")
    assert [s["type"] for s in public["sections"]] == ["hero", "faq"]
    assert store.get(page_id, ME)["version"] == 3


def test_publishing_defaults_to_the_current_draft(store):
    page_id = create(store)
    store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ])
    assert store.publish(page_id, ME)["version"] == 2


def test_publish_rejects_an_unknown_version(store):
    page_id = create(store)
    with pytest.raises(VersionNotFound):
        store.publish(page_id, ME, version=9)


def test_publish_rejects_invalid_content(store):
    page_id = create(store)
    store._pages.update_one({"_id": page_id}, {"$set": {"versions.0.sections": []}})
    with pytest.raises(ValidationError):
        store.publish(page_id, ME)
    assert store.get(page_id, ME)["published"] is None


def test_unpublishing_takes_the_page_down(store):
    page_id = create(store)
    store.publish(page_id, ME)
    assert store.published("/test-page") is not None
    store.unpublish(page_id, ME)
    assert store.published("/test-page") is None


def test_a_stale_write_is_rejected(store):
    page_id = create(store)
    store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ])
    with pytest.raises(RevisionConflict) as exc:
        store.append_version(page_id, ME, 1, "Stale", [HERO])
    assert (exc.value.expected, exc.value.current) == (1, 2)
    assert [v["version"] for v in store.get(page_id, ME)["versions"]] == [1, 2]


def test_versions_append_and_restore(store):
    page_id = create(store)
    assert store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ]) == 2

    page = store.restore_version(page_id, ME, 1)
    assert page.version == 3
    assert page.id == page_id
    assert len(page.sections) == 1

    doc = store.get(page_id, ME)
    assert [v["version"] for v in doc["versions"]] == [1, 2, 3]
    assert doc["versions"][2]["label"] == "Restored v1"
    assert len(doc["sections"]) == 1


def test_restoring_leaves_the_published_copy_alone(store):
    page_id = create(store)
    store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ])
    store.publish(page_id, ME)

    store.restore_version(page_id, ME, 1)
    doc = store.get(page_id, ME)
    assert doc["version"] == 3
    assert doc["published"]["version"] == 2
    assert len(store.published("/test-page")["sections"]) == 2


def test_restoring_against_a_stale_version_is_refused(store):
    page_id = create(store)
    store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ])
    with pytest.raises(RevisionConflict):
        store.restore_version(page_id, ME, 1, expected_version=1)


def test_looking_at_a_version_writes_nothing(store):
    page_id = create(store)
    store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ])

    snap = store.version_snapshot(page_id, ME, 1)
    assert snap["label"] == "Initial draft"
    assert len(snap["sections"]) == 1
    assert snap["name"] == "Test Page"

    doc = store.get(page_id, ME)
    assert [v["version"] for v in doc["versions"]] == [1, 2]
    assert len(doc["sections"]) == 2


def test_looking_at_an_unknown_version(store):
    page_id = create(store)
    with pytest.raises(VersionNotFound):
        store.version_snapshot(page_id, ME, 9)


def test_restore_unknown_version(store):
    page_id = create(store)
    with pytest.raises(VersionNotFound):
        store.restore_version(page_id, ME, 9)


def test_snapshot_shape(store):
    create(store)
    snap = store.snapshot()
    assert list(snap["tables"].keys()) == ["pages"]
    row = snap["tables"]["pages"][0]
    assert row["id"] == "/test-page"
    assert row["owner"] == ME
    assert row["publish"] is False
    assert row["published_version"] is None
    assert "version" not in row


def test_pipeline_persists_draft_and_suffixes_collisions(store):
    cmd = "Create a landing page for Maria's Bakery with a hero and an FAQ"
    first = run_create_page(cmd, store=store)
    second = run_create_page(cmd, store=store)

    assert first["page"]["url"] == "/maria-s-bakery"
    assert second["page"]["url"] == "/maria-s-bakery-2"
    assert first["page"]["id"] != second["page"]["id"]

    doc = store.get(first["page"]["id"], None)
    assert doc["published"] is None
    assert [v["label"] for v in doc["versions"]] == ["Initial draft"]

    tools = [s["call"]["tool"] for s in first["_trace"]["steps"]]
    assert tools[-1] == "save_draft"
    assert first["_trace"]["steps"][-1]["call"]["args"]["page_id"] == first["page"]["id"]


def test_a_page_moves_to_a_new_url_with_its_history_and_identity(store):
    page_id = create(store, "/old")
    store.append_version(page_id, ME, 1, "Added FAQ", [HERO, FAQ])

    assert store.rename(page_id, ME, "Summer Offer") == "/summer-offer"
    moved = store.get(page_id, ME)
    assert moved["url"] == "/summer-offer"
    assert [v["label"] for v in moved["versions"]] == ["Initial draft", "Added FAQ"]


def test_renaming_moves_the_public_copy_too(store):
    page_id = create(store, "/old")
    store.publish(page_id, ME)
    store.rename(page_id, ME, "new")
    assert store.published("/old") is None
    assert store.published("/new")["version"] == 1


def test_renaming_onto_a_taken_url_is_refused(store):
    one = create(store, "/one")
    create(store, "/two", owner=THEM)

    with pytest.raises(UrlTaken):
        store.rename(one, ME, "/two")
    assert store.get(one, ME)["url"] == "/one"


def test_renaming_to_the_same_url_is_a_no_op(store):
    page_id = create(store, "/same")
    assert store.rename(page_id, ME, "same") == "/same"
