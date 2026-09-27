from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, TypedDict

LIBRARY = Path(__file__).resolve().parent / "image_library"
logger = logging.getLogger("mlp.pipeline")


class ImageChoice(TypedDict, total=False):
    id: str
    src: str
    alt: str
    category: str
    photographer: Optional[str]
    photographer_url: Optional[str]
    source_url: Optional[str]


PLACEHOLDER = {"src": "/images/hero-section.jpg", "alt": ""}


class StubImageService:
    HERO = {"src": "/images/hero-section.jpg", "alt": "Premium installed windows"}

    def rank(self, query: str = "", k: int = 5) -> list[ImageChoice]:
        return [{"id": "stub-hero", **self.HERO}][:k]

    def related(self, query: str, k: int,
                subject: Optional[str] = None) -> list[ImageChoice]:
        return [dict(self.HERO) for _ in range(k)]

    def select(self, section_type: str, query: str = "", index: int = 0) -> ImageChoice:
        if section_type == "hero":
            return dict(self.HERO)
        return dict(PLACEHOLDER)


class CLIPImageService:
    MODEL = "ViT-B-32"
    PRETRAINED = "laion2b_s34b_b79k"

    def __init__(self, library: Path = LIBRARY):
        import numpy as np

        self.records: list[dict] = json.loads(
            (library / "index.json").read_text(encoding="utf-8"))
        self.matrix = np.load(library / "embeddings.npy")
        if len(self.records) != len(self.matrix):
            raise ValueError(
                f"library out of sync: {len(self.records)} records vs "
                f"{len(self.matrix)} embeddings -- rerun scripts/embed_library.py")
        self._model = None
        self._tokenizer = None

    def _encode(self, query: str):
        import torch

        if self._model is None:
            import open_clip
            self._model, _, _ = open_clip.create_model_and_transforms(
                self.MODEL, pretrained=self.PRETRAINED)
            self._model = self._model.eval()
            self._tokenizer = open_clip.get_tokenizer(self.MODEL)
            logger.info("CLIP text encoder loaded (%d photos indexed)", len(self.records))

        with torch.no_grad():
            features = self._model.encode_text(self._tokenizer([query]))
            features /= features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy()[0]

    def rank(self, query: str, k: int = 5) -> list[ImageChoice]:
        import numpy as np

        if not self.records:
            return []
        scores = self.matrix @ self._encode(query)
        order = np.argsort(-scores)[:k]
        return [self._choice(self.records[i]) for i in order]

    @staticmethod
    def _choice(record: dict) -> ImageChoice:
        return {
            "id": record["id"],
            "src": record["src"],
            "alt": record.get("alt") or record.get("category", ""),
            "category": record.get("category", ""),
            "photographer": record.get("photographer"),
            "photographer_url": record.get("photographer_url"),
            "source_url": record.get("source_url"),
        }

    def select(self, section_type: str, query: str = "", index: int = 0) -> ImageChoice:
        ranked = self.rank(query, k=index + 1)
        if not ranked:
            return dict(PLACEHOLDER)
        return ranked[min(index, len(ranked) - 1)]

    def related(self, query: str, k: int,
                subject: Optional[str] = None) -> list[ImageChoice]:
        ranked = self.rank(query, k=len(self.records))
        if not ranked:
            return []

        subject = subject or ranked[0].get("category")
        chosen = [c for c in ranked if c.get("category") == subject][:k]
        chosen += [c for c in ranked if c not in chosen][:k - len(chosen)]
        return chosen


@lru_cache(maxsize=1)
def build_image_service():
    mode = os.environ.get("MLP_IMAGES", "").lower()
    if mode == "stub":
        return StubImageService()

    ready = (LIBRARY / "embeddings.npy").exists() and (LIBRARY / "index.json").exists()
    if mode == "clip" and not ready:
        raise RuntimeError(
            "MLP_IMAGES=clip but no embedded library -- run scripts/fetch_library.py "
            "then scripts/embed_library.py")
    if not ready:
        logger.info("no photo library found, using fixed images "
                    "(run scripts/fetch_library.py to enable CLIP selection)")
        return StubImageService()
    return CLIPImageService()


ImageService = StubImageService
