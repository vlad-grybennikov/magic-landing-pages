from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

from .evaluators import OutcomeCheck, PathCheck


class Outcome(BaseModel):
    name: str
    runs: int
    k: int = 0
    passes: int
    pass_rate: float
    pass_hat_k: float
    diffs: list[str] = Field(default_factory=list)
    rejected_at: Optional[str] = None
    per_run: list[OutcomeCheck] = Field(default_factory=list)
    seconds: float = 0.0

    @property
    def passed(self) -> bool:
        return self.passes == self.runs


class Path(BaseModel):
    name: str
    runs: int
    node_f1: float
    node_precision: float
    node_recall: float
    edge_f1: float
    order_conformance: float
    redundancy_ratio: float
    policies_passed: bool
    missing_ops: list[str] = Field(default_factory=list)
    observed_ops: list[str] = Field(default_factory=list)
    policy_failures: list[str] = Field(default_factory=list)
    per_run: list[PathCheck] = Field(default_factory=list)


class ClassLabelMetrics(BaseModel):
    precision: float
    recall: float
    f1: float
    support: int


class Classification(BaseModel):
    name: str
    accuracy: float
    macro_f1: float
    per_class: dict[str, ClassLabelMetrics] = Field(default_factory=dict)
    errors: list[dict] = Field(default_factory=list)
    total: int = 0


class Extraction(BaseModel):
    name: str
    slot_accuracy: float
    per_slot: dict[str, float] = Field(default_factory=dict)
    errors: list[dict] = Field(default_factory=list)
    total: int = 0


class Retrieval(BaseModel):
    name: str
    k: int
    recall_at_k: float
    hits: int = 0
    total: int = 0
    misses: list[dict] = Field(default_factory=list)


class Components(BaseModel):
    name: str
    phrasings: int = 1
    intent_accuracy: Optional[float] = None
    slot_accuracy: Optional[float] = None
    sections_accuracy: Optional[float] = None
    image_recall: Optional[float] = None
    per_slot: dict[str, float] = Field(default_factory=dict)
    predicted_intents: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CaseResult(BaseModel):
    name: str
    stage: str
    kind: str
    doc: str = ""
    passed: bool = True
    error: Optional[str] = None
    skipped: bool = False
    measurement: Any = None

    @model_validator(mode="after")
    def _rebuild_measurement(self) -> "CaseResult":
        if isinstance(self.measurement, dict):
            model = MEASUREMENT_TYPES.get(self.kind)
            if model is not None:
                self.measurement = model.model_validate(self.measurement)
        return self


MEASUREMENT_TYPES: dict[str, type[BaseModel]] = {
    "outcome": Outcome,
    "path": Path,
    "components": Components,
    "classification": Classification,
    "extraction": Extraction,
    "retrieval": Retrieval,
}
