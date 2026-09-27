from __future__ import annotations

import argparse
import io
import json
import tarfile
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent.parent
ICONS = HERE.parent / "frontend" / "public" / "icons"
INDEX = HERE / "icon_library" / "index.json"
REGISTRY = "https://registry.npmjs.org/lucide-static"


def download(version: str | None) -> tuple[str, bytes]:
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        meta = client.get(f"{REGISTRY}/{version or 'latest'}").json()
        return meta["version"], client.get(meta["dist"]["tarball"]).content


def extract(payload: bytes, into: Path) -> dict[str, list[str]]:
    into.mkdir(parents=True, exist_ok=True)
    names: list[str] = []
    tags: dict[str, list[str]] = {}

    with tarfile.open(fileobj=io.BytesIO(payload)) as tar:
        for member in tar:
            name = member.name
            if name == "package/tags.json":
                tags = json.loads(tar.extractfile(member).read())
            elif member.isfile() and name.startswith("package/icons/") \
                    and name.endswith(".svg"):
                stem = Path(name).stem
                (into / f"{stem}.svg").write_bytes(tar.extractfile(member).read())
                names.append(stem)

    return {name: tags.get(name, []) for name in sorted(names)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="lucide-static version (default: latest)")
    parser.add_argument("--force", action="store_true",
                        help="refetch even when the library is already built")
    args = parser.parse_args()

    if not args.force and INDEX.exists() and any(ICONS.glob("*.svg")):
        existing = json.loads(INDEX.read_text(encoding="utf-8"))
        print(f"icon library already built: {len(existing['icons'])} icons "
              f"(lucide-static {existing.get('version')}) -- use --force to refetch")
        return

    version, payload = download(args.version)
    icons = extract(payload, ICONS)

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(
        {"source": "lucide-static", "version": version, "icons": icons},
        indent=1, sort_keys=True) + "\n", encoding="utf-8")

    tagged = sum(1 for tags in icons.values() if tags)
    print(f"lucide-static {version}: {len(icons)} icons → {ICONS}")
    print(f"vocabulary → {INDEX} ({tagged} with synonym tags)")


if __name__ == "__main__":
    main()
