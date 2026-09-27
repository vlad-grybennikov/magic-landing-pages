import mongomock
import pytest

import providers
from llm import ExtractedArgs, Interpretation
from pipeline import CommandContext, CommandUnclear, IntentInvalid, run_command
from session import PendingIntent, SessionStore, question_for
from theme import from_hue


def sessions_store(**kw):
    return SessionStore(mongomock.MongoClient()["vlp-session"]["sessions"], **kw)


def test_pending_intent_round_trips():
    store = sessions_store()
    sid = store.new_id()
    store.set(sid, PendingIntent(intent="createPage", args={"business": "Bakery"}))
    assert store.get(sid).args["business"] == "Bakery"


def test_unknown_and_empty_sessions_are_simply_absent():
    store = sessions_store()
    assert store.get("nope") is None
    assert store.get(None) is None


def test_expired_state_is_dropped():
    store = sessions_store(ttl=-1)
    store.set("s", PendingIntent(intent="createPage"))
    assert store.get("s") is None


def test_clearing_forgets_the_command():
    store = sessions_store()
    store.set("s", PendingIntent(intent="createPage"))
    store.clear("s")
    assert store.get("s") is None and len(store) == 0


def test_merge_only_fills_blanks():
    pending = PendingIntent(intent="createPage", args={"business": "Bakery"})
    pending.merge({"business": "Something Else", "audience": "families", "goal": None})
    assert pending.args == {"business": "Bakery", "audience": "families"}


def test_exhaustion_is_bounded():
    pending = PendingIntent(intent="createPage", limit=2)
    assert not pending.exhausted
    pending.asked = 2
    assert pending.exhausted


def test_ids_are_unique():
    store = sessions_store()
    assert len({store.new_id() for _ in range(50)}) == 50


def test_one_question_covers_everything_missing():
    assert question_for(["audience"]) == "Could you tell me who the page is for?"
    assert "and" in question_for(["audience", "goal"])
    assert question_for(["business", "audience", "goal"]).count(",") == 2


class FakeLang:
    def __init__(self, *interpretations, options=None):
        self.queue = list(interpretations)
        self.pendings = []
        self.options = options or {}
        self.asked_for = []

    def interpret(self, transcript, pending=None):
        self.pendings.append(pending)
        return self.queue.pop(0)

    def choose_layouts(self, brief, pack, section_types):
        return {}


    def generate_schema(self, brief, transcript):
        return ["hero"]

    def generate_copy(self, section_type, brief):
        return {"headline": "Headline", "button": {"label": "Go"}}

    def generate_theme(self, brief, hint=None):
        return from_hue(200).model_dump()

    def suggest_options(self, intent, args, missing, request=""):
        self.asked_for.append(list(missing))
        return {k: v for k, v in self.options.items() if k in missing}


def interp(intent="createPage", **args):
    return Interpretation(intent=intent, args=ExtractedArgs(**args))


@pytest.fixture
def sessions():
    return sessions_store()


def test_incomplete_command_asks_instead_of_guessing(monkeypatch, sessions):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(business="Nordvik Dental")))
    result = run_command("A page for Nordvik Dental", "en", None,
                         CommandContext(session_id="s1"), sessions)

    assert result["clarification"]["missing"] == ["audience", "goal"]
    assert "page" not in result
    assert sessions.get("s1").intent == "createPage"


def test_a_question_offers_the_model_s_options(monkeypatch, sessions):
    fake = FakeLang(interp(business="Nordvik Dental"),
                    options={"audience": ["local families", "nervous patients"]})
    monkeypatch.setattr(providers.DEFAULT, "lang", fake)
    result = run_command("A page for Nordvik Dental", "en", None,
                         CommandContext(session_id="s1"), sessions)

    fields = result["clarification"]["fields"]
    assert [f["name"] for f in fields] == ["audience", "goal"]
    assert fields[0]["options"] == ["local families", "nervous patients"]
    assert fields[0]["question"] == "Who is the page for?"


def test_a_name_is_never_offered_as_a_choice(monkeypatch, sessions):
    fake = FakeLang(interp(audience="dog owners", goal="sell senior dog food"),
                    options={"business": ["local coffee roaster"]})
    monkeypatch.setattr(providers.DEFAULT, "lang", fake)
    result = run_command("a page for a dog food brand", "en", None,
                         CommandContext(session_id="s1"), sessions)

    fields = result["clarification"]["fields"]
    assert [f["name"] for f in fields] == ["business"]
    assert fields[0]["options"] == []
    assert fake.asked_for == []


def test_options_are_asked_for_only_where_they_can_help(monkeypatch, sessions):
    fake = FakeLang(interp(goal="sell senior dog food"),
                    options={"audience": ["owners of older dogs", "new puppy owners"]})
    monkeypatch.setattr(providers.DEFAULT, "lang", fake)
    result = run_command("a page for a dog food brand", "en", None,
                         CommandContext(session_id="s1"), sessions)

    fields = {f["name"]: f["options"] for f in result["clarification"]["fields"]}
    assert fields["business"] == []
    assert fields["audience"] == ["owners of older dogs", "new puppy owners"]
    assert fake.asked_for == [["audience"]]


def test_a_question_without_options_is_still_asked(monkeypatch, sessions):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(business="Nordvik Dental")))
    result = run_command("A page for Nordvik Dental", "en", None,
                         CommandContext(session_id="s1"), sessions)

    fields = result["clarification"]["fields"]
    assert all(f["options"] == [] for f in fields)
    assert all(f["question"] for f in fields)


def test_the_answer_completes_the_original_command(monkeypatch, sessions):
    fake = FakeLang(
        interp(business="Nordvik Dental"),
        interp(intent="unsupported", audience="local families", goal="book appointments"),
    )
    monkeypatch.setattr(providers.DEFAULT, "lang", fake)
    ctx = CommandContext(session_id="s1")

    run_command("A page for Nordvik Dental", "en", None, ctx, sessions)
    result = run_command("local families, to book appointments", "en", None, ctx, sessions)

    assert result["brief"]["business"] == "Nordvik Dental"
    assert result["brief"]["audience"] == "local families"
    assert result["page"]["sections"]
    assert sessions.get("s1") is None


def test_a_one_word_answer_is_not_mistaken_for_a_blip(monkeypatch, sessions):
    fake = FakeLang(
        interp(audience="owners of older dogs", goal="sell senior dog food"),
        interp(intent="unsupported", business="OpenFarm"),
    )
    monkeypatch.setattr(providers.DEFAULT, "lang", fake)
    ctx = CommandContext(session_id="s1")

    first = run_command("a page for a dog food brand for older dogs", "en",
                        None, ctx, sessions)
    assert first["clarification"]["missing"] == ["business"]

    result = run_command("OpenFarm", "en", None, ctx, sessions)
    assert result["brief"]["business"] == "OpenFarm"
    assert result["page"]["sections"]


def test_an_answer_to_a_forgotten_question_says_so(monkeypatch, sessions):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(intent="unsupported")))
    ctx = CommandContext(session_id="gone", answering=True)

    with pytest.raises(IntentInvalid, match="lost track"):
        run_command("I want them to buy this food", "en", None, ctx, sessions)


def test_an_unsupported_command_is_still_refused_as_one(monkeypatch, sessions):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(intent="unsupported")))
    ctx = CommandContext(session_id="s1")

    with pytest.raises(IntentInvalid, match="couldn't map that"):
        run_command("what is the weather in Paris", "en", None, ctx, sessions)


def test_a_forgotten_question_does_not_hold_a_bare_answer_at_gate_zero(
        monkeypatch, sessions):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(intent="unsupported")))
    ctx = CommandContext(session_id="gone", answering=True)

    with pytest.raises(IntentInvalid, match="lost track"):
        run_command("OpenFarm", "en", None, ctx, sessions)


def test_the_same_fragment_is_still_refused_as_a_command(monkeypatch, sessions):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(business="OpenFarm")))
    with pytest.raises(CommandUnclear):
        run_command("OpenFarm", "en", None, CommandContext(session_id="s1"), sessions)


def test_the_pending_question_is_passed_to_the_model(monkeypatch, sessions):
    fake = FakeLang(interp(business="X"), interp(audience="a", goal="g"))
    monkeypatch.setattr(providers.DEFAULT, "lang", fake)
    ctx = CommandContext(session_id="s1")

    run_command("A page for X", "en", None, ctx, sessions)
    run_command("everyone, to call us", "en", None, ctx, sessions)

    assert fake.pendings[0] is None
    assert fake.pendings[1] is not None
    assert fake.pendings[1].missing == ["audience", "goal"]


def test_we_stop_asking_and_default(monkeypatch):
    sessions = sessions_store(max_clarifications=1)
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(
        interp(business="X"), interp(business="X"),
    ))
    ctx = CommandContext(session_id="s1")

    first = run_command("A page for X", "en", None, ctx, sessions)
    assert first["clarification"]["needed"]

    second = run_command("no idea", "en", None, ctx, sessions)
    assert "clarification" not in second
    assert second["page"]["sections"]


def test_without_a_session_store_defaults_apply(monkeypatch):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(business="X")))
    result = run_command("A page for X", "en", None, CommandContext(), None)
    assert result["page"]["sections"]


def test_clarification_carries_the_whole_response_contract(monkeypatch, sessions):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(business="Nordvik Dental")))
    result = run_command("A page for Nordvik Dental", "en", None,
                         CommandContext(session_id="s1"), sessions)

    for key in ("recognizedCommand", "message", "summary", "brief",
                "clarifications", "versions", "plan", "validation"):
        assert key in result, f"clarification response is missing {key!r}"
    assert result["versions"] == []
    assert result["plan"]["operations"] == []
    assert result["summary"]


def test_summary_reflects_what_was_understood_so_far(monkeypatch, sessions):
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(interp(business="Nordvik Dental")))
    result = run_command("A page for Nordvik Dental", "en", None,
                         CommandContext(session_id="s1"), sessions)
    assert "Nordvik Dental" in result["summary"]


def test_a_request_without_a_business_name_is_asked_for_one_not_titled_after_its_first_words(monkeypatch, sessions):
    transcript = ("Can you create a website for a tourism guide? I'm working in Toronto and I want "
                  "to have a website with pricing like one day tour visiting Niagara Falls")
    heard = interp(audience="visitors to Toronto", goal="sell day tours")
    monkeypatch.setattr(providers.DEFAULT, "lang", FakeLang(heard, heard))
    result = run_command(transcript, "en", None, CommandContext(session_id="s1"), sessions)
    assert result["clarification"]["missing"] == ["business"]
    assert "page" not in result

    result = run_command(transcript, "en", None, CommandContext(), None)
    assert result["page"]["name"] == "Your Business"
