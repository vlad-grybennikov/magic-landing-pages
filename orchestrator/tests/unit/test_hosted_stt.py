import httpx
import pytest

from settings import ConfigError, Settings
from transcriber import HostedTranscriber, Transcriber, TranscriptionFailed, build_transcriber


def transcriber(handler, provider="openai", **kw):
    kw.setdefault("api_key", "sk-test")
    return HostedTranscriber(provider, transport=httpx.MockTransport(handler), **kw)


def test_request_is_multipart_with_model_and_language():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.content
        seen["type"] = request.headers["content-type"]
        return httpx.Response(200, json={"text": "  Create a page for Maria's Bakery "})

    text, language = transcriber(handler).transcribe(b"OggS...")
    assert (text, language) == ("Create a page for Maria's Bakery", "en")
    assert seen["url"] == "https://api.openai.com/v1/audio/transcriptions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["type"].startswith("multipart/form-data")
    for part in (b'name="model"\r\n\r\nwhisper-1', b'name="language"\r\n\r\nen',
                 b'name="response_format"\r\n\r\njson',
                 b'name="file"; filename="command.webm"', b"OggS..."):
        assert part in seen["body"]


def test_groq_uses_its_own_endpoint_model_and_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-env")
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.content
        return httpx.Response(200, json={"text": "ok"})

    made = HostedTranscriber("groq", transport=httpx.MockTransport(handler))
    made.transcribe(b"x")
    assert seen["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert seen["auth"] == "Bearer gsk-env"
    assert b"whisper-large-v3-turbo" in seen["body"]

    made = transcriber(handler, "groq", model="whisper-large-v3")
    made.transcribe(b"x")
    assert b"whisper-large-v3\r\n" in seen["body"]


def test_auto_detect_sends_no_language():
    seen = {}

    def handler(request):
        seen["body"] = request.content
        return httpx.Response(200, json={"text": "hola"})

    text, language = transcriber(handler, language=None).transcribe(b"x")
    assert (text, language) == ("hola", None)
    assert b'name="language"' not in seen["body"]


def test_http_and_connection_errors_are_transcription_failures():
    def rejected(request):
        return httpx.Response(401, json={"error": {"message": "bad key"}})

    with pytest.raises(TranscriptionFailed, match="401"):
        transcriber(rejected).transcribe(b"x")

    def down(request):
        raise httpx.ConnectError("no route")

    with pytest.raises(TranscriptionFailed, match="no route"):
        transcriber(down).transcribe(b"x")


def test_hosted_transcriber_needs_no_warm_up():
    made = transcriber(lambda request: httpx.Response(200, json={"text": ""}))
    assert made.loaded is True
    assert made.load() is made
    made.close()


def test_build_transcriber_follows_settings():
    local = build_transcriber(Settings(stt="local", stt_language=None))
    assert isinstance(local, Transcriber)
    assert (local.model_name, local.language) == ("large-v3-turbo", None)
    assert build_transcriber(Settings(stt="local", stt_model="small")).model_name == "small"

    hosted = build_transcriber(Settings(stt="groq", stt_api_key="k", stt_language="en"))
    assert isinstance(hosted, HostedTranscriber)
    assert (hosted.provider, hosted.api_key, hosted.model, hosted.language) == \
        ("groq", "k", "whisper-large-v3-turbo", "en")
    assert build_transcriber(Settings(stt="openai", stt_api_key="k")).model == "whisper-1"


def test_settings_validate_the_stt_provider_and_key():
    with pytest.raises(ConfigError, match="GROQ_API_KEY"):
        Settings(stt="groq").validate()
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        Settings(stt="openai").validate()
    with pytest.raises(ConfigError, match="MLP_STT"):
        Settings(stt="deepgram").validate()
    Settings(stt="groq", stt_api_key="k").validate()
    Settings(stt="local").validate()

    settings = Settings.from_env({"MLP_STT": " Groq ", "GROQ_API_KEY": " k ",
                                  "OPENAI_API_KEY": "other", "MLP_STT_MODEL": " "})
    assert (settings.stt, settings.stt_api_key, settings.stt_model) == ("groq", "k", None)
    assert Settings.from_env({"MLP_STT": "openai", "OPENAI_API_KEY": "o"}).stt_api_key == "o"
