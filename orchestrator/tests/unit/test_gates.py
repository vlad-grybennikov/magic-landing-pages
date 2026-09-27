import pytest

import providers
from pipeline import CommandUnclear, IntentInvalid, SchemaInvalid, run_create_page

CREATE_CMD = "Create a landing page for Maria's Bakery with a hero and an FAQ"


def composed(page):
    return [s["type"] for s in page["sections"]
            if s["type"] not in ("header", "footer")]


def by_type(page, kind):
    return next(s for s in page["sections"] if s["type"] == kind)


def test_gate0_rejects_short_transcript():
    with pytest.raises(CommandUnclear) as exc:
        run_create_page("hi")
    assert exc.value.stage == "command"


def test_gate0_rejects_whisper_hallucination():
    with pytest.raises(CommandUnclear):
        run_create_page("Thank you.")


def test_gate1_rejects_edit_intent():
    with pytest.raises(IntentInvalid) as exc:
        run_create_page("Please edit the headline.")
    assert exc.value.stage == "intent"


def test_gate2_rejects_empty_schema():
    with pytest.raises(SchemaInvalid) as exc:
        run_create_page("break the page schema now")
    assert exc.value.stage == "schema"
    tools = [s["call"]["tool"] for s in exc.value.trace["steps"]]
    assert tools[-1] == "assemble_page"
    assert "save_draft" not in tools


def test_happy_path_builds_named_sections():
    result = run_create_page(CREATE_CMD)
    assert composed(result["page"]) == ["hero", "faq"]
    assert result["brief"]["business"] == "Maria's Bakery"
    assert result["validation"]["valid"] is True
    assert result["validation"]["gates"]["operations"] == "ok"


def test_happy_path_trace_order():
    result = run_create_page(CREATE_CMD)
    tools = [s["call"]["tool"] for s in result["_trace"]["steps"]]
    assert tools[0] == "interpret"
    assert tools.index("generate_schema") < tools.index("plan") < tools.index("assemble_page")
    assert max(i for i, t in enumerate(tools) if t == "assemble_section") \
        < tools.index("assemble_page")
    assert "save_draft" not in tools


def test_gate3_defaults_invalid_copy(monkeypatch):
    monkeypatch.setattr(providers.DEFAULT.lang, "generate_copy", lambda section_type, brief: {})
    result = run_create_page(CREATE_CMD)
    assert result["validation"]["gates"]["operations"] == "defaulted"
    assert composed(result["page"]) == ["hero", "faq"]


BENEFITS_CMD = "Create a landing page for Maria's Bakery with a hero and benefits"


def test_each_benefit_gets_its_own_icon_operation():
    result = run_create_page(BENEFITS_CMD)
    items = by_type(result["page"], "benefits")["items"]
    operations = result["plan"]["operations"]
    assert [op for op in operations if op.startswith("select_icon")] == \
        [f"select_icon:benefits#{i + 1}" for i in range(len(items))]
    assert "select_image:benefits" not in operations


def test_icon_operations_run_after_the_copy_they_illustrate():
    result = run_create_page(BENEFITS_CMD)
    tools = [s["call"]["tool"] for s in result["_trace"]["steps"]]
    assert tools.index("select_icon") > tools.index("generate_copy")
    assert tools.index("select_icon") < tools.index("assemble_page")


def test_each_icon_step_records_the_item_it_chose_for():
    result = run_create_page(BENEFITS_CMD)
    steps = [s for s in result["_trace"]["steps"] if s["call"]["tool"] == "select_icon"]
    titles = [item["title"] for item in by_type(result["page"], "benefits")["items"]]
    assert [s["call"]["args"]["item"] for s in steps] == list(range(1, len(titles) + 1))
    assert [s["call"]["args"]["title"] for s in steps] == titles
    assert all(step["result"]["status"] in ("ok", "repaired", "defaulted")
               for step in steps)


def test_no_two_benefits_share_an_icon():
    icons = [item["icon"]["id"]
             for item in by_type(run_create_page(BENEFITS_CMD)["page"], "benefits")["items"]]
    assert len(set(icons)) == len(icons)


def test_an_unusable_icon_name_defaults_rather_than_failing(monkeypatch):
    monkeypatch.setattr(providers.DEFAULT.lang, "choose_icon",
                        lambda item, brief, taken=None, hint=None: {})
    result = run_create_page(BENEFITS_CMD)
    items = by_type(result["page"], "benefits")["items"]
    assert all(item["icon"]["src"].endswith(".svg") for item in items)
    assert len({item["icon"]["id"] for item in items}) == len(items)
    statuses = {step["result"]["status"] for step in result["_trace"]["steps"]
                if step["call"]["tool"] == "select_icon"}
    assert statuses and "ok" not in statuses
