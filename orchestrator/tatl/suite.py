from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


STAGES = ("outcome", "path", "component")


@dataclass
class Case:
    stage: str
    kind: str
    name: str
    data: str
    fn: Callable
    k: int = 1
    image_k: int = 5
    runs: Optional[int] = None
    doc: str = ""
    module: str = ""

    @property
    def label(self) -> str:
        return self.name

    @property
    def episodes(self) -> int:
        return max(self.runs or self.k, self.k)


@dataclass
class Registry:
    cases: list[Case] = field(default_factory=list)

    def add(self, case: Case) -> None:
        clash = next((c for c in self.cases
                      if c.stage == case.stage and c.kind == case.kind
                      and c.name == case.name), None)
        if clash is not None:
            raise ValueError(
                f"duplicate {case.stage} {case.kind} case {case.name!r} "
                f"({clash.module} and {case.module})")
        self.cases.append(case)

    def by_stage(self, stage: str) -> list[Case]:
        return [c for c in self.cases if c.stage == stage]

    def clear(self) -> None:
        self.cases.clear()


REGISTRY = Registry()


def _default_name(data: str, explicit: Optional[str]) -> str:
    return explicit or Path(data).stem


def _register(stage: str, kind: str, data: str, name: Optional[str],
              k: int, image_k: int, runs: Optional[int] = None):
    def decorate(fn: Callable) -> Callable:
        REGISTRY.add(Case(
            stage=stage, kind=kind, name=_default_name(data, name), data=data,
            fn=fn, k=k, image_k=image_k, runs=runs,
            doc=(fn.__doc__ or "").strip(), module=fn.__module__,
        ))
        return fn
    return decorate


def outcome(data: str, name: str | None = None, k: int = 3, runs: int | None = None):
    return _register("outcome", "outcome", data, name, k, 5, runs)


def path(data: str, name: str | None = None, k: int = 1, runs: int | None = None):
    return _register("path", "path", data, name, k, 5, runs)


class _Component:
    def __call__(self, data: str, name: str | None = None, k: int = 5):
        return _register("component", "components", data, name, 1, k)

    def classification(self, data: str, name: str | None = None):
        return _register("component", "classification", data, name, 1, 5)

    def extraction(self, data: str, name: str | None = None):
        return _register("component", "extraction", data, name, 1, 5)

    def retrieval(self, data: str, name: str | None = None, k: int = 5):
        return _register("component", "retrieval", data, name, 1, k)


component = _Component()


def load_suites(directory: str | Path) -> Registry:
    import importlib.util
    import sys

    REGISTRY.clear()
    for path in sorted(Path(directory).glob("*.py")):
        if path.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f"vlp_suite_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return REGISTRY
