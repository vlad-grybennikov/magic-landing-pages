from __future__ import annotations


class ScriptedLLM:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict:
        self.calls.append((system, user))
        if not self.responses:
            raise AssertionError(
                f"ScriptedLLM exhausted after {len(self.calls)} calls;"
                f" last prompt:\n{user[:400]}"
            )
        return self.responses.pop(0)


class LoopingLLM:
    def __init__(self, cycle: list[dict]) -> None:
        self.cycle = list(cycle)
        self.n = 0

    def complete_json(self, system: str, user: str, schema: dict | None = None) -> dict:
        response = self.cycle[self.n % len(self.cycle)]
        self.n += 1
        return response
