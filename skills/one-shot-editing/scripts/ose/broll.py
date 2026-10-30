"""B-roll library: ingest (scene split + thumbnails), label/sort (by the agent's vision), search."""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import shutil
import tempfile
from pathlib import Path

from .common import BROLL_DIR, OseError, ffmpeg, log, media_kind, probe, read_json, slug, strip_accents, write_json
from .locking import index_transaction

INDEX = BROLL_DIR / "index.json"
INBOX = BROLL_DIR / "_inbox"
UNSORTED = BROLL_DIR / "_unsorted"
THUMBS = BROLL_DIR / ".thumbs"


def load_index() -> list[dict]:
    return read_json(INDEX, [])


def save_index(items) -> None:
    write_json(INDEX, items)


def _id(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "b" + digest.hexdigest()


def detect_scenes(path, threshold=27.0, max_scenes=200):
    try:
        from scenedetect import ContentDetector, detect
        scenes = detect(str(path), ContentDetector(threshold=threshold))
        out = [[round(a.get_seconds(), 2), round(b.get_seconds(), 2)] for a, b in scenes][:max_scenes]
    except Exception as e:  # noqa: BLE001 - scenedetect is optional; fall back to one scene
        log(f"scene detection skipped for {Path(path).name}: {e}")
        out = []
    return out


def make_thumbs(item: dict, n_max=6, *, directory=None) -> list[str]:
    directory = THUMBS if directory is None else Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = item["path"]
    thumbs = []
    if item["kind"] == "image":
        t = directory / f"{item['id']}_0.jpg"
        ffmpeg(["-i", path, "-vf", "scale=480:-2", "-frames:v", "1", t])
        return [str(t)]
    scenes = item["scenes"] or [[0, item["duration"]]]
    if len(scenes) > n_max:
        step = len(scenes) / n_max
        scenes = [scenes[int(k * step)] for k in range(n_max)]
    for k, (a, b) in enumerate(scenes):
        t = directory / f"{item['id']}_{k}.jpg"
        ffmpeg(["-ss", f"{(a + b) / 2:.2f}", "-i", path, "-vf", "scale=480:-2", "-frames:v", "1", t])
        thumbs.append(str(t))
    return thumbs


@index_transaction
def ingest(paths=None, *, source="user", project=None, copy=False) -> list[dict]:
    """Ingest files/folders (default: the _inbox drop folder). Inbox files are moved (unless copy=True); explicit paths are copied."""
    INBOX.mkdir(parents=True, exist_ok=True)
    UNSORTED.mkdir(parents=True, exist_ok=True)
    targets = []
    from_inbox = not paths
    for p in (paths or [INBOX]):
        p = Path(p).expanduser().resolve()
        if p.is_dir():
            targets += sorted(f for f in p.rglob("*") if f.is_file() and media_kind(f) in ("video", "image"))
        elif p.is_file():
            targets.append(p)
        else:
            raise OseError(f"not found: {p}")
    items = load_index()
    known = {_id(Path(item["path"])) for item in items if Path(item["path"]).is_file()}
    added = []
    for f in targets:
        iid = _id(f)
        if iid in known:
            log(f"skip (already ingested): {f.name}")
            continue
        if any(item["id"] == iid for item in items):
            raise OseError(f"b-roll id collision: {iid}")
        import_dir = Path(tempfile.mkdtemp(prefix="import-", dir=UNSORTED))
        dest = import_dir / f"{iid}_{slug(f.stem, 40)}{f.suffix.lower()}"
        try:
            shutil.copy2(f, dest)
            if _id(dest) != iid:
                raise OseError(f"source changed during import: {f}")
            kind = media_kind(dest)
            info = probe(dest)
            item = {"id": iid, "path": str(dest), "original_name": f.name, "kind": kind,
                    "duration": round(info["duration"], 2) if kind == "video" else None,
                    "width": info.get("width"), "height": info.get("height"), "has_audio": info.get("audio", False),
                    "scenes": detect_scenes(dest) if kind == "video" else [],
                    "source": source, "project": project, "status": "unlabeled",
                    "category": None, "labels": [], "description": "", "uses": 0,
                    "added": dt.date.today().isoformat()}
            item["thumbs"] = make_thumbs(item, directory=import_dir / ".thumbs")
            save_index(items + [item])
        except Exception:
            shutil.rmtree(import_dir, ignore_errors=True)
            raise
        items.append(item)
        known.add(iid)
        added.append(item)
        if from_inbox and not copy:
            f.unlink()
        log(f"ingested {f.name} -> {iid} ({kind}, {len(item['scenes'])} scenes)")
    return added


def find(items, iid):
    for it in items:
        if it["id"] == iid:
            return it
    raise OseError(f"no b-roll item {iid}")


def pending() -> list[dict]:
    return [{k: it[k] for k in ("id", "kind", "original_name", "duration", "thumbs", "source")}
            for it in load_index() if it["status"] == "unlabeled"]


@index_transaction
def label(iid, *, category, labels=(), description="", sort=True) -> dict:
    items = load_index()
    it = find(items, iid)
    cat = slug(category, 32)
    it.update(category=cat, labels=sorted({label_text.strip().lower() for label_text in labels if label_text.strip()}),
              description=description, status="labeled")
    if sort:
        dest_dir = BROLL_DIR / cat
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / Path(it["path"]).name
        if Path(it["path"]) != dest:
            source = Path(it["path"])
            if dest.exists():
                raise OseError(f"refusing to overwrite B-roll destination: {dest}")
            shutil.copy2(source, dest)
            it["path"] = str(dest)
            try:
                save_index(items)
            except Exception:
                dest.unlink()
                raise
            source.unlink()
            return it
    save_index(items)
    return it


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", strip_accents((text or "").lower())) if len(w) > 2}


def search(query, *, kind=None, n=8, min_duration=0.0, project=None, include_unlabeled=False) -> list[dict]:
    q = _words(query)
    out = []
    for it in load_index():
        if kind and it["kind"] != kind:
            continue
        if it["status"] != "labeled" and not include_unlabeled:
            continue
        if it["kind"] == "video" and (it["duration"] or 0) < min_duration:
            continue
        text = " ".join([it.get("category") or "", " ".join(it["labels"]), it["description"], it["original_name"]])
        score = 2 * len(q & _words(" ".join(it["labels"]) + " " + (it.get("category") or ""))) + len(q & _words(text))
        if project and it.get("project") == project:
            score += 1.5
        score -= 0.2 * it.get("uses", 0)
        if score > 0:
            out.append((score, it))
    out.sort(key=lambda x: -x[0])
    return [{"score": round(s, 2), **{k: it[k] for k in ("id", "kind", "category", "labels", "description",
                                                          "duration", "path", "thumbs")}} for s, it in out[:n]]


def resolve(ref: str) -> dict:
    p = Path(ref).expanduser()
    if p.exists():
        info = probe(p)
        return {"id": None, "path": str(p.resolve()), "kind": media_kind(p),
                "duration": info["duration"] if media_kind(p) == "video" else None}
    return find(load_index(), ref)


@index_transaction
def mark_used(iid) -> None:
    items = load_index()
    for it in items:
        if it["id"] == iid:
            it["uses"] = it.get("uses", 0) + 1
    save_index(items)
