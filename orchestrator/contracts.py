from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from schema import Section, Theme


class GoogleLogin(BaseModel):
    idToken: str


class RefreshRequest(BaseModel):
    refreshToken: str


class User(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    picture: Optional[str] = None


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str


class LoginResponse(TokenPair):
    user: User


class AuthConfig(BaseModel):
    enabled: bool
    mode: Literal["development", "production"]


class SavedMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    tone: Optional[Literal["error"]] = None
    clarification: Optional[dict] = None


class Brief(BaseModel):
    business: Optional[str] = None
    audience: Optional[str] = None
    goal: Optional[str] = None
    tone: Optional[str] = None


class BuildPatch(BaseModel):
    title: Optional[str] = None
    messages: Optional[List[SavedMessage]] = None
    brief: Optional[Brief] = None
    summary: Optional[str] = None


class AttachRequest(BaseModel):
    page_id: str


class BuildSummary(BaseModel):
    id: str
    title: str
    pageId: Optional[str] = None
    pageUrl: Optional[str] = None
    updated: Optional[str] = None
    turns: int


class BuildDetail(BuildSummary):
    messages: List[SavedMessage]
    brief: Optional[Brief] = None
    summary: Optional[str] = None


class BuildList(BaseModel):
    builds: List[BuildSummary]


class Deleted(BaseModel):
    deleted: str


class ReadinessIssue(BaseModel):
    section: str
    index: int
    provenance: Optional[str] = None
    reason: str


class Readiness(BaseModel):
    ready: bool
    blocking: List[ReadinessIssue]
    warnings: List[ReadinessIssue]


class PublishedRef(BaseModel):
    version: int
    when: str


class PageView(BaseModel):
    id: str
    version: int
    name: Optional[str] = None
    url: str
    sections: List[Section]
    theme: Optional[Theme] = None
    published: Optional[PublishedRef] = None
    readiness: Readiness


class VersionEntry(BaseModel):
    id: str
    version: int
    label: str
    when: str
    published: bool


class OpenPage(BaseModel):
    page: PageView
    versions: List[VersionEntry]


class OpenBuild(BaseModel):
    build: BuildDetail
    page: Optional[PageView] = None
    versions: List[VersionEntry]


class ClarificationField(BaseModel):
    name: str
    question: str
    options: List[str]


class Clarification(BaseModel):
    needed: bool
    question: str
    missing: List[str]
    fields: List[ClarificationField]
    sessionId: Optional[str] = None
    intent: str
    asked: Optional[int] = None
    limit: Optional[int] = None


class Plan(BaseModel):
    action: Optional[str] = None
    schema_: List[str] = Field(alias="schema")
    operations: List[str]

    model_config = {"populate_by_name": True}


class ValidationStatus(BaseModel):
    valid: bool
    gates: Optional[dict[str, str]] = None


class CommandResponse(BaseModel):
    recognizedCommand: str
    commandId: Optional[str] = None
    sessionId: Optional[str] = None
    language: Optional[str] = None
    message: str
    summary: str
    brief: Brief
    clarifications: List[str]
    clarification: Optional[Clarification] = None
    versions: List[VersionEntry]
    page: Optional[PageView] = None
    plan: Plan
    validation: ValidationStatus


class TextCommand(BaseModel):
    text: str
    session_id: Optional[str] = None
    page_id: Optional[str] = None
    build_id: Optional[str] = None
    answering: bool = False
    section: Optional[str] = None
    model: Optional[str] = None
    idempotency_key: Optional[str] = None


class ErrorDetail(BaseModel):
    stage: str
    message: str
    current: Optional[int] = None
    expected: Optional[int] = None
    readiness: Optional[Readiness] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    recognizedCommand: Optional[str] = None
    validation: Optional[ValidationStatus] = None


class CommandRecord(BaseModel):
    id: str
    buildId: Optional[str] = None
    status: Literal["queued", "running", "done", "failed", "cancelled"]
    text: Optional[str] = None
    result: Optional[CommandResponse] = None
    error: Optional[ErrorDetail] = None
    created: Optional[str] = None
    updated: Optional[str] = None


class CommandEvent(BaseModel):
    type: Literal["command"]
    commandId: str


class StepEvent(BaseModel):
    type: Literal["step"]
    commandId: str
    index: int
    tool: str
    section: Optional[str] = None
    total: Optional[int] = None
    text: Optional[str] = None


class ResultEvent(BaseModel):
    type: Literal["result"]
    commandId: str
    result: CommandResponse


class StreamErrorEvent(BaseModel):
    type: Literal["error"]
    commandId: str
    error: ErrorDetail


class StatusEvent(BaseModel):
    type: Literal["status"]
    commandId: str
    status: str
    detached: bool = False


StreamEvent = Union[CommandEvent, StepEvent, ResultEvent, StreamErrorEvent, StatusEvent]


class EditChange(BaseModel):
    action: str
    args: dict[str, Any] = Field(default_factory=dict)


class EditRequest(BaseModel):
    page_id: str
    expected_version: Optional[int] = None
    action: Optional[str] = None
    args: dict[str, Any] = Field(default_factory=dict)
    changes: Optional[List[EditChange]] = None


class RenameRequest(BaseModel):
    page_id: str
    wanted: str


class RenameResponse(BaseModel):
    id: str
    url: str
    published: bool


class VersionSnapshot(BaseModel):
    version: int
    label: str
    when: str
    sections: List[Section]
    theme: Optional[Theme] = None
    name: Optional[str] = None


class RestoreRequest(BaseModel):
    page_id: str
    version: int
    expected_version: Optional[int] = None


class RestoreResponse(BaseModel):
    page: PageView
    versions: List[VersionEntry]
    message: str


class PublishRequest(BaseModel):
    page_id: str
    version: Optional[int] = None


class PublishResponse(BaseModel):
    id: str
    url: str
    published: bool
    version: int
    when: str
    readiness: Readiness


class UnpublishRequest(BaseModel):
    page_id: str


class UnpublishResponse(BaseModel):
    id: str
    published: bool


class PublicPage(BaseModel):
    url: str
    version: int
    name: Optional[str] = None
    sections: List[Section]
    theme: Optional[Theme] = None
    when: str


class ImageCandidate(BaseModel):
    id: Optional[str] = None
    src: str
    alt: str = ""
    category: Optional[str] = None
    photographer: Optional[str] = None
    photographer_url: Optional[str] = None
    source_url: Optional[str] = None


class ImageList(BaseModel):
    images: List[ImageCandidate]


class IconList(BaseModel):
    icons: List[ImageCandidate]


class Health(BaseModel):
    status: Literal["ok"]
    release: str
    commit: str


class ModelInfo(BaseModel):
    id: str
    label: str
    hint: str
    default: bool


class ModelList(BaseModel):
    models: List[ModelInfo]


class Ready(BaseModel):
    status: Literal["ready", "degraded"]
    mongo: bool
    providers: dict[str, bool]
    transcriber: bool
    commands: int
