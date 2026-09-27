import asyncio
import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from app import create_app
from oracle import FixtureLanguageService
from conftest import Session, make_services
from transcriber import ScriptedTranscriber

CREATE = "Create a landing page for Maria's Bakery targeting young families to take online orders"


class Gate(FixtureLanguageService):
    def __init__(self):
        super().__init__()
        self.release = threading.Event()
        self.entered = threading.Event()

    def interpret(self, transcript, pending=None):
        self.entered.set()
        assert self.release.wait(5), "test never released the gate"
        return super().interpret(transcript, pending)


@pytest.fixture
def gate():
    return Gate()


@pytest.fixture
def gated(gate):
    services = make_services(lang=gate, transcriber=ScriptedTranscriber(CREATE))
    with TestClient(create_app(services.settings, services)) as client:
        yield client, services
    services.close()


def events(response) -> list[dict]:
    return [json.loads(line[5:]) for line in response.text.split("\n")
            if line.startswith("data:")]


def test_a_stream_is_tagged_with_its_command_id(alice, services):
    response = alice.post("/command/text/stream", json={"text": CREATE})
    stream = events(response)
    assert stream[0]["type"] == "command"
    command_id = stream[0]["commandId"]
    assert all(e["commandId"] == command_id for e in stream)
    assert stream[-1]["type"] == "result"
    assert [e["tool"] for e in stream if e["type"] == "step"][:3] == \
        ["interpret", "generate_schema", "plan"]

    record = alice.get(f"/commands/{command_id}").json()
    assert record["status"] == "done"
    assert record["result"]["page"]["id"] == stream[-1]["result"]["page"]["id"]


def test_a_stream_opened_after_the_command_finished_still_carries_its_steps(services):
    cs = services.command_service
    record, execution = cs.submit("alice", None, CREATE, cs.text_run(CREATE, cs.context(
        {"id": "alice"}, None, None, False, None, None)))
    cs.wait(execution, 10)
    assert cs.live() == 0

    async def collect():
        return [json.loads(frame[5:]) async for frame in cs.events(record["_id"], "alice", execution)]

    stream = asyncio.run(collect())
    assert [e["tool"] for e in stream if e["type"] == "step"][:3] == \
        ["interpret", "generate_schema", "plan"]
    assert stream[-1]["type"] == "result"


def test_a_completed_command_can_be_recovered_after_disconnecting(alice, services):
    response = alice.post("/command/text/stream", json={"text": CREATE})
    command_id = events(response)[0]["commandId"]

    replay = events(alice.get(f"/commands/{command_id}/events"))
    assert replay[-1]["type"] == "result"
    assert replay[-1]["result"]["page"]["url"] == "/maria-s-bakery"


def test_a_rejected_command_is_recorded_as_failed(alice):
    response = alice.post("/command/text/stream", json={"text": "Thank you."})
    stream = events(response)
    assert stream[-1]["type"] == "error"
    assert stream[-1]["error"]["stage"] == "command"

    record = alice.get(f"/commands/{stream[0]['commandId']}").json()
    assert record["status"] == "failed"
    assert record["error"]["stage"] == "command"


def test_retrying_with_the_same_key_does_not_apply_the_command_twice(alice, services):
    first = alice.post("/command/text", json={"text": CREATE, "idempotency_key": "k1"})
    second = alice.post("/command/text", json={"text": CREATE, "idempotency_key": "k1"})
    third = alice.post("/command/text", json={"text": CREATE},
                       headers={"Idempotency-Key": "k1"})

    assert first.status_code == second.status_code == third.status_code == 200
    assert first.json()["commandId"] == second.json()["commandId"] == third.json()["commandId"]
    assert first.json()["page"]["id"] == second.json()["page"]["id"]
    assert services.pages._pages.count_documents({}) == 1

    fresh = alice.post("/command/text", json={"text": CREATE, "idempotency_key": "k2"})
    assert fresh.json()["page"]["url"] == "/maria-s-bakery-2"


def test_idempotency_keys_are_per_user(alice, bob, services):
    alice.post("/command/text", json={"text": CREATE, "idempotency_key": "shared"})
    bob.post("/command/text", json={"text": CREATE, "idempotency_key": "shared"})
    assert services.pages._pages.count_documents({}) == 2


def test_other_users_cannot_read_or_cancel_a_command(alice, bob):
    command_id = events(alice.post("/command/text/stream", json={"text": CREATE}))[0]["commandId"]
    assert bob.get(f"/commands/{command_id}").status_code == 404
    assert bob.delete(f"/commands/{command_id}").status_code == 404
    assert events(bob.get(f"/commands/{command_id}/events"))[-1]["error"]["stage"] == "command"


def test_a_running_command_can_be_cancelled_and_its_result_is_discarded(gated, gate):
    client, services = gated
    alice = Session(client, "alice")
    outcome = {}

    def start():
        outcome["response"] = alice.post("/command/text/stream", json={"text": CREATE})

    worker = threading.Thread(target=start)
    worker.start()
    assert gate.entered.wait(5)

    command_id = None
    for _ in range(50):
        listed = services.commands._commands.find_one({"status": "running"})
        if listed is not None:
            command_id = listed["_id"]
            break
        time.sleep(0.02)
    assert command_id is not None

    cancelled = alice.delete(f"/commands/{command_id}").json()
    assert cancelled["status"] == "cancelled"

    gate.release.set()
    worker.join(5)
    stream = events(outcome["response"])
    assert stream[-1]["type"] == "error"
    assert stream[-1]["error"]["stage"] == "cancelled"
    assert services.pages._pages.count_documents({}) == 0
    assert alice.get(f"/commands/{command_id}").json()["status"] == "cancelled"


def test_the_audio_route_runs_transcription_off_the_event_loop(gated, gate):
    client, services = gated
    alice = Session(client, "alice")
    outcome = {}

    def start():
        outcome["response"] = alice.post(
            "/command", files={"file": ("c.wav", b"RIFF", "audio/wav")})

    worker = threading.Thread(target=start)
    worker.start()
    assert gate.entered.wait(5)
    assert client.get("/health").json()["status"] == "ok"
    assert alice.get("/builds").status_code == 200

    gate.release.set()
    worker.join(5)
    assert outcome["response"].status_code == 200
    assert outcome["response"].json()["page"]["url"] == "/maria-s-bakery"
    assert services.transcriber.calls == [b"RIFF"]


def test_a_disconnected_client_can_reattach_to_a_live_command(gated, gate):
    client, services = gated
    alice = Session(client, "alice")
    started = {}

    def start():
        started["response"] = alice.post("/command/text/stream",
                                         json={"text": CREATE, "idempotency_key": "live"})

    worker = threading.Thread(target=start)
    worker.start()
    assert gate.entered.wait(5)
    running = services.commands._commands.find_one({"status": "running"})
    assert running is not None

    def reattach():
        started["again"] = alice.post("/command/text/stream",
                                      json={"text": CREATE, "idempotency_key": "live"})

    second = threading.Thread(target=reattach)
    second.start()
    gate.release.set()
    worker.join(5)
    second.join(5)

    original = events(started["response"])
    replayed = events(started["again"])
    assert original[0]["commandId"] == replayed[0]["commandId"] == running["_id"]
    assert replayed[-1]["type"] == "result"
    assert services.pages._pages.count_documents({}) == 1


def test_health_names_the_running_build(client, monkeypatch):
    assert client.get("/health").json() == {"status": "ok", "release": "dev", "commit": "unknown"}

    from settings import Settings
    stamped = Settings.from_env({"MLP_RELEASE": "release-2026-09-21-01-44-02", "MLP_COMMIT": "3caa1ec"})
    assert (stamped.release, stamped.commit) == ("release-2026-09-21-01-44-02", "3caa1ec")


def test_readiness_reports_dependencies(client, services):
    ready = client.get("/ready").json()
    assert ready["status"] == "ready"
    assert ready["providers"] == {"lang": True, "images": True, "icons": True}
    assert ready["transcriber"] is True
    assert ready["commands"] == 0


class Counting(FixtureLanguageService):
    def __init__(self):
        super().__init__()
        self.id = "openrouter:qwen/qwen3.5-27b"
        self.calls = 0

    def interpret(self, transcript, pending=None):
        self.calls += 1
        return super().interpret(transcript, pending)


def test_models_are_listed_and_selectable_per_command(alice, services):
    hosted = Counting()
    services.providers.models.ids.append(hosted.id)
    services.providers.models._services[hosted.id] = hosted

    listed = alice.get("/models").json()["models"]
    assert [m["id"] for m in listed] == ["stub", hosted.id]
    assert listed[0]["default"] is True and listed[1]["default"] is False
    assert listed[1] == {"id": hosted.id, "label": "qwen/qwen3.5-27b",
                         "hint": "Hosted, via OpenRouter", "default": False}

    response = alice.post("/command/text", json={"text": CREATE, "model": hosted.id})
    assert response.status_code == 200, response.text
    assert hosted.calls == 1

    response = alice.post("/command/text", json={"text": CREATE, "model": "openrouter:nope"})
    assert response.status_code == 422
    assert response.json()["error"]["stage"] == "model"
    assert hosted.calls == 1

    response = alice.post("/command/text/stream", json={"text": CREATE, "model": hosted.id})
    assert events(response)[-1]["type"] == "result"
    assert hosted.calls == 2


def test_models_require_a_signed_in_user(client):
    assert client.get("/models").status_code == 401


class BrokenTranscriber(ScriptedTranscriber):
    def transcribe(self, audio):
        from transcriber import TranscriptionFailed
        raise TranscriptionFailed("401 bad key")


def test_a_failed_transcription_is_a_503_not_a_crash():
    services = make_services(transcriber=BrokenTranscriber())
    with TestClient(create_app(services.settings, services)) as client:
        alice = Session(client, "alice")
        response = alice.post("/command", files={"file": ("c.webm", b"OggS", "audio/webm")})
        assert response.status_code == 503
        error = response.json()["error"]
        assert error["stage"] == "stt"
        assert "type the command" in error["message"]
        record = alice.get(f"/commands/{response.json()['commandId']}").json()
        assert record["status"] == "failed"
    services.close()
