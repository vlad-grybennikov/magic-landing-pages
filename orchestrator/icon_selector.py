from __future__ import annotations

import json
import logging
import math
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

LIBRARY = Path(__file__).resolve().parent / "icon_library" / "index.json"
logger = logging.getLogger("mlp.pipeline")

BUNDLED = ("quality", "energy", "personalisation")

FALLBACKS = ("badge-check", "sparkles", "thumbs-up", "star", "heart-handshake",
             "circle-check")


def _kebab(name: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", (name or "").strip())
    text = re.sub(r"[\s_]+", "-", text.lower())
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    text = re.sub(r"^lucide-", "", text)
    return re.sub(r"-icons?$", "", text)


STOP_WORDS = frozenset(
    "and the for you our its not all one any who how why are was has had but too"
    " this that from than then more most some each both only very much many into"
    " onto over under with your their there they them here when what which while"
    " about after before also just like have been will does".split())

NEGATED = re.compile(r"-(off|x)(-\d+)?$")

MIN_SIMILARITY = 0.2


NAME_WEIGHT = 3


def _tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z]+", (text or "").lower())
            if len(word) > 2}


class LucideIcons:
    def __init__(self, library: Path = LIBRARY):
        data = json.loads(library.read_text(encoding="utf-8"))
        self.version: str = data.get("version", "")
        self.tags: dict[str, list[str]] = data["icons"]

        bags: dict[str, Counter] = {}
        for name, tags in self.tags.items():
            counts: Counter = Counter()
            for token in _tokens(name.replace("-", " ")):
                counts[token] += NAME_WEIGHT
            for token in _tokens(" ".join(tags)):
                counts[token] += 1
            bags[name] = counts

        frequency = Counter(token for counts in bags.values() for token in counts)
        self.idf = {token: math.log(len(bags) / count)
                    for token, count in frequency.items()}
        self.vectors = {name: _normalized({token: weight * self.idf[token]
                                           for token, weight in counts.items()})
                        for name, counts in bags.items()}

    def __len__(self) -> int:
        return len(self.tags)

    def resolve(self, name: str) -> Optional[dict]:
        candidate = _kebab(name)
        if candidate in self.tags:
            return icon(candidate)
        singular = re.sub(r"s$", "", candidate)
        return icon(singular) if singular in self.tags else None

    def match(self, text: str, taken: Iterable[str] = ()) -> Optional[dict]:
        query = _normalized({token: weight for token in self._query_tokens(text)
                             if (weight := self.idf.get(token))})
        if not query:
            return None

        used = {_kebab(name) for name in taken}
        best: tuple[float, int, str] | None = None
        for name, vector in self.vectors.items():
            if name in used or NEGATED.search(name):
                continue
            score = sum(weight * vector.get(token, 0.0)
                        for token, weight in query.items())
            if score >= MIN_SIMILARITY and (best is None
                                            or (score, -len(name), name) > best):
                best = (score, -len(name), name)

        return icon(best[2]) if best else None

    def _query_tokens(self, text: str) -> set[str]:
        tokens = set()
        for token in _tokens(text):
            if token in STOP_WORDS:
                continue
            if token not in self.idf and token.endswith("s"):
                token = token[:-1]
            tokens.add(token)
        return tokens

    def rank(self, text: str, k: int = 40) -> list[dict]:
        needle = _kebab(text)
        phrase = (text or "").strip().lower()
        query = _normalized({token: weight for token in self._query_tokens(text)
                             if (weight := self.idf.get(token))})

        found: list[str] = []
        if needle:
            scored = []
            for name, vector in self.vectors.items():
                if NEGATED.search(name) and needle not in name:
                    continue
                score = 0.0
                if name == needle:
                    score += 4
                elif name.startswith(needle):
                    score += 3
                elif needle in name:
                    score += 2
                elif any(phrase in tag for tag in self.tags[name]):
                    score += 1
                score += self._similarity(query, vector)
                if score > 0:
                    scored.append((score, -len(name), name))
            scored.sort(reverse=True)
            found = [name for _, _, name in scored]

        if found and len(found) < k:
            alike = _normalized({
                token: weight for name in found[:3]
                for token in _tokens(" ".join(self.tags[name]))
                if (weight := self.idf.get(token))})
            related = sorted(
                ((self._similarity(alike, vector), -len(name), name)
                 for name, vector in self.vectors.items()
                 if name not in found and not NEGATED.search(name)),
                reverse=True)
            found += [name for score, _, name in related if score > 0]

        if len(found) < k:
            seen = set(found)
            found += [name for name in self._shelf() if name not in seen]
        return [icon(name) for name in found[:k]]

    @staticmethod
    def _similarity(query: dict[str, float], vector: dict[str, float]) -> float:
        return sum(weight * vector.get(token, 0.0) for token, weight in query.items())

    def _shelf(self) -> list[str]:
        rest = sorted(name for name in self.tags
                      if name not in FALLBACKS and not NEGATED.search(name))
        return [*FALLBACKS, *rest]

    def default(self, index: int = 0, taken: Iterable[str] = ()) -> dict:
        return icon(_unused(FALLBACKS, index, taken))


class BundledIcons:
    def __len__(self) -> int:
        return len(BUNDLED)

    def resolve(self, name: str) -> Optional[dict]:
        candidate = _kebab(name)
        return bundled_icon(candidate) if candidate in BUNDLED else None

    def match(self, text: str, taken: Iterable[str] = ()) -> Optional[dict]:
        remaining = [name for name in BUNDLED if name not in set(taken)]
        return bundled_icon(remaining[0]) if remaining else None

    def rank(self, text: str, k: int = 40) -> list[dict]:
        return [bundled_icon(name) for name in BUNDLED[:k]]

    def default(self, index: int = 0, taken: Iterable[str] = ()) -> dict:
        return bundled_icon(_unused(BUNDLED, index, taken))


def _unused(names: tuple[str, ...], index: int, taken: Iterable[str]) -> str:
    used = set(taken)
    for offset in range(len(names)):
        name = names[(index + offset) % len(names)]
        if name not in used:
            return name
    return names[index % len(names)]


def _normalized(vector: dict[str, float]) -> dict[str, float]:
    length = math.sqrt(sum(weight * weight for weight in vector.values()))
    return {token: weight / length for token, weight in vector.items()} if length else {}


def icon(name: str) -> dict:
    return {"src": f"/icons/{name}.svg", "alt": "", "id": name}


def bundled_icon(name: str) -> dict:
    return {"src": f"/images/{name}.svg", "alt": "", "id": name}


@lru_cache(maxsize=1)
def build_icon_service():
    mode = os.environ.get("MLP_ICONS", "").lower()
    if mode == "bundled":
        return BundledIcons()

    if not LIBRARY.exists():
        if mode == "lucide":
            raise RuntimeError(
                "MLP_ICONS=lucide but no icon vocabulary -- run scripts/fetch_icons.py")
        logger.info("no icon vocabulary found, cycling the bundled icons "
                    "(run scripts/fetch_icons.py to enable Lucide selection)")
        return BundledIcons()

    icons = LucideIcons()
    logger.info("icon vocabulary loaded: %d Lucide names (lucide-static %s)",
                len(icons), icons.version)
    return icons
