import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

from command_service import CommandStore
from schema import Page
from storage import PageStore, RevisionConflict, UrlTaken

HERO = {"type": "hero", "headline": "Welcome",
        "image": {"src": "/images/hero-section.jpg", "alt": ""},
        "button": {"label": "Go"}}
FAQ = {"type": "faq", "items": [{"question": "Q?", "answer": "A."}]}
WORKERS = 12


@pytest.fixture(scope="module")
def client():
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
                         serverSelectionTimeoutMS=1500)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        pytest.skip("no MongoDB at MONGO_URL")
    yield client
    client.close()


@pytest.fixture
def db(client):
    name = f"vlp-concurrency-{uuid.uuid4().hex[:8]}"
    yield client[name]
    client.drop_database(name)


@pytest.fixture
def store(db):
    store = PageStore(db["pages"])
    store.ensure_indexes()
    return store


def fan_out(fn, n=WORKERS):
    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(fn, range(n)))


def test_concurrent_creates_never_share_a_slug(store):
    docs = fan_out(lambda i: store.create(
        Page(name="Maria's Bakery", url="/maria-s-bakery", sections=[HERO]), f"user-{i}"))

    urls = sorted(d["url"] for d in docs)
    assert len(set(urls)) == WORKERS
    assert urls[0] == "/maria-s-bakery"
    assert store._pages.count_documents({}) == WORKERS
    assert len({d["_id"] for d in docs}) == WORKERS


def test_concurrent_edits_of_one_version_admit_exactly_one_writer(store):
    page_id = store.create(Page(name="P", url="/p", sections=[HERO]), "me")["_id"]

    def edit(i):
        try:
            return store.append_version(page_id, "me", 1, f"Edit {i}",
                                        [HERO, {**FAQ, "heading": f"By {i}"}])
        except RevisionConflict as e:
            return e

    results = fan_out(edit)
    winners = [r for r in results if isinstance(r, int)]
    assert winners == [2]
    assert all(r.current == 2 for r in results if isinstance(r, RevisionConflict))

    doc = store.get(page_id, "me")
    assert [v["version"] for v in doc["versions"]] == [1, 2]
    assert doc["sections"] == doc["versions"][1]["sections"]


def test_sequential_edits_from_racing_writers_never_duplicate_a_version(store):
    page_id = store.create(Page(name="P", url="/p", sections=[HERO]), "me")["_id"]

    def keep_editing(i):
        applied = 0
        for _ in range(20):
            current = store.get(page_id, "me")["version"]
            try:
                store.append_version(page_id, "me", current, f"w{i}", [HERO])
                applied += 1
            except RevisionConflict:
                continue
        return applied

    applied = sum(fan_out(keep_editing, 6))
    versions = [v["version"] for v in store.get(page_id, "me")["versions"]]
    assert versions == list(range(1, applied + 2))
    assert store.get(page_id, "me")["version"] == applied + 1


def test_concurrent_renames_onto_one_url_admit_exactly_one(store):
    ids = [store.create(Page(name="P", url=f"/p{i}", sections=[HERO]), "me")["_id"]
           for i in range(WORKERS)]

    def rename(i):
        try:
            return store.rename(ids[i], "me", "winner")
        except UrlTaken as e:
            return e

    results = fan_out(rename)
    assert sum(1 for r in results if r == "/winner") == 1
    assert store._pages.count_documents({"url": "/winner"}) == 1


def test_publishing_while_editing_keeps_content_and_reference_consistent(store):
    page_id = store.create(Page(name="P", url="/p", sections=[HERO]), "me")["_id"]

    def work(i):
        if i % 2:
            try:
                current = store.get(page_id, "me")["version"]
                store.append_version(page_id, "me", current, f"e{i}", [HERO, FAQ])
            except RevisionConflict:
                pass
        else:
            store.publish(page_id, "me", version=1)

    fan_out(work)
    doc = store.get(page_id, "me")
    published = store.published("/p")
    assert published["version"] == 1
    assert published["sections"] == doc["versions"][0]["sections"]
    assert doc["version"] == doc["versions"][-1]["version"]
    assert doc["sections"] == doc["versions"][-1]["sections"]


def test_concurrent_retries_with_one_idempotency_key_start_one_command(db):
    commands = CommandStore(db["commands"])
    commands.ensure_indexes()

    results = fan_out(lambda i: commands.begin("me", None, "create", key="k"))
    created = [record for record, fresh in results if fresh]
    assert len(created) == 1
    assert {record["_id"] for record, _ in results} == {created[0]["_id"]}
    assert commands.begin("you", None, "create", key="k")[1] is True
