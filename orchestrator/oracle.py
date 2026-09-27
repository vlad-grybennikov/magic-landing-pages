from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import ValidationError

from actions import missing_args
from editor import FIELD_ROLES
from llm import ExtractedArgs, Interpretation, StubLanguageService

HERE = Path(__file__).resolve().parent


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _args(slots: dict) -> ExtractedArgs:
    values = {k: v["$any"][0] if isinstance(v, dict) and v.get("$any") else v
              for k, v in slots.items() if k in ExtractedArgs.model_fields}
    if isinstance(values.get("field"), str):
        values["field"] = FIELD_ROLES.get(values["field"].lower(), values["field"])
    while values:
        try:
            return ExtractedArgs(**values)
        except ValidationError as e:
            for bad in {err["loc"][0] for err in e.errors() if err["loc"]}:
                values.pop(bad, None)
    return ExtractedArgs()


class FixtureLanguageService(StubLanguageService):
    def __init__(self, data_dir: str | Path = HERE / "test_data"):
        self._index: dict[str, dict] = {}
        for path in sorted(Path(data_dir).glob("component/*.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            expect = case.get("expect") or {}
            for variant in [case["instruction"], *case.get("variants", [])]:
                phrasing = variant if isinstance(variant, str) else variant["text"]
                override = {} if isinstance(variant, str) else variant.get("slots") or {}
                self._index[_normalize(phrasing)] = {
                    "intent": expect.get("intent"),
                    "slots": {**(expect.get("slots") or {}), **override},
                    "sections": expect.get("sections"),
                }

    def lookup(self, transcript: str) -> dict | None:
        return self._index.get(_normalize(transcript))

    def interpret(self, transcript: str, pending=None) -> Interpretation:
        hit = self.lookup(transcript)
        if hit is None or not hit["intent"]:
            return super().interpret(transcript, pending)
        args = _args(hit["slots"])
        return Interpretation(intent=hit["intent"], args=args,
                              missing=missing_args(hit["intent"], args.model_dump()))

    def generate_schema(self, brief: dict, transcript: str) -> list[str]:
        hit = self.lookup(transcript)
        if hit is None or not isinstance(hit["sections"], list):
            return super().generate_schema(brief, transcript)
        return list(hit["sections"])
