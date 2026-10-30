"""Explicitly opt-in, local OpenCLIP retrieval; never uploads library media."""
from __future__ import annotations

from . import broll
from .common import OseError, read_json, write_json
from .locking import locked
from .provenance import digest, revision


def _backend(model, pretrained):
    try:
        import open_clip
        import torch
    except ImportError as error:
        raise OseError("semantic search needs setup.sh --extra semantic (downloads model dependencies)") from error
    encoder, _, preprocess = open_clip.create_model_and_transforms(model, pretrained=pretrained, device="cpu")
    encoder.eval()
    return encoder, preprocess, open_clip.get_tokenizer(model), torch


def _signature(items):
    return revision([{"id": item["id"], "media": digest(item["path"]) if item.get("path") else None,
                      "thumbs": [digest(path) for path in item.get("thumbs", [])]}
                     for item in items])


def build_index(model="ViT-B-32", pretrained="laion2b_s34b_b79k"):
    from PIL import Image
    with locked(broll.INDEX):
        items = broll.load_index()
        if not items:
            raise OseError("B-roll library is empty")
        encoder, preprocess, _, torch = _backend(model, pretrained)
        vectors = []
        with torch.inference_mode():
            for item in items:
                if not item.get("thumbs"):
                    raise OseError(f"B-roll {item['id']} has no thumbnails; reimport before indexing")
                embeddings = []
                for path in item["thumbs"]:
                    with Image.open(path) as image:
                        embeddings.append(encoder.encode_image(preprocess(image.convert("RGB")).unsqueeze(0)))
                vector = torch.cat(embeddings).mean(dim=0)
                norm = vector.norm()
                if not torch.isfinite(vector).all() or norm.item() == 0:
                    raise OseError(f"invalid embedding for {item['id']}")
                vectors.append({"id": item["id"], "vector": (vector / norm).tolist()})
        write_json(broll.BROLL_DIR / "semantic.json",
                   {"model": model, "pretrained": pretrained, "signature": _signature(items), "vectors": vectors})
        return {"indexed": len(vectors), "model": model, "pretrained": pretrained,
                "note": "Language coverage depends on the selected model; benchmark PT-BR queries separately."}


def rank(items, vectors, query_vector, *, n=8, kind=None, min_duration=0, project=None):
    import numpy as np
    q = np.asarray(query_vector, dtype=float)
    if not np.isfinite(q).all() or np.linalg.norm(q) == 0:
        raise OseError("query embedding is not finite/nonzero")
    q = q / np.linalg.norm(q)
    by_id = {item["id"]: item for item in items}
    matches = []
    for row in vectors:
        item = by_id.get(row["id"])
        if not item or (kind and item["kind"] != kind) or (project and item.get("project") != project):
            continue
        if item["kind"] == "video" and (item.get("duration") or 0) < min_duration:
            continue
        score = float(np.dot(np.asarray(row["vector"]), q))
        matches.append({"score": round(score, 4), **{key: item.get(key) for key in
                        ("id", "kind", "path", "thumbs", "description", "labels", "duration")}})
    return sorted(matches, key=lambda row: row["score"], reverse=True)[:n]


def search(query, *, n=8, kind=None, min_duration=0, project=None):
    if not query.strip() or n <= 0:
        raise OseError("semantic search needs a nonempty query and positive result count")
    with locked(broll.INDEX):
        items = broll.load_index()
        index = read_json(broll.BROLL_DIR / "semantic.json", {})
        if not index or index.get("signature") != _signature(items):
            raise OseError("semantic index is missing/stale; run `ose broll index-semantic`")
        encoder, _, tokenizer, torch = _backend(index["model"], index["pretrained"])
        with torch.inference_mode():
            vector = encoder.encode_text(tokenizer([query]))[0].tolist()
        return rank(items, index["vectors"], vector, n=n, kind=kind, min_duration=min_duration, project=project)
