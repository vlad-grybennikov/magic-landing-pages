from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Projection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drop_tables: list[str] = Field(default_factory=list)
    drop_fields: dict[str, list[str]] = Field(
        default_factory=lambda: {"pages": ["sections", "versions", "theme"]}
    )
    derive_section_summary: bool = True

    def apply(self, snapshot: dict) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for table, rows in snapshot["tables"].items():
            if table in self.drop_tables:
                continue
            dropped = set(self.drop_fields.get(table, []))
            projected = {}
            for row in rows:
                cells = {k: v for k, v in row.items() if k not in dropped}
                if self.derive_section_summary and table == "pages":
                    sections = row.get("sections") or []
                    cells["section_types"] = ",".join(
                        s.get("type", "?") for s in sections
                    )
                    cells["n_sections"] = len(sections)
                    cells["themed"] = bool(row.get("theme"))
                projected[str(row["id"])] = cells
            out[table] = projected
        return out


DEFAULT_PROJECTION = Projection()


class GoalState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected: dict[str, dict[str, dict]] = Field(default_factory=dict)
    created: dict[str, dict[str, dict]] = Field(default_factory=dict)


class OpSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    args_include: dict = Field(default_factory=dict)


class Edge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str


class DependencyGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_ops: list[OpSpec] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    ordering: list[Edge] = Field(default_factory=list)


class PolicyAssertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["require_before", "forbid_call"]
    first: Optional[str] = None
    then: Optional[str] = None
    tool: Optional[str] = None


class ImageCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    expected: str


class IntentCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    utterance: str
    expected: str
    source: Literal["author", "llm"] = "author"
    reviewed: bool = True


class Level3Fixtures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_intent: str
    expected_slots: dict[str, object] = Field(default_factory=dict)
    expected_sections: Optional[list[str]] = None
    image_cases: list[ImageCase] = Field(default_factory=list)


class AnnotationMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annotator: str = "author"
    minutes: Optional[int] = None


class InstructionVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    source: Literal["author", "llm"] = "llm"
    reviewed: bool = False


class TaskAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    capability: str
    instruction: str
    variants: list[InstructionVariant] = Field(default_factory=list)
    setup_pages: list[dict] = Field(default_factory=list)
    expect_rejection: Optional[str] = None
    goal: GoalState = Field(default_factory=GoalState)
    dependency: DependencyGraph = Field(default_factory=DependencyGraph)
    policies: list[PolicyAssertion] = Field(default_factory=list)
    level3: Optional[Level3Fixtures] = None
    projection: Projection = Field(
        default_factory=lambda: DEFAULT_PROJECTION.model_copy(deep=True))
    annotation: AnnotationMeta = Field(default_factory=AnnotationMeta)

    def phrasings(self, include_unreviewed: bool = False) -> list[str]:
        return [self.instruction] + [
            v.text for v in self.variants if v.reviewed or include_unreviewed
        ]


def load_task(path: str | Path) -> TaskAnnotation:
    return TaskAnnotation.model_validate(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def load_tasks(directory: str | Path) -> list[TaskAnnotation]:
    return [load_task(p) for p in sorted(Path(directory).glob("*.json"))]


def load_intent_dataset(path: str | Path,
                        include_unreviewed: bool = False) -> list[IntentCase]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = [IntentCase.model_validate(item) for item in raw]
    return [c for c in cases if c.reviewed or include_unreviewed]
