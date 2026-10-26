"""Music library: download (yt-dlp), analyse (tempo/energy/brightness), tag by vibe, suggest by topic."""
from __future__ import annotations

import datetime as dt
import hashlib
import re
import shutil
from pathlib import Path

from .common import MUSIC_DIR, OseError, log, media_kind, probe, read_json, run, strip_accents, write_json

INDEX = MUSIC_DIR / "index.json"

# Mood vocabulary (also used by the agent when tagging). Keep tags lowercase, English.
MOODS = ["hype", "upbeat", "playful", "chill", "calm", "emotional", "dark", "epic", "suspense", "funny", "nostalgic"]
LICENSES = ["unknown", "platform-only", "royalty-free", "owned", "cc-by"]


def load_index() -> list[dict]:
    return read_json(INDEX, [])


def save_index(items) -> None:
    write_json(INDEX, items)


def analyse(path) -> dict:
    import librosa
    import numpy as np

    info = probe(path)
    dur = info["duration"]
    offset = max(0.0, dur / 2 - 30) if dur > 70 else 0.0
    y, sr = librosa.load(str(path), sr=22050, mono=True, offset=offset, duration=60)
    if not len(y):
        raise OseError(f"could not decode audio: {path}")
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    rms_db = float(20 * np.log10(np.mean(librosa.feature.rms(y=y)) + 1e-9))
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    onset = float(np.mean(librosa.onset.onset_strength(y=y, sr=sr)))
    energy = float(np.clip((rms_db + 35) / 27, 0, 1))  # ~-35 dB quiet .. -8 dB loud
    brightness = float(np.clip((centroid - 1000) / 3000, 0, 1))
    return {"duration": round(dur, 2), "bpm": round(tempo, 1), "energy": round(energy, 2),
            "brightness": round(brightness, 2), "onset": round(onset, 2), "mood_guess": guess_mood(tempo, energy, brightness)}


def guess_mood(bpm, energy, brightness) -> list[str]:
    m = []
    if energy > 0.7 and bpm >= 115:
        m.append("hype")
    elif energy > 0.55:
        m.append("upbeat")
    if energy < 0.45 and bpm < 115:
        m.append("chill" if brightness > 0.35 else "calm")
    if brightness < 0.25 and energy < 0.6:
        m.append("dark")
    if brightness > 0.55 and 95 <= bpm <= 135 and energy > 0.4:
        m.append("playful")
    return m or (["upbeat"] if energy >= 0.45 else ["chill"])


def _new_id(seed: str) -> str:
    return "m" + hashlib.sha1(seed.encode()).hexdigest()[:7]


def add(source: str, *, tags=(), vibe="", license="unknown", title=None) -> dict:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    items = load_index()
    if re.match(r"https?://", source):
        if any(i.get("source_url") == source for i in items):
            raise OseError(f"already in library: {source}")
        tmpl = str(MUSIC_DIR / "%(title).80B [%(id)s].%(ext)s")
        res = run(["yt-dlp", "--no-playlist", "-x", "--audio-format", "mp3", "--audio-quality", "0",
                   "--print", "after_move:filepath", "-o", tmpl, source], capture=True)
        path = Path(res.stdout.strip().splitlines()[-1])
        title = title or re.sub(r"\s*\[[^\]]+\]$", "", path.stem)
        url = source
    else:
        src = Path(source).expanduser().resolve()
        if media_kind(src) not in ("audio", "video"):
            raise OseError(f"not an audio file: {src}")
        path = MUSIC_DIR / src.name
        if src != path:
            shutil.copy2(src, path)
        title = title or src.stem
        url = None
    log(f"analysing {path.name}")
    feats = analyse(path)
    moods = feats.pop("mood_guess", [])
    item = {"id": _new_id(str(path)), "title": title, "path": str(path), "source_url": url, **feats, "moods": moods,
            "tags": sorted({t.strip().lower() for t in tags if t.strip()}), "vibe": vibe,
            "license": license, "uses": 0, "added": dt.date.today().isoformat()}
    items = [i for i in items if i["id"] != item["id"]] + [item]
    save_index(items)
    return item


def tag(item_id, *, tags=None, moods=None, vibe=None, license=None, title=None) -> dict:
    items = load_index()
    it = find(items, item_id)
    if tags is not None:
        it["tags"] = sorted({*it.get("tags", []), *(t.strip().lower() for t in tags if t.strip())})
    if moods is not None:
        it["moods"] = [m.strip().lower() for m in moods if m.strip()]
    if vibe is not None:
        it["vibe"] = vibe
    if license is not None:
        it["license"] = license
    if title is not None:
        it["title"] = title
    save_index(items)
    return it


def find(items, item_id):
    for it in items:
        if it["id"] == item_id or Path(it["path"]).name == item_id:
            return it
    raise OseError(f"no music item {item_id}")


def resolve(ref: str) -> dict:
    """Accept a library id or a direct file path."""
    if Path(ref).expanduser().exists():
        return {"id": None, "path": str(Path(ref).expanduser().resolve()), "license": "unknown", "title": Path(ref).stem}
    return find(load_index(), ref)


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", strip_accents((text or "").lower())) if len(w) > 2}


def suggest(query="", *, mood=None, energy=None, min_duration=0, n=5, avoid_overused=True) -> list[dict]:
    items = load_index()
    q = _words(query)
    scored = []
    for it in items:
        if it.get("duration", 0) < min_duration:
            continue
        text = " ".join([it.get("title", ""), it.get("vibe", ""), " ".join(it.get("tags", [])), " ".join(it.get("moods", []))])
        overlap = len(q & _words(text))
        s = 2.0 * overlap
        if mood:
            s += 3.0 if mood in it.get("moods", []) else 0
        if energy is not None:
            s += 1.5 * (1 - abs(energy - it.get("energy", 0.5)))
        if avoid_overused:
            s -= 0.15 * it.get("uses", 0)
        scored.append((round(s, 2), it))
    scored.sort(key=lambda x: -x[0])
    return [{"score": s, **{k: it[k] for k in ("id", "title", "bpm", "energy", "moods", "tags", "vibe", "license", "duration")}}
            for s, it in scored[:n]]


def mark_used(item_id) -> None:
    items = load_index()
    try:
        find(items, item_id)["uses"] = find(items, item_id).get("uses", 0) + 1
        save_index(items)
    except OseError:
        pass


def remove(item_id, delete_file=False) -> None:
    items = load_index()
    it = find(items, item_id)
    if delete_file:
        Path(it["path"]).unlink(missing_ok=True)
    save_index([i for i in items if i is not it])

