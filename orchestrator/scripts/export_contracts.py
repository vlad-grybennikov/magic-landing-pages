import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
os.environ.setdefault("MLP_ENV", "development")

from app import create_app  # noqa: E402
from manifest import build_manifest, render_ts  # noqa: E402
from settings import Settings  # noqa: E402

GENERATED = HERE.parent / "frontend" / "src" / "generated"


def render_openapi() -> str:
    schema = create_app(Settings(env="development"), warm=False).openapi()
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def outputs() -> dict[Path, str]:
    return {
        GENERATED / "openapi.json": render_openapi(),
        GENERATED / "manifest.ts": render_ts(build_manifest()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the committed files differ from the code")
    args = parser.parse_args()

    stale = []
    for path, content in outputs().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        stale.append(path)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(HERE.parent)}")

    if args.check and stale:
        for path in stale:
            print(f"out of date: {path.relative_to(HERE.parent)}", file=sys.stderr)
        print("run `make contracts` and commit the result", file=sys.stderr)
        return 1
    if not stale:
        print("contracts up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
