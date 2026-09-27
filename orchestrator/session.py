from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo import ReturnDocument

TTL_SECONDS = 900.0
MAX_CLARIFICATIONS = 2


@dataclass
class PendingIntent:
    intent: str
    args: dict = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    asked: int = 0
    page_id: str | None = None
    owner: str | None = None
    limit: int = MAX_CLARIFICATIONS
    expires: datetime | None = None

    @property
    def expired(self) -> bool:
        return self.expires is not None and self.expires <= _now()

    @property
    def exhausted(self) -> bool:
        return self.asked >= self.limit

    def merge(self, args: dict) -> None:
        for key, value in (args or {}).items():
            if value and not self.args.get(key):
                self.args[key] = value

    def to_doc(self) -> dict:
        return {"intent": self.intent, "args": self.args, "missing": self.missing,
                "asked": self.asked, "page_id": self.page_id, "owner": self.owner,
                "limit": self.limit, "expires": self.expires}

    @classmethod
    def from_doc(cls, doc: dict) -> "PendingIntent":
        expires = doc.get("expires")
        if isinstance(expires, datetime) and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return cls(intent=doc["intent"], args=dict(doc.get("args") or {}),
                   missing=list(doc.get("missing") or []), asked=doc.get("asked", 0),
                   page_id=doc.get("page_id"), owner=doc.get("owner"),
                   limit=doc.get("limit", MAX_CLARIFICATIONS), expires=expires)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SessionStore:
    def __init__(self, collection, ttl: float = TTL_SECONDS,
                 max_clarifications: int = MAX_CLARIFICATIONS):
        self._pending = collection
        self.ttl = ttl
        self.max_clarifications = max_clarifications

    def ensure_indexes(self) -> None:
        self._pending.create_index("expires", expireAfterSeconds=0)

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _key(session_id: str, owner: Optional[str]) -> str:
        return f"{owner or ''}:{session_id}"

    def get(self, session_id: str | None, owner: Optional[str] = None) -> PendingIntent | None:
        if not session_id:
            return None
        key = self._key(session_id, owner)
        doc = self._pending.find_one({"_id": key})
        if doc is None:
            return None
        pending = PendingIntent.from_doc(doc)
        if pending.expired:
            self._pending.delete_one({"_id": key})
            return None
        return pending

    def set(self, session_id: str, pending: PendingIntent) -> PendingIntent:
        pending.limit = self.max_clarifications
        pending.expires = _now() + timedelta(seconds=self.ttl)
        key = self._key(session_id, pending.owner)
        self._pending.replace_one({"_id": key}, {"_id": key, **pending.to_doc()},
                                  upsert=True)
        return pending

    def ask(self, session_id: str, pending: PendingIntent) -> PendingIntent:
        expires = _now() + timedelta(seconds=self.ttl)
        doc = self._pending.find_one_and_update(
            {"_id": self._key(session_id, pending.owner)},
            {"$set": {"intent": pending.intent, "args": pending.args,
                      "missing": pending.missing, "page_id": pending.page_id,
                      "owner": pending.owner, "limit": self.max_clarifications,
                      "expires": expires},
             "$inc": {"asked": 1}},
            upsert=True, return_document=ReturnDocument.AFTER)
        return PendingIntent.from_doc(doc)

    def clear(self, session_id: str | None, owner: Optional[str] = None) -> None:
        if not session_id:
            return
        self._pending.delete_one({"_id": self._key(session_id, owner)})

    def __len__(self) -> int:
        return self._pending.count_documents({"expires": {"$gt": _now()}})


QUESTIONS = {
    "business": "what the business is called",
    "audience": "who the page is for",
    "goal": "what you want visitors to do",
    "section": "which section you mean",
    "field": "which part of it to change",
    "value": "what it should say instead",
    "type": "what kind of section to add",
}

DEFAULTS = {
    "business": "Your Business",
    "audience": "Local customers",
    "goal": "Generate enquiries",
}


FIELD_QUESTIONS = {
    "business": "What is the business called?",
    "audience": "Who is the page for?",
    "goal": "What should visitors do?",
    "section": "Which section do you mean?",
    "field": "Which part of it should change?",
    "value": "What should it say instead?",
    "type": "What kind of section should I add?",
}


FREE_TEXT = {"business", "value", "query"}


def field_question(name: str) -> str:
    return FIELD_QUESTIONS.get(name, f"What should the {name} be?")


def question_for(missing: list[str]) -> str:
    parts = [QUESTIONS.get(name, name) for name in missing]
    if len(parts) == 1:
        return f"Could you tell me {parts[0]}?"
    if len(parts) == 2:
        return f"Could you tell me {parts[0]} and {parts[1]}?"
    return f"Could you tell me {', '.join(parts[:-1])}, and {parts[-1]}?"
