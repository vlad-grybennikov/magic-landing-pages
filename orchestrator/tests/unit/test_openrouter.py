import json

import httpx
import pytest

from llm import (
    LanguageModels,
    ModelLanguageService,
    ModelUnknown,
    StubLanguageService,
    build_language_service,
)
from llm_client import LLMResponseInvalid, LLMUnavailable, OpenRouterClient
from providers import Providers
from settings import ConfigError, Settings

SCHEMA = {"title": "Interpretation", "type": "object",
          "properties": {"intent": {"type": "string"}}}


def reply(content, finish="stop"):
    return {"choices": [{"message": {"role": "assistant", "content": content},
                         "finish_reason": finish}]}


class Server:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, httpx.Response):
            return item
        return httpx.Response(200, json=item)


def client(*responses, **kw):
    server = Server(*responses)
    kw.setdefault("api_key", "sk-test")
    kw.setdefault("fallbacks", ())
    made = OpenRouterClient(transport=httpx.MockTransport(server), **kw)
    made.retry_delay = 0
    return made, server


def test_request_shape_matches_the_chat_completions_api():
    made, server = client(reply('{"intent": "createPage"}'))
    out = made.complete_json("You interpret.", "a page for Maria", SCHEMA,
                             {"temperature": 0.6, "seed": 7})

    assert out == {"intent": "createPage"}
    request = server.requests[0]
    assert request.url == "https://openrouter.ai/api/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer sk-test"
    body = json.loads(request.content)
    assert body["model"] == "qwen/qwen3.8-flash"
    assert body["temperature"] == 0.6
    assert body["seed"] == 7
    assert body["max_tokens"] == 2048
    assert body["reasoning"] == {"enabled": False}
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"] == {"name": "Interpretation",
                                                      "strict": True, "schema": SCHEMA}
    assert body["messages"][0]["content"].startswith("You interpret.")
    assert json.dumps(SCHEMA) in body["messages"][0]["content"]
    assert body["messages"][1] == {"role": "user", "content": "a page for Maria"}


def test_fenced_json_is_accepted():
    made, _ = client(reply('```json\n{"intent": "createPage"}\n```'))
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "createPage"}


def test_empty_and_non_json_content_are_invalid_not_unavailable():
    made, _ = client(reply("", finish="length"), reply("sure, here you go"))
    with pytest.raises(LLMResponseInvalid, match="length"):
        made.complete_json("s", "u", SCHEMA)
    with pytest.raises(LLMResponseInvalid, match="non-JSON"):
        made.complete_json("s", "u", SCHEMA)


def test_http_errors_carry_the_openrouter_message():
    made, _ = client(httpx.Response(401, json={"error": {"message": "No auth credentials",
                                                        "code": 401}}))
    with pytest.raises(LLMUnavailable, match="401 No auth credentials"):
        made.complete_json("s", "u", SCHEMA)


def test_retryable_statuses_are_retried_then_given_up_on():
    made, server = client(httpx.Response(429, json={"error": {"message": "slow down"}}),
                          reply('{"intent": "createPage"}'))
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "createPage"}
    assert len(server.requests) == 2

    made, server = client(*[httpx.Response(503, text="down")] * 6)
    with pytest.raises(LLMUnavailable, match="503"):
        made.complete_json("s", "u", SCHEMA)
    assert len(server.requests) == 6


def test_rate_limit_waits_follow_the_server_hint_then_back_off(monkeypatch):
    waits = []
    monkeypatch.setattr("llm_client.time.sleep", waits.append)
    monkeypatch.setattr("llm_client.time.time", lambda: 1000.0)

    def limited(**headers):
        return httpx.Response(429, json={"error": {"message": "slow down"}}, headers=headers)

    made, server = client(limited(**{"retry-after": "7"}),
                          limited(**{"retry-after": "Thu, 01 Jan 1970 00:17:10 GMT"}),
                          limited(**{"x-ratelimit-reset": "1012500"}),
                          limited(**{"x-ratelimit-reset": "900000"}),
                          limited(),
                          reply('{"intent": "createPage"}'))
    made.retry_delay = 1.0
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "createPage"}
    assert waits == [7.0, 30.0, 12.5, 1.0, 16.0]
    assert len(server.requests) == 6

    made, _ = client(limited(**{"retry-after": "500"}), reply('{"intent": "createPage"}'))
    made.retry_delay = 1.0
    waits.clear()
    made.complete_json("s", "u", SCHEMA)
    assert waits == [60.0]


def test_unsupported_structured_outputs_downgrade_then_stick():
    unsupported = {"error": {"message": "Provider does not support structured outputs"}}
    made, server = client(httpx.Response(400, json=unsupported),
                          httpx.Response(400, json={"error": {"message": "response_format"}}),
                          reply('{"intent": "createPage"}'),
                          reply('{"intent": "editContent"}'))
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "createPage"}
    formats = [json.loads(r.content).get("response_format") for r in server.requests]
    assert formats[0]["type"] == "json_schema"
    assert formats[1] == {"type": "json_object"}
    assert formats[2] is None
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "editContent"}
    assert len(server.requests) == 4
    assert "response_format" not in json.loads(server.requests[3].content)


def test_mandatory_reasoning_falls_back_to_low_effort_then_none_and_sticks():
    refused = {"error": {"message": "Reasoning is mandatory for this endpoint and cannot be disabled."}}
    made, server = client(httpx.Response(400, json=refused),
                          reply('{"intent": "createPage"}'),
                          reply('{"intent": "editContent"}'))
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "createPage"}
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "editContent"}
    bodies = [json.loads(r.content) for r in server.requests]
    assert bodies[0]["reasoning"] == {"enabled": False}
    assert bodies[1]["reasoning"] == {"effort": "low"}
    assert bodies[2]["reasoning"] == {"effort": "low"}
    assert bodies[2]["response_format"]["type"] == "json_schema"

    made, server = client(httpx.Response(400, json=refused), httpx.Response(400, json=refused),
                          reply('{"intent": "createPage"}'))
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "createPage"}
    assert "reasoning" not in json.loads(server.requests[2].content)
    assert made.reasoning is None


def test_concurrent_fallbacks_resend_with_the_settings_another_request_already_found():
    refused = {"error": {"message": "Reasoning is mandatory for this endpoint and cannot be disabled."}}
    made, server = client(*[httpx.Response(400, json=refused), reply('{"intent": "createPage"}')] * 3)
    in_flight = [{"model": "m", "messages": [], "reasoning": {"enabled": False}},
                 {"model": "m", "messages": [], "reasoning": {"effort": "low"}},
                 {"model": "m", "messages": [], "reasoning": {"enabled": False}}]
    for payload in in_flight:
        assert made._post(payload)["choices"][0]["message"]["content"] == '{"intent": "createPage"}'
    assert made.reasoning is None
    assert [json.loads(r.content).get("reasoning") for r in server.requests] == [
        {"enabled": False}, {"effort": "low"},
        {"effort": "low"}, None,
        {"enabled": False}, None,
    ]

    unsupported = {"error": {"message": "Provider does not support structured outputs"}}
    made, server = client(*[httpx.Response(400, json=unsupported), reply('{"intent": "createPage"}')] * 2)
    stale = {"model": "m", "messages": [], **made._format(SCHEMA)}
    made.format = None
    assert made._post(dict(stale))["choices"][0]["message"]["content"] == '{"intent": "createPage"}'
    assert made.format is None
    assert "response_format" not in json.loads(server.requests[1].content)


def test_fallback_models_ride_along_and_the_one_that_answered_is_logged(monkeypatch):
    warnings = []
    monkeypatch.setattr("llm_client.logger.warning", lambda msg, *args: warnings.append(msg % args))
    made, server = client({"model": "qwen/qwen3.8-flash", **reply('{"intent": "createPage"}')},
                          {"model": "deepseek/deepseek-v4-flash-0731", **reply('{"intent": "editContent"}')},
                          fallbacks=("deepseek/deepseek-v4-flash-0731", "qwen/qwen3.5-27b"))

    assert made.complete_json("s", "u", SCHEMA) == {"intent": "createPage"}
    body = json.loads(server.requests[0].content)
    assert body["models"] == ["qwen/qwen3.8-flash", "deepseek/deepseek-v4-flash-0731",
                              "qwen/qwen3.5-27b"]
    assert "model" not in body
    assert warnings == []

    assert made.complete_json("s", "u", SCHEMA) == {"intent": "editContent"}
    assert warnings == ["OpenRouter fell back from qwen/qwen3.8-flash to deepseek/deepseek-v4-flash-0731"]

    made, server = client(reply('{"intent": "createPage"}'))
    made.complete_json("s", "u", SCHEMA)
    body = json.loads(server.requests[0].content)
    assert body["model"] == "qwen/qwen3.8-flash"
    assert "models" not in body


def test_fallbacks_come_from_the_environment_without_the_primary_or_duplicates(monkeypatch):
    monkeypatch.setenv("MLP_LLM_FALLBACKS",
                       " deepseek/deepseek-v4-flash-0731, qwen/qwen3.8-flash ,deepseek/deepseek-v4-flash-0731, qwen/qwen3.5-27b")
    made = OpenRouterClient(api_key="k")
    assert made.fallbacks == ("deepseek/deepseek-v4-flash-0731", "qwen/qwen3.5-27b")

    made = OpenRouterClient(api_key="k", model="qwen/qwen3.5-27b")
    assert made.fallbacks == ("deepseek/deepseek-v4-flash-0731", "qwen/qwen3.8-flash")

    monkeypatch.delenv("MLP_LLM_FALLBACKS")
    assert OpenRouterClient(api_key="k").fallbacks == ()


def test_error_bodies_with_200_status_are_unavailable():
    made, _ = client({"error": {"message": "Provider returned error", "code": 502}})
    with pytest.raises(LLMUnavailable, match="Provider returned error"):
        made.complete_json("s", "u", SCHEMA)


def test_connection_failures_are_retried_then_unavailable(monkeypatch):
    calls = []

    def flaky(request):
        calls.append(request)
        if len(calls) < 3:
            raise httpx.ReadTimeout("slow")
        return httpx.Response(200, json=reply('{"intent": "createPage"}'))

    made = OpenRouterClient(api_key="k", transport=httpx.MockTransport(flaky))
    made.retry_delay = 0
    assert made.complete_json("s", "u", SCHEMA) == {"intent": "createPage"}
    assert len(calls) == 3

    def down(request):
        raise httpx.ConnectError("no route")

    made = OpenRouterClient(api_key="k", transport=httpx.MockTransport(down))
    made.retry_delay = 0
    with pytest.raises(LLMUnavailable, match="no route"):
        made.complete_json("s", "u", SCHEMA)


def test_build_language_service_picks_the_provider(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    svc = build_language_service("openrouter", "qwen/qwen3.5-9b")
    assert isinstance(svc, ModelLanguageService)
    assert isinstance(svc.client, OpenRouterClient)
    assert svc.id == "openrouter:qwen/qwen3.5-9b"
    assert build_language_service("ollama").id == "ollama:qwen3.5:latest"
    assert isinstance(build_language_service("stub"), StubLanguageService)
    with pytest.raises(ValueError, match="MLP_LLM"):
        build_language_service("bedrock")


def test_registry_offers_the_default_and_the_configured_extras(monkeypatch):
    monkeypatch.setenv("MLP_LLM", "ollama")
    monkeypatch.setenv("MLP_LLM_MODEL", "qwen3.5:9b")
    monkeypatch.setenv("MLP_LLM_MODELS", "openrouter:qwen/qwen3.5-27b, ollama:qwen3.5:9b")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    models = LanguageModels.from_env()

    assert models.default_id == "ollama:qwen3.5:9b"
    assert models.ids == ["ollama:qwen3.5:9b", "openrouter:qwen/qwen3.5-27b"]
    assert models.describe() == [
        {"id": "ollama:qwen3.5:9b", "label": "qwen3.5:9b", "hint": "Local, via Ollama",
         "default": True},
        {"id": "openrouter:qwen/qwen3.5-27b", "label": "qwen/qwen3.5-27b",
         "hint": "Hosted, via OpenRouter", "default": False},
    ]
    assert models.get() is models.default
    hosted = models.get("openrouter:qwen/qwen3.5-27b")
    assert isinstance(hosted.client, OpenRouterClient)
    assert hosted.client.model == "qwen/qwen3.5-27b"
    assert models.get("openrouter:qwen/qwen3.5-27b") is hosted
    with pytest.raises(ModelUnknown):
        models.get("openrouter:qwen/qwen3-max")
    assert models.check(None) is None
    assert models.check("") is None


def test_providers_switch_the_language_service_per_model(monkeypatch):
    monkeypatch.setenv("MLP_LLM_MODELS", "openrouter:qwen/qwen3.5-27b")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    stub = StubLanguageService()
    providers = Providers(lang=stub, images="images", icons="icons")

    assert providers.models.default_id == "stub"
    assert providers.for_model(None) is providers
    assert providers.for_model("stub") is providers
    hosted = providers.for_model("openrouter:qwen/qwen3.5-27b")
    assert hosted is not providers
    assert isinstance(hosted.lang.client, OpenRouterClient)
    assert hosted.images == "images" and hosted.icons == "icons"
    assert hosted.models is providers.models


def test_settings_validate_providers_and_the_openrouter_key():
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        Settings(llm="openrouter").validate()
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        Settings(llm="ollama", llm_models=("openrouter:qwen/qwen3.5-27b",)).validate()
    with pytest.raises(ConfigError, match="bedrock"):
        Settings(llm="bedrock").validate()
    Settings(llm="openrouter", openrouter_api_key="k").validate()
    Settings(llm="ollama", llm_models=("openrouter:qwen/qwen3.5-27b",),
             openrouter_api_key="k").validate()

    settings = Settings.from_env({"MLP_LLM": "openrouter", "OPENROUTER_API_KEY": " k ",
                                  "MLP_LLM_MODELS": "openrouter:a, ollama:b"})
    assert settings.openrouter_api_key == "k"
    assert settings.llm_models == ("openrouter:a", "ollama:b")
    assert settings.llm_providers == {"openrouter", "ollama"}
