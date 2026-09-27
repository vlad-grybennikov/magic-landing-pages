from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import env  # noqa: E402,F401

HERE = Path(__file__).resolve().parent.parent
IMAGES = HERE.parent / "frontend" / "public" / "images" / "library"
META = HERE / "image_library" / "metadata.json"
API = "https://api.pexels.com/v1/search"

CATEGORIES = [
    "bakery", "coffee shop", "restaurant interior", "catering food",
    "florist shop", "plumber working", "electrician working",
    "home renovation construction", "window installation", "roofing work",
    "landscaping garden", "house cleaning service", "moving service",
    "car repair garage", "dental clinic", "medical clinic", "physiotherapy",
    "veterinary clinic", "dog grooming", "yoga studio", "gym fitness",
    "hair salon", "spa massage", "wedding photography", "photography studio",
    "law office", "accounting office", "real estate house", "coworking office",
    "classroom teaching", "music studio", "barber shop",
]


def fetch(client: httpx.Client, query: str, count: int) -> list[dict]:
    response = client.get(API, params={
        "query": query, "per_page": count, "orientation": "landscape",
        "size": "medium",
    })
    response.raise_for_status()
    return response.json().get("photos", [])


def restore(client: httpx.Client) -> None:
    """Download the exact photos listed in metadata.json, by Pexels id."""
    records = json.loads(META.read_text(encoding="utf-8"))
    missing = 0
    for record in records:
        target = IMAGES / record["file"]
        if target.exists():
            continue
        try:
            photo = client.get(f"https://api.pexels.com/v1/photos/{record['id']}")
            photo.raise_for_status()
            image = client.get(photo.json()["src"]["large"], timeout=60)
            image.raise_for_status()
            target.write_bytes(image.content)
        except httpx.HTTPError as e:
            missing += 1
            print(f"  skipped {record['file']} ({e})")
        time.sleep(0.3)
    print(f"\n{len(records) - missing}/{len(records)} photos in {IMAGES}")
    print("next: venv/bin/python scripts/embed_library.py")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch the Pexels photo library")
    parser.add_argument("--per-category", type=int, default=15)
    parser.add_argument("--categories", nargs="*", default=CATEGORIES)
    parser.add_argument("--from-metadata", action="store_true",
                        help="re-download the photos already listed in metadata.json")
    args = parser.parse_args()

    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        sys.exit("PEXELS_API_KEY is not set -- get a free key at https://www.pexels.com/api/")

    IMAGES.mkdir(parents=True, exist_ok=True)
    if args.from_metadata:
        with httpx.Client(headers={"Authorization": key}, timeout=30) as client:
            restore(client)
        return

    META.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    seen: set[int] = set()
    with httpx.Client(headers={"Authorization": key}, timeout=30) as client:
        for category in args.categories:
            try:
                photos = fetch(client, category, args.per_category)
            except httpx.HTTPError as e:
                print(f"  {category}: FAILED ({e})")
                continue

            kept = 0
            for photo in photos:
                if photo["id"] in seen:
                    continue
                seen.add(photo["id"])
                slug = category.replace(" ", "-")
                name = f"{slug}-{photo['id']}.jpg"
                target = IMAGES / name

                if not target.exists():
                    try:
                        image = client.get(photo["src"]["large"], timeout=60)
                        image.raise_for_status()
                        target.write_bytes(image.content)
                    except httpx.HTTPError as e:
                        print(f"  {category}: skipped {photo['id']} ({e})")
                        continue

                records.append({
                    "id": str(photo["id"]),
                    "file": name,
                    "src": f"/images/library/{name}",
                    "category": category,
                    "alt": photo.get("alt") or category,
                    "photographer": photo.get("photographer"),
                    "photographer_url": photo.get("photographer_url"),
                    "source_url": photo.get("url"),
                    "width": photo.get("width"),
                    "height": photo.get("height"),
                })
                kept += 1
            print(f"  {category}: {kept}")
            time.sleep(0.3)

    META.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    categories = len({r["category"] for r in records})
    print(f"\n{len(records)} photos across {categories} categories -> {META}")
    print("next: venv/bin/python scripts/embed_library.py")


if __name__ == "__main__":
    main()
