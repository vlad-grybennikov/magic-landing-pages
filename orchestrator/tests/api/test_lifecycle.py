def edit(session, page, value, expected=None):
    return session.post("/edit", json={
        "page_id": page["id"],
        "expected_version": page["version"] if expected is None else expected,
        "changes": [{"action": "editContent",
                     "args": {"section": "hero", "field": "title", "value": value}}]})


def headline(page_or_public):
    return next(s["headline"] for s in page_or_public["sections"] if s["type"] == "hero")


def test_create_edit_save_publish_reopen_restore(alice, client):
    build = alice.post("/builds").json()
    page = alice.create_page()
    alice.put(f"/builds/{build['id']}/page", json={"page_id": page["id"]})

    edited = edit(alice, page, "Baked before sunrise").json()["page"]
    assert edited["version"] == 2
    assert edited["published"] is None

    published = alice.post("/publish", json={"page_id": page["id"]}).json()
    assert published["version"] == 2
    assert headline(client.get(f"/public?url={page['url']}").json()) == "Baked before sunrise"

    reopened = alice.get(f"/builds/{build['id']}").json()
    assert reopened["page"]["version"] == 2
    assert reopened["page"]["published"] == {"version": 2, "when": published["when"]}
    assert [v["published"] for v in reopened["versions"]] == [True, False]

    restored = alice.post("/versions/restore",
                          json={"page_id": page["id"], "version": 1}).json()
    assert restored["page"]["version"] == 3
    assert restored["page"]["published"]["version"] == 2
    assert headline(restored["page"]) != "Baked before sunrise"
    assert headline(client.get(f"/public?url={page['url']}").json()) == "Baked before sunrise"

    reopened = alice.get(f"/builds/{build['id']}").json()
    assert reopened["page"]["version"] == 3
    assert reopened["page"]["published"]["version"] == 2
    assert [v["id"] for v in reopened["versions"]] == ["v3", "v2", "v1"]


def test_publishing_a_specific_version(alice, client):
    page = alice.create_page()
    edit(alice, page, "Second")
    edit(alice, {**page, "version": 2}, "Third")

    assert alice.post("/publish", json={"page_id": page["id"], "version": 2}).json()["version"] == 2
    assert headline(client.get(f"/public?url={page['url']}").json()) == "Second"
    assert alice.get(f"/pages/{page['id']}").json()["page"]["version"] == 3


def test_a_stale_edit_is_rejected_with_the_current_version(alice):
    page = alice.create_page()
    assert edit(alice, page, "First").status_code == 200

    stale = edit(alice, page, "Second", expected=1)
    assert stale.status_code == 409
    body = stale.json()["error"]
    assert (body["stage"], body["expected"], body["current"]) == ("conflict", 1, 2)

    current = alice.get(f"/pages/{page['id']}").json()["page"]
    assert current["version"] == 2
    assert headline(current) == "First"


def test_a_stale_restore_is_rejected(alice):
    page = alice.create_page()
    edit(alice, page, "First")
    response = alice.post("/versions/restore", json={
        "page_id": page["id"], "version": 1, "expected_version": 1})
    assert response.status_code == 409


def test_an_edit_without_an_expected_version_applies_to_the_current_draft(alice):
    page = alice.create_page()
    edit(alice, page, "First")
    response = alice.post("/edit", json={"page_id": page["id"], "changes": [
        {"action": "editContent",
         "args": {"section": "hero", "field": "title", "value": "Second"}}]})
    assert response.status_code == 200
    assert response.json()["page"]["version"] == 3


def test_renaming_keeps_the_build_link_and_moves_the_public_url(alice, client):
    build = alice.post("/builds").json()
    page = alice.create_page()
    alice.put(f"/builds/{build['id']}/page", json={"page_id": page["id"]})
    alice.post("/publish", json={"page_id": page["id"]})

    moved = alice.post("/pages/url", json={"page_id": page["id"], "wanted": "Summer"}).json()
    assert moved == {"id": page["id"], "url": "/summer", "published": True}
    assert client.get("/public?url=/summer").status_code == 200
    assert client.get(f"/public?url={page['url']}").status_code == 404

    reopened = alice.get(f"/builds/{build['id']}").json()
    assert reopened["page"]["id"] == page["id"]
    assert reopened["page"]["url"] == "/summer"


def test_renaming_onto_another_user_s_url_is_refused(alice, bob):
    mine = alice.create_page("Create a landing page for Apex Plumbing with a hero")
    theirs = bob.create_page("Create a landing page for Maria's Bakery with a hero")
    response = alice.post("/pages/url", json={"page_id": mine["id"], "wanted": theirs["url"]})
    assert response.status_code == 409
    assert alice.get(f"/pages/{mine['id']}").json()["page"]["url"] == mine["url"]


def test_two_users_creating_the_same_business_get_distinct_urls(alice, bob):
    first = alice.create_page()
    second = bob.create_page()
    assert first["url"] == "/maria-s-bakery"
    assert second["url"] == "/maria-s-bakery-2"


def test_the_page_view_reports_readiness(alice):
    page = alice.create_page()
    assert page["readiness"] == {"ready": True, "blocking": [], "warnings": []}
    assert all(s.get("provenance") == "generated"
               for s in page["sections"] if s["type"] not in ("header", "footer"))


def test_a_placeholder_section_blocks_publishing_until_edited(alice, services):
    page = alice.create_page()
    doc = services.pages.get(page["id"], alice.user["id"])
    sections = [{**s, "provenance": "placeholder"} if s["type"] == "faq" else s
                for s in doc["sections"]]
    services.pages.append_version(page["id"], alice.user["id"], 1, "Placeholder", sections)

    refused = alice.post("/publish", json={"page_id": page["id"]})
    assert refused.status_code == 422
    error = refused.json()["error"]
    assert error["stage"] == "readiness"
    assert error["readiness"]["blocking"][0]["section"] == "faq"
    assert services.pages.get(page["id"], alice.user["id"])["published"] is None

    fixed = alice.post("/edit", json={"page_id": page["id"], "expected_version": 2, "changes": [
        {"action": "editContent",
         "args": {"section": "faq", "field": "title", "value": "Real questions"}}]}).json()
    assert fixed["page"]["readiness"]["ready"]
    assert next(s for s in fixed["page"]["sections"]
                if s["type"] == "faq")["provenance"] == "edited"
    assert alice.post("/publish", json={"page_id": page["id"]}).status_code == 200


def test_generated_claims_block_publishing_until_they_are_approved(alice):
    page = alice.create_page(
        "Create a landing page for Maria's Bakery with a hero and testimonials")
    warnings = page["readiness"]["warnings"]
    assert not page["readiness"]["ready"]
    assert [w["section"] for w in warnings] == ["testimonials"]
    assert warnings[0]["reason"] == "Sample reviews, not real ones"

    refused = alice.post("/publish", json={"page_id": page["id"]})
    assert refused.status_code == 422
    error = refused.json()["error"]
    assert error["stage"] == "readiness"
    assert error["message"] == "Approve the flagged sections before publishing."
    assert [w["section"] for w in error["readiness"]["warnings"]] == ["testimonials"]
    assert error["readiness"]["blocking"] == []

    alice.post("/edit", json={"page_id": page["id"], "expected_version": 1, "changes": [
        {"action": "approveSection", "args": {"section": "testimonials"}}]})
    assert alice.post("/publish", json={"page_id": page["id"]}).status_code == 200


def test_rearranging_generated_claims_does_not_release_the_hold(alice):
    page = alice.create_page(
        "Create a landing page for Maria's Bakery with a hero and testimonials")
    version = page["version"]

    for change in ({"action": "moveItem",
                    "args": {"section": "testimonials", "path": "items.0",
                             "position": "down"}},
                   {"action": "removeItem",
                    "args": {"section": "testimonials", "path": "items.1"}},
                   {"action": "addItem", "args": {"section": "testimonials"}},
                   {"action": "editContent",
                    "args": {"section": "testimonials", "field": "title",
                             "value": "What our customers say"}}):
        edited = alice.post("/edit", json={"page_id": page["id"],
                                           "expected_version": version,
                                           "changes": [change]})
        assert edited.status_code == 200, edited.text
        version = edited.json()["page"]["version"]
        readiness = edited.json()["page"]["readiness"]
        assert not readiness["ready"], change["action"]
        assert [w["section"] for w in readiness["warnings"]] == ["testimonials"]
        assert alice.post("/publish", json={"page_id": page["id"]}).status_code == 422


def test_swapping_a_member_photo_does_not_release_the_hold(alice):
    page = alice.create_page(
        "Create a landing page for Maria's Bakery with a hero and a team")
    assert [w["section"] for w in page["readiness"]["warnings"]] == ["team"]

    edited = alice.post("/edit", json={"page_id": page["id"], "expected_version": 1,
                                       "changes": [
        {"action": "replaceImage",
         "args": {"section": "team", "path": "members.0.photo", "query": "baker"}}]})
    assert edited.status_code == 200, edited.text
    assert [w["section"] for w in edited.json()["page"]["readiness"]["warnings"]] == ["team"]
    assert alice.post("/publish", json={"page_id": page["id"]}).status_code == 422


def test_rewriting_a_claim_itself_releases_the_hold(alice):
    page = alice.create_page(
        "Create a landing page for Maria's Bakery with a hero and testimonials")
    edited = alice.post("/edit", json={"page_id": page["id"], "expected_version": 1,
                                       "changes": [
        {"action": "editContent",
         "args": {"section": "testimonials", "path": "items.0.content",
                  "value": "Best sourdough in town -- Dana, a real customer"}}]}).json()

    assert edited["page"]["readiness"] == {"ready": True, "blocking": [], "warnings": []}
    assert next(s for s in edited["page"]["sections"]
                if s["type"] == "testimonials")["provenance"] == "edited"
    assert alice.post("/publish", json={"page_id": page["id"]}).status_code == 200


def test_swapping_a_photo_leaves_placeholder_content_blocking(alice, services):
    page = alice.create_page()
    doc = services.pages.get(page["id"], alice.user["id"])
    sections = [{**s, "provenance": "placeholder"} if s["type"] == "hero" else s
                for s in doc["sections"]]
    services.pages.append_version(page["id"], alice.user["id"], 1, "Placeholder", sections)

    edited = alice.post("/edit", json={"page_id": page["id"], "expected_version": 2, "changes": [
        {"action": "replaceImage", "args": {"section": "hero", "query": "bakery"}}]})
    assert edited.status_code == 200, edited.text
    assert next(s for s in edited.json()["page"]["sections"]
                if s["type"] == "hero")["provenance"] == "placeholder"
    refused = alice.post("/publish", json={"page_id": page["id"]})
    assert refused.status_code == 422
    assert refused.json()["error"]["readiness"]["blocking"][0]["section"] == "hero"


def test_approving_a_generated_section_clears_its_warning(alice):
    page = alice.create_page(
        "Create a landing page for Maria's Bakery with a hero and testimonials")
    assert page["readiness"]["warnings"]

    approved = alice.post("/edit", json={"page_id": page["id"], "expected_version": 1, "changes": [
        {"action": "approveSection", "args": {"section": "testimonials"}}]}).json()
    assert approved["page"]["readiness"] == {"ready": True, "blocking": [], "warnings": []}
    assert approved["versions"][0]["label"] == "Approved testimonials"
    assert next(s for s in approved["page"]["sections"]
                if s["type"] == "testimonials")["reviewed"] is True
    assert next(s for s in approved["page"]["sections"]
                if s["type"] == "testimonials")["provenance"] == "generated"

    again = alice.post("/edit", json={"page_id": page["id"], "expected_version": 2, "changes": [
        {"action": "approveSection", "args": {"section": "testimonials"}}]})
    assert again.status_code == 422
    assert "nothing to approve" in again.json()["error"]["message"]


def test_a_placeholder_cannot_be_approved_away(alice, services):
    page = alice.create_page()
    doc = services.pages.get(page["id"], alice.user["id"])
    sections = [{**s, "provenance": "placeholder"} if s["type"] == "faq" else s
                for s in doc["sections"]]
    services.pages.append_version(page["id"], alice.user["id"], 1, "Placeholder", sections)

    refused = alice.post("/edit", json={"page_id": page["id"], "expected_version": 2, "changes": [
        {"action": "approveSection", "args": {"section": "faq"}}]})
    assert refused.status_code == 422
    assert "placeholder" in refused.json()["error"]["message"]
    assert alice.post("/publish", json={"page_id": page["id"]}).status_code == 422


def test_publishing_an_older_version_applies_the_same_policy(alice, services):
    page = alice.create_page()
    doc = services.pages.get(page["id"], alice.user["id"])
    placeholder = [{**s, "provenance": "placeholder"} for s in doc["sections"]]
    services.pages.append_version(page["id"], alice.user["id"], 1, "Bad", placeholder)
    services.pages.append_version(page["id"], alice.user["id"], 2, "Good", doc["sections"])

    assert alice.post("/publish", json={"page_id": page["id"], "version": 2}).status_code == 422
    assert alice.post("/publish", json={"page_id": page["id"], "version": 3}).status_code == 200
