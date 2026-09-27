from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from .annotations import (
    DependencyGraph,
    Edge,
    GoalState,
    OpSpec,
    PolicyAssertion,
    Projection,
)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str
    variants: list[str] = Field(default_factory=list)
    setup: list[dict] = Field(default_factory=list)

    def phrasings(self) -> list[str]:
        return [self.instruction, *self.variants]

    def key(self) -> str:
        return json.dumps([self.instruction, self.variants, self.setup], sort_keys=True)


class Expectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    created: dict[str, dict[str, dict]] = Field(default_factory=dict)
    changed: dict[str, dict[str, dict]] = Field(default_factory=dict)

    def to_goal(self) -> GoalState:
        return GoalState(expected=self.changed, created=self.created)


class OutcomeData(Scenario):
    model_config = ConfigDict(extra="forbid")

    expect: Expectation = Field(default_factory=Expectation)
    ignore_fields: Optional[dict[str, list[str]]] = None
    expect_rejection: Optional[str] = None

    def projection(self) -> Projection:
        if self.ignore_fields is None:
            return Projection()
        return Projection(drop_fields=self.ignore_fields)


class RequiredOp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    where: dict = Field(default_factory=dict)


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require_before: Optional[tuple[str, str]] = None
    forbid: Optional[str] = None

    def to_assertion(self) -> PolicyAssertion:
        if self.require_before:
            first, then = self.require_before
            return PolicyAssertion(kind="require_before", first=first, then=then)
        if self.forbid:
            return PolicyAssertion(kind="forbid_call", tool=self.forbid)
        raise ValueError("policy needs require_before or forbid")


Pair = Union[tuple[str, str], list[str]]


class PathData(Scenario):
    model_config = ConfigDict(extra="forbid")

    require: list[RequiredOp] = Field(default_factory=list)
    flows: list[Pair] = Field(default_factory=list)
    before: list[Pair] = Field(default_factory=list)
    policies: list[Policy] = Field(default_factory=list)

    def to_dependency(self) -> DependencyGraph:
        return DependencyGraph(
            required_ops=[OpSpec(tool=op.tool, args_include=op.where) for op in self.require],
            edges=[Edge(source=a, target=b) for a, b in self.flows],
            ordering=[Edge(source=a, target=b) for a, b in self.before],
        )

    def to_policies(self) -> list[PolicyAssertion]:
        return [p.to_assertion() for p in self.policies]


class ComponentCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str
    expect: Any
    reviewed: bool = True


class DatasetData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probe: Literal["classify", "plan_sections", "rank_images",
               "rank_categories"] = "classify"
    metric: Literal["macro_f1", "slot_accuracy", "recall_at_k", "exact_match"] = "macro_f1"
    cases: list[ComponentCase] = Field(default_factory=list)

    def reviewed_cases(self) -> list[ComponentCase]:
        return [c for c in self.cases if c.reviewed]


class ComponentExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Optional[str] = None
    slots: dict[str, Any] = Field(default_factory=dict)
    sections: Optional[Union[list[str], dict[str, Any]]] = None
    image: Optional[str] = None


class Variant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    slots: dict[str, Any] = Field(default_factory=dict)


class ComponentData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instruction: str
    variants: list[Union[str, Variant]] = Field(default_factory=list)
    expect: ComponentExpectation = Field(default_factory=ComponentExpectation)

    def phrasings(self) -> list[str]:
        return [self.instruction, *(v if isinstance(v, str) else v.text for v in self.variants)]

    def expected_slots(self, text: str) -> dict[str, Any]:
        override = next((v.slots for v in self.variants
                         if isinstance(v, Variant) and v.text == text), {})
        return {**(self.expect.slots or {}), **override}


MODELS = {
    "outcome": OutcomeData,
    "path": PathData,
    "component": DatasetData,
    "components": ComponentData,
}


def load(stage, path: str | Path, root: str | Path = "."):
    full = Path(path)
    if not full.is_absolute():
        full = Path(root) / full
    raw = json.loads(full.read_text(encoding="utf-8"))
    try:
        return MODELS[stage].model_validate(raw)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"{full}: {e}") from e
