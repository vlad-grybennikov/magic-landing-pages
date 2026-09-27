from tatl import GoalState, Projection, evaluate_outcome, pass_hat_k

PROJECTION = Projection()
HERO = {"type": "hero", "headline": "Welcome"}
FAQ = {"type": "faq", "items": []}


def snapshot(rows):
    return {"tables": {"pages": rows}}


def page_row(url, name="Maria's Bakery", publish=False, sections=(HERO,), versions=()):
    return {"id": url, "url": url, "name": name, "version": 1,
            "publish": publish, "sections": list(sections), "versions": list(versions)}


def trace(initial, final):
    return {"steps": [], "initial_snapshot": initial, "final_snapshot": final}


def test_projection_drops_copy_and_derives_structure():
    projected = PROJECTION.apply(snapshot([page_row("/a", sections=(HERO, FAQ))]))
    row = projected["pages"]["/a"]
    assert "sections" not in row and "versions" not in row
    assert row["section_types"] == "hero,faq"
    assert row["n_sections"] == 2


def test_created_page_matches_goal():
    goal = GoalState(created={"pages": {"/maria-s-bakery": {
        "name": "Maria's Bakery", "publish": False,
        "section_types": "hero,faq", "n_sections": 2}}})
    result = evaluate_outcome(
        trace(snapshot([]), snapshot([page_row("/maria-s-bakery", sections=(HERO, FAQ))])),
        goal, PROJECTION)
    assert result.passed, result.diffs


def test_wrong_section_structure_fails():
    goal = GoalState(created={"pages": {"/maria-s-bakery": {
        "section_types": "hero,faq", "n_sections": 2}}})
    result = evaluate_outcome(
        trace(snapshot([]), snapshot([page_row("/maria-s-bakery", sections=(HERO,))])),
        goal, PROJECTION)
    assert not result.passed
    assert any("section_types" in d for d in result.diffs)


def test_empty_goal_requires_untouched_store():
    before = snapshot([page_row("/existing")])
    assert evaluate_outcome(trace(before, before), GoalState(), PROJECTION).passed

    after = snapshot([page_row("/existing"), page_row("/new", name="New")])
    result = evaluate_outcome(trace(before, after), GoalState(), PROJECTION)
    assert not result.passed
    assert any("unexpected new row" in d for d in result.diffs)


def test_collision_must_not_overwrite_existing_page():
    before = snapshot([page_row("/maria-s-bakery", publish=True, sections=(HERO,))])
    goal = GoalState(
        expected={"pages": {"/maria-s-bakery": {"publish": True, "n_sections": 1}}},
        created={"pages": {"/maria-s-bakery-2": {"publish": False}}},
    )

    good = snapshot([page_row("/maria-s-bakery", publish=True, sections=(HERO,)),
                     page_row("/maria-s-bakery-2", sections=(HERO, FAQ))])
    assert evaluate_outcome(trace(before, good), goal, PROJECTION).passed

    clobbered = snapshot([page_row("/maria-s-bakery", publish=False, sections=(HERO, FAQ))])
    result = evaluate_outcome(trace(before, clobbered), goal, PROJECTION)
    assert not result.passed


def test_pass_hat_k():
    assert pass_hat_k(3, 3, 3) == 1.0
    assert pass_hat_k(3, 2, 3) == 0.0
    assert pass_hat_k(4, 2, 2) == 1 / 6
    assert pass_hat_k(3, 2, 1) == 2 / 3


def test_goal_values_can_be_matchers_instead_of_literals():
    from tatl import matches

    assert matches({"$changed": True}, "new", initial="old")
    assert not matches({"$changed": True}, "same", initial="same")
    assert matches({"$changed": False}, "same", initial="same")
    assert matches({"$contains": "star"}, "benefits:/icons/star.svg|")
    assert matches({"$contains": ["hero", "faq"]}, ["hero", "benefits", "faq"])
    assert not matches({"$contains": "team"}, ["hero", "faq"])
    assert matches({"$between": [6, 9]}, 7)
    assert matches({"$between": [2, 3]}, ["hero", "faq"])
    assert not matches({"$between": [6, 9]}, 5)
    assert matches({"$startswith": "header,hero", "$endswith": "faq,footer"},
                   "header,hero,about,faq,footer")
    assert matches({"$endswith": "faq"}, ["hero", "faq"])
    assert not matches({"$endswith": ["hero", "faq"]}, ["faq", "hero"])
    assert matches({"plain": "dict"}, {"plain": "dict"})
    assert not matches("literal", "other")


def test_changed_rows_accept_matchers_against_the_initial_state():
    before = snapshot([page_row("/a", sections=({"type": "hero", "headline": "Old"},))])
    after = snapshot([page_row("/a", sections=({"type": "hero", "headline": "New"},))])
    projection = Projection(drop_fields={"pages": ["versions", "theme"]})
    goal = GoalState(expected={"pages": {"/a": {"sections": {"$changed": True}}}})
    assert evaluate_outcome(trace(before, after), goal, projection).passed
    result = evaluate_outcome(trace(before, before), goal, projection)
    assert not result.passed and any("$changed" in d for d in result.diffs)

    goal = GoalState(created={"pages": {"/b": {
        "section_types": {"$startswith": "hero", "$contains": ["faq"]},
        "n_sections": {"$between": [2, 4]}}}})
    created = snapshot([page_row("/b", sections=(HERO, FAQ))])
    assert evaluate_outcome(trace(snapshot([]), created), goal, PROJECTION).passed


def test_free_text_slots_tolerate_paraphrase_but_short_slots_stay_strict():
    from tatl.evaluators import _slot_match

    assert _slot_match("collect enquiries", "collects enquiries")
    assert _slot_match("take online table reservations", "reserve a table online")
    assert _slot_match("gather quote requests", "collect quote requests")
    assert _slot_match("book appointments", "book an appointment")
    assert not _slot_match("generate enquiries", "take online orders")
    assert _slot_match("faqs", "faq")
    assert not _slot_match("items.0", "items.1")
    assert not _slot_match("items.order online", "items.0")
    assert not _slot_match("after items.we bake", "down")
    assert _slot_match("items.1", {"$any": ["items.0", "items.1"]})
    assert not _slot_match(None, "faq")
