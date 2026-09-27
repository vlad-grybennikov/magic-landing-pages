from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

HERE = Path(__file__).resolve().parent.parent
IMAGES = HERE.parent / "frontend" / "public" / "images" / "library"
LIBRARY = HERE / "image_library"

MODEL = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"


def device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"


def main() -> None:
    parser = argparse.ArgumentParser(description="Embed the photo library with CLIP")
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()

    import open_clip

    records = json.loads((LIBRARY / "metadata.json").read_text(encoding="utf-8"))
    dev = device()
    print(f"{len(records)} photos, device={dev}, model={MODEL}/{PRETRAINED}")

    model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED)
    model = model.to(dev).eval()

    vectors, kept = [], []
    for start in range(0, len(records), args.batch):
        batch = records[start:start + args.batch]
        tensors, keep = [], []
        for record in batch:
            path = IMAGES / record["file"]
            if not path.exists():
                print(f"  missing, skipped: {record['file']}")
                continue
            tensors.append(preprocess(Image.open(path).convert("RGB")))
            keep.append(record)
        if not tensors:
            continue

        with torch.no_grad():
            features = model.encode_image(torch.stack(tensors).to(dev))
            features /= features.norm(dim=-1, keepdim=True)
        vectors.append(features.cpu().numpy().astype("float32"))
        kept += keep
        print(f"  {len(kept)}/{len(records)}")

    matrix = np.concatenate(vectors) if vectors else np.zeros((0, 512), dtype="float32")
    np.save(LIBRARY / "embeddings.npy", matrix)
    (LIBRARY / "index.json").write_text(json.dumps(kept, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {matrix.shape} -> {LIBRARY / 'embeddings.npy'}")


if __name__ == "__main__":
    main()
