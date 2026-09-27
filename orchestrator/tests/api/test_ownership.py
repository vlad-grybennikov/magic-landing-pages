import pytest


def test_importing_the_api_loads_no_models_or_database():
    import sys

    import app  # noqa: F401

    assert "faster_whisper" not in sys.modules
    assert "torch" not in sys.modules


def test_a_build_and_page_belong_to_their_owner(alice, bob):
    build = alice.post("/builds").json()
    page = alice.create_page()
    assert alice.put(f"/builds/{build['id']}/page",
                     json={"page_id": page["id"]}).status_code == 200

    opened = alice.get(f"/builds/{build['id']}").json()
    assert opened["page"]["id"] == page["id"]
    assert opened["page"]["published"] is None

    assert bob.get(f"/builds/{build['id']}").status_code == 404
    assert bob.get(f"/pages/{page['id']}").status_code == 404
    assert [b["id"] for b in bob.get("/builds").json()["builds"]] == []


@pytest.mark.parametrize("call", [
    lambda s, p: s.post("/edit", json={
        "page_id": p["id"], "expected_version": p["version"],
        "changes": [{"action": "editContent",
                     "args": {"section": "hero", "field": "title", "value": "Mine now"}}]}),
    lambda s, p: s.post("/publish", json={"page_id": p["id"]}),
    lambda s, p: s.post("/unpublish", json={"page_id": p["id"]}),
    lambda s, p: s.post("/pages/url", json={"page_id": p["id"], "wanted": "stolen"}),
    lambda s, p: s.get(f"/versions/1?page_id={p['id']}"),
    lambda s, p: s.post("/versions/restore", json={"page_id": p["id"], "version": 1}),
    lambda s, p: s.get(f"/pages/{p['id']}"),
    lambda s, p: s.post("/command/text", json={
        "text": "Change the hero headline to Baked Before Sunrise", "page_id": p["id"]}),
], ids=["edit", "publish", "unpublish", "rename", "version", "restore", "open", "command"])
def test_a_second_user_cannot_touch_another_s_page(alice, bob, services, call):
    page = alice.create_page()
    before = services.pages.get(page["id"], alice.user["id"])

    response = call(bob, page)
    assert response.status_code in (404, 422), response.text
    if response.status_code == 422:
        assert "find" in response.json()["error"]["message"]

    after = services.pages.get(page["id"], alice.user["id"])
    assert after["version"] == before["version"]
    assert after["url"] == before["url"]
    assert after["published"] is None
    assert after["sections"] == before["sections"]


def test_a_build_cannot_be_linked_to_someone_else_s_page(alice, bob):
    page = alice.create_page()
    build = bob.post("/builds").json()

    response = bob.put(f"/builds/{build['id']}/page", json={"page_id": page["id"]})
    assert response.status_code == 404
    assert bob.get(f"/builds/{build['id']}").json()["page"] is None


def test_a_build_cannot_be_linked_through_a_patch(alice):
    page = alice.create_page()
    build = alice.post("/builds").json()
    alice.patch(f"/builds/{build['id']}", json={"title": "x", "page_id": page["id"]})
    assert alice.get(f"/builds/{build['id']}").json()["page"] is None


def test_a_page_someone_else_deleted_from_a_build_is_not_reachable_by_url(alice, bob, client):
    page = alice.create_page()
    assert client.get(f"/public?url={page['url']}").status_code == 404
    alice.post("/publish", json={"page_id": page["id"]})
    assert client.get(f"/public?url={page['url']}").status_code == 200
    assert bob.post("/unpublish", json={"page_id": page["id"]}).status_code == 404
    assert client.get(f"/public?url={page['url']}").status_code == 200


def test_the_public_interface_only_returns_published_content(alice, client):
    page = alice.create_page()
    assert client.get(f"/public?url={page['url']}").status_code == 404

    alice.post("/publish", json={"page_id": page["id"]})
    public = client.get(f"/public?url={page['url']}").json()
    assert public["version"] == 1
    assert "readiness" not in public
    assert "owner" not in public

    alice.post("/edit", json={"page_id": page["id"], "expected_version": 1, "changes": [
        {"action": "editContent",
         "args": {"section": "hero", "field": "title", "value": "Unpublished draft"}}]})
    public = client.get(f"/public?url={page['url']}").json()
    assert public["version"] == 1
    assert all(s.get("headline") != "Unpublished draft" for s in public["sections"])


def test_requests_without_a_token_are_refused_when_auth_is_on(client):
    assert client.get("/builds").status_code == 401
    assert client.get("/auth/config").json() == {"enabled": True, "mode": "development"}


def test_a_refresh_token_cannot_be_used_as_an_access_token(client):
    signed = client.post("/auth/google", json={"idToken": "alice"}).json()
    response = client.get("/auth/me",
                          headers={"Authorization": f"Bearer {signed['refreshToken']}"})
    assert response.status_code == 401
    refreshed = client.post("/auth/refresh", json={"refreshToken": signed["refreshToken"]})
    assert refreshed.status_code == 200
    me = client.get("/auth/me",
                    headers={"Authorization": f"Bearer {refreshed.json()['accessToken']}"})
    assert me.json()["email"] == "alice@example.com"


def test_the_build_list_shows_the_linked_page_url_but_references_its_id(alice, bob):
    build = alice.post("/builds").json()
    page = alice.create_page()
    alice.put(f"/builds/{build['id']}/page", json={"page_id": page["id"]})
    alice.post("/pages/url", json={"page_id": page["id"], "wanted": "renamed"})

    listed = alice.get("/builds").json()["builds"][0]
    assert listed["pageId"] == page["id"]
    assert listed["pageUrl"] == "/renamed"
    assert bob.get("/builds").json()["builds"] == []
