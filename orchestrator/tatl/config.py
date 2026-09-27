from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str
    label: str
    threshold: float
    direction: Literal["gte", "lte"] = "gte"

    def met(self, value: float) -> bool:
        return value >= self.threshold if self.direction == "gte" else value <= self.threshold


class Column(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    group: str = ""
    format: Literal["ratio", "float", "flag", "text", "count"] = "float"
    good: float = 1.0
    bad: float = 0.0
    inverted: bool = False
    width: int = 9


DEFAULT_COLUMNS: list[Column] = [
    Column(key='n', label='n', group='scope', format='count', width=5),
    Column(key='runs', label='runs', group='scope', format='ratio', width=7),
    Column(key='pass_k', label='pass^{k}', group='Outcome'),
    Column(key='node_f1', label='node F1', group='Path'),
    Column(key='edge_f1', label='edge F1', group='Path'),
    Column(key='order', label='order', group='Path'),
    Column(key='redundancy', label='redund.', group='Path', good=0.0, bad=0.5, inverted=True),
    Column(key='policies', label='policy', group='Path'),
    Column(key='intent', label='intent', group='Component'),
    Column(key='slots', label='slots', group='Component'),
    Column(key='sections', label='sections', group='Component'),
    Column(key='image', label='image', group='Component'),
]


class SuiteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter: str = "mlp_adapter:MlpAdapter"
    suite_dir: str = "suite"
    data_dir: str = "test_data"
    out_dir: str = "reports"
    workers: int = 3
    matrix: list[Column] = Field(default_factory=lambda: [c.model_copy() for c in DEFAULT_COLUMNS])

    root: str = "."

    def path(self, value: str) -> Path:
        p = Path(value)
        return p if p.is_absolute() else Path(self.root) / p

    def build_adapter(self, **kwargs):
        module_name, _, class_name = self.adapter.partition(":")
        module = importlib.import_module(module_name)
        return getattr(module, class_name)(**kwargs)

    @classmethod
    def load(cls, path: str | Path | None, root: str | Path) -> "SuiteConfig":
        if path is None:
            candidate = Path(root) / "tatl.config.json"
            if not candidate.exists():
                return cls(root=str(root))
            path = candidate
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data.setdefault("root", str(root))
        return cls.model_validate(data)
