import json
import logging
import os
import re
import time
from email.utils import parsedate_to_datetime

import httpx

from settings import listed

logger = logging.getLogger("mlp.pipeline")


class LLMUnavailable(Exception):
    pass


class LLMResponseInvalid(Exception):
    pass


FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)
FORMAT_ERROR = re.compile(r"response_format|json_schema|structured", re.I)
REASONING_ERROR = re.compile(r"reasoning", re.I)
RETRY_STATUSES = {408, 429, 500, 502, 503, 504}


def parse_json(content: str | None, reason: str | None = None) -> dict:
    if not (content or "").strip():
        raise LLMResponseInvalid(f"model returned empty content (finish={reason!r})")
    match = FENCE.match(content)
    try:
        return json.loads(match.group(1) if match else content)
    except json.JSONDecodeError as e:
        raise LLMResponseInvalid(f"model returned non-JSON: {content[:200]!r}") from e


def retry_wait(resp: httpx.Response, fallback: float) -> float:
    after = resp.headers.get("retry-after", "").strip()
    reset = resp.headers.get("x-ratelimit-reset", "").strip()
    try:
        if after.replace(".", "", 1).isdigit():
            return float(after)
        if after:
            return parsedate_to_datetime(after).timestamp() - time.time()
        if reset.isdigit():
            return int(reset) / 1000 - time.time()
    except (ValueError, TypeError):
        pass
    return fallback


class OllamaClient:
    provider = "ollama"
    name = "Ollama"
    hint = "Local, via Ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None,
                 timeout: float | None = None):
        self.base_url = (base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or "qwen3.5:latest"
        self.timeout = float(timeout or os.environ.get("MLP_LLM_TIMEOUT", "90"))
        self.think = False
        self._http = httpx.Client(timeout=httpx.Timeout(self.timeout, connect=5))

    def complete_json(self, system: str, user: str, schema: dict | None = None,
                      options: dict | None = None) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": schema if schema is not None else "json",
            "options": {"temperature": 0, "num_predict": 2048, **(options or {})},
            "keep_alive": "10m",
        }
        if self.think is not None:
            payload["think"] = self.think

        data = self._post(payload)
        return parse_json(data.get("message", {}).get("content"), data.get("done_reason"))

    def _post(self, payload: dict) -> dict:
        try:
            resp = self._http.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if self.think is not None and "think" in e.response.text.lower():
                self.think = None
                payload.pop("think", None)
                return self._post(payload)
            raise LLMUnavailable(f"Ollama request failed: {e}") from e
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"Ollama request failed: {e}") from e


class OpenRouterClient:
    provider = "openrouter"
    name = "OpenRouter"
    hint = "Hosted, via OpenRouter"

    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 model: str | None = None, timeout: float | None = None,
                 transport: httpx.BaseTransport | None = None,
                 fallbacks: tuple[str, ...] | None = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1")).rstrip("/")
        self.model = model or "qwen/qwen3.8-flash"
        if fallbacks is None:
            fallbacks = listed(os.environ.get("MLP_LLM_FALLBACKS", ""))
        self.fallbacks = tuple(dict.fromkeys(name for name in fallbacks if name != self.model))
        self.timeout = float(timeout or os.environ.get("MLP_LLM_TIMEOUT", "90"))
        self.retry_delay = 1.0
        self.retries = 5
        self.max_delay = 60.0
        self.format = "json_schema"
        self.reasoning = {"enabled": False}
        self._http = httpx.Client(
            timeout=httpx.Timeout(self.timeout, connect=10),
            headers={"Authorization": f"Bearer {self.api_key}",
                     "X-Title": "Magic Landing Pages"},
            transport=transport,
        )

    def complete_json(self, system: str, user: str, schema: dict | None = None,
                      options: dict | None = None) -> dict:
        options = dict(options or {})
        if schema is not None:
            system = (f"{system}\n\nRespond with a single JSON object matching this "
                      f"schema and nothing else:\n{json.dumps(schema)}")
        payload = {
            **self._route(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": options.pop("temperature", 0),
            "max_tokens": options.pop("num_predict", 2048),
            **({"reasoning": self.reasoning} if self.reasoning else {}),
            **self._format(schema),
            **options,
        }
        data = self._post(payload)
        if data.get("error"):
            raise LLMUnavailable(f"OpenRouter request failed: {_error_text(data)}")
        answered = data.get("model")
        if self.fallbacks and answered and answered != self.model:
            logger.warning("OpenRouter fell back from %s to %s", self.model, answered)
        choice = (data.get("choices") or [{}])[0]
        return parse_json(choice.get("message", {}).get("content"),
                          choice.get("finish_reason"))

    def _route(self) -> dict:
        if self.fallbacks:
            return {"models": [self.model, *self.fallbacks]}
        return {"model": self.model}

    def _format(self, schema: dict | None) -> dict:
        if self.format == "json_schema" and schema is not None:
            return {"response_format": {"type": "json_schema", "json_schema": {
                "name": schema.get("title", "response"), "strict": True, "schema": schema}}}
        if self.format:
            return {"response_format": {"type": "json_object"}}
        return {}

    def _post(self, payload: dict) -> dict:
        for attempt in range(self.retries + 1):
            backoff = self.retry_delay * 2 ** attempt
            try:
                resp = self._send(payload)
            except LLMUnavailable:
                if attempt == self.retries:
                    raise
                time.sleep(min(max(backoff, self.retry_delay), self.max_delay))
                continue
            if resp.status_code in RETRY_STATUSES and attempt < self.retries:
                wait = retry_wait(resp, backoff)
                time.sleep(min(max(wait, self.retry_delay), self.max_delay))
                continue
            break
        if resp.is_error and resp.status_code < 500:
            if "reasoning" in payload and REASONING_ERROR.search(resp.text):
                if payload["reasoning"] == self.reasoning:
                    self.reasoning = {"effort": "low"} if self.reasoning.get("enabled") is False else None
                payload.pop("reasoning")
                if self.reasoning:
                    payload["reasoning"] = self.reasoning
                return self._post(payload)
            if "response_format" in payload and FORMAT_ERROR.search(resp.text):
                if payload["response_format"]["type"] == self.format:
                    self.format = "json_object" if self.format == "json_schema" else None
                payload.pop("response_format")
                payload.update(self._format(None))
                return self._post(payload)
        if resp.is_error:
            raise LLMUnavailable(
                f"OpenRouter request failed: {resp.status_code} {_error_text(resp)}")
        return resp.json()

    def _send(self, payload: dict) -> httpx.Response:
        try:
            return self._http.post(f"{self.base_url}/chat/completions", json=payload)
        except httpx.HTTPError as e:
            raise LLMUnavailable(f"OpenRouter request failed: {e}") from e


def _error_text(source) -> str:
    try:
        body = source.json() if isinstance(source, httpx.Response) else source
        return str(body["error"].get("message") or body["error"])
    except Exception:  # noqa: BLE001
        return source.text[:200] if isinstance(source, httpx.Response) else str(source)
