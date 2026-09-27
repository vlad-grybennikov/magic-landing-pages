from __future__ import annotations

from abc import ABC, abstractmethod
from typing import NamedTuple, Optional

from .annotations import TaskAnnotation


class EpisodeOutcome(NamedTuple):
    trace: dict
    rejected_at: Optional[str] = None


class ComponentProbes(ABC):
    @abstractmethod
    def classify(self, utterance: str) -> tuple[str, dict]:
        pass

    def plan_sections(self, slots: dict, instruction: str) -> Optional[list[str]]:
        return None

    def rank_images(self, query: str, k: int) -> Optional[list[str]]:
        return None

    def rank_categories(self, query: str, k: int) -> Optional[list[str]]:
        return None


class AgentAdapter(ABC):
    name: str = "agent"

    @abstractmethod
    def run_episode(self, task: TaskAnnotation, run_index: int) -> EpisodeOutcome:
        pass

    @abstractmethod
    def probes(self) -> ComponentProbes:
        pass

    def close(self) -> None:  # pragma: no cover
        pass
