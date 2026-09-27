from dataclasses import dataclass


@dataclass(frozen=True)
class ActionSpec:
    required: tuple[str, ...]
    optional: tuple[str, ...] = ()
    needs_page: bool = False


REGISTRY: dict[str, ActionSpec] = {
    "createPage": ActionSpec(("business", "audience", "goal"), ("tone", "sections")),
    "editContent": ActionSpec(("section", "value"), ("field", "path"), True),
    "replaceImage": ActionSpec(("section",), ("query", "path"), True),
    "setIcon": ActionSpec(("section",), ("icon", "query", "path"), True),
    "addSection": ActionSpec((), ("type", "position"), True),
    "removeSection": ActionSpec(("section",), (), True),
    "moveSection": ActionSpec(("section",), ("position",), True),
    "setVariant": ActionSpec(("section",), ("variant",), True),
    "addItem": ActionSpec(("section",), ("path",), True),
    "removeItem": ActionSpec(("section",), ("path",), True),
    "moveItem": ActionSpec(("section", "path", "position"), (), True),
    "setTheme": ActionSpec(
        (), ("style", "primary", "accent", "background", "font"), True),
    "setName": ActionSpec(("value",), (), True),
    "approveSection": ActionSpec(("section",), (), True),
    "regenerateSection": ActionSpec(("section",), ("query", "field", "path"), True),
}


def missing_args(intent: str, args: dict) -> list[str]:
    spec = REGISTRY.get(intent)
    if spec is None:
        return []
    return [name for name in spec.required if not args.get(name)]
