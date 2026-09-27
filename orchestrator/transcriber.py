from __future__ import annotations

import os
import tempfile
import threading
from typing import Optional

import httpx


class TranscriptionFailed(Exception):
    pass


HOSTED = {
    "openai": ("https://api.openai.com/v1", "whisper-1", "OPENAI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "whisper-large-v3-turbo", "GROQ_API_KEY"),
}


class Transcriber:
    DEFAULT_MODEL = "large-v3-turbo"

    def __init__(self, model_name: str | None = None, language: Optional[str] = "en",
                 device: str = "cpu", compute_type: str = "int8"):
        self.model_name = model_name or self.DEFAULT_MODEL
        self.language = language
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self):
        with self._lock:
            if self._model is None:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(self.model_name, device=self.device,
                                           compute_type=self.compute_type)
        return self._model

    def transcribe(self, audio: bytes) -> tuple[str, Optional[str]]:
        model = self.load()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio)
            tmp_path = tmp.name
        try:
            segments, info = model.transcribe(
                tmp_path,
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
                language=self.language,
            )
            return "".join(segment.text for segment in segments).strip(), info.language
        finally:
            os.unlink(tmp_path)

    def close(self) -> None:
        self._model = None


class HostedTranscriber:
    def __init__(self, provider: str = "openai", api_key: str | None = None,
                 model: str | None = None, language: Optional[str] = "en",
                 timeout: float = 60.0, transport: httpx.BaseTransport | None = None):
        base_url, default_model, key_var = HOSTED[provider]
        self.provider = provider
        self.api_key = api_key or os.environ.get(key_var, "")
        self.base_url = base_url
        self.model = model or default_model
        self.language = language
        self._http = httpx.Client(timeout=httpx.Timeout(timeout, connect=10),
                                  headers={"Authorization": f"Bearer {self.api_key}"},
                                  transport=transport)

    @property
    def loaded(self) -> bool:
        return True

    def load(self):
        return self

    def transcribe(self, audio: bytes) -> tuple[str, Optional[str]]:
        data = {"model": self.model, "response_format": "json"}
        if self.language:
            data["language"] = self.language
        try:
            resp = self._http.post(f"{self.base_url}/audio/transcriptions", data=data,
                                   files={"file": ("command.webm", audio, "audio/webm")})
        except httpx.HTTPError as e:
            raise TranscriptionFailed(f"transcription request failed: {e}") from e
        if resp.is_error:
            raise TranscriptionFailed(
                f"transcription request failed: {resp.status_code} {resp.text[:200]}")
        return (resp.json().get("text") or "").strip(), self.language

    def close(self) -> None:
        self._http.close()


class ScriptedTranscriber:
    def __init__(self, text: str = "", language: Optional[str] = "en"):
        self.text = text
        self.language = language
        self.calls: list[bytes] = []

    @property
    def loaded(self) -> bool:
        return True

    def load(self):
        return self

    def transcribe(self, audio: bytes) -> tuple[str, Optional[str]]:
        self.calls.append(audio)
        return self.text, self.language

    def close(self) -> None:
        pass


def build_transcriber(settings):
    if settings.stt in HOSTED:
        return HostedTranscriber(settings.stt, settings.stt_api_key, settings.stt_model,
                                 settings.stt_language)
    return Transcriber(settings.stt_model, settings.stt_language)
