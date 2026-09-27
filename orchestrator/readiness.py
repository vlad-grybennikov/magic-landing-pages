from __future__ import annotations

REVIEW_IF_GENERATED: frozenset[str] = frozenset({"testimonials", "stats", "pricing", "team"})

REVIEW_REASONS = {
    "testimonials": "Sample reviews, not real ones",
    "stats": "Made-up figures",
    "pricing": "Suggested prices, not yours",
    "team": "Made-up people",
}

PLACEHOLDER_REASON = "Placeholder text"


class NotReady(ValueError):
    def __init__(self, readiness: dict):
        super().__init__("Fix the flagged sections before publishing."
                         if readiness["blocking"]
                         else "Approve the flagged sections before publishing.")
        self.readiness = readiness


def needs_review(section: dict) -> bool:
    return (section.get("provenance") == "generated"
            and section.get("type") in REVIEW_IF_GENERATED
            and not section.get("reviewed"))


def assess(sections: list[dict]) -> dict:
    blocking: list[dict] = []
    warnings: list[dict] = []
    for index, section in enumerate(sections):
        kind = section.get("type", "")
        provenance = section.get("provenance")
        if provenance == "placeholder":
            blocking.append({"section": kind, "index": index, "provenance": provenance,
                             "reason": PLACEHOLDER_REASON})
        elif needs_review(section):
            warnings.append({"section": kind, "index": index, "provenance": provenance,
                             "reason": REVIEW_REASONS[kind]})
    return {"ready": not blocking and not warnings,
            "blocking": blocking, "warnings": warnings}


def enforce(sections: list[dict]) -> dict:
    readiness = assess(sections)
    if not readiness["ready"]:
        raise NotReady(readiness)
    return readiness
