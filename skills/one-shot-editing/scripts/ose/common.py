"""Shared helpers: paths, JSON IO, ffmpeg/ffprobe wrappers, timeline remapping."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
ASSETS = SKILL_DIR / "assets"
OSE_HOME = Path(os.environ.get("OSE_HOME", Path.home() / ".one-shot-editing"))
LIBRARY = OSE_HOME / "library"
MUSIC_DIR = LIBRARY / "music"
BROLL_DIR = LIBRARY / "broll"
PERF_CSV = OSE_HOME / "performance.csv"

W, H = 1080, 1920  # vertical canvas
FPS = 30


class OseError(RuntimeError):
    pass


def log(msg: str) -> None:
    print(f"[ose] {msg}", file=sys.stderr)


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        if default is not None:
            return default
        raise OseError(f"missing file: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path, data) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
    return p


def run(cmd: list[str], *, capture: bool = False, cwd=None, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(
        [str(c) for c in cmd],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if check and res.returncode != 0:
        tail = "\n".join((res.stderr or "").strip().splitlines()[-25:])
        raise OseError(f"command failed ({res.returncode}): {' '.join(map(str, cmd[:6]))} ...\n{tail}")
    return res


def ffmpeg(args: list, *, cwd=None, capture_stderr: bool = False) -> subprocess.CompletedProcess:
    return run(["ffmpeg", "-hide_banner", "-y", "-loglevel", "info" if capture_stderr else "error", *args], cwd=cwd)


def probe(path) -> dict:
    res = run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture=True,
    )
    data = json.loads(res.stdout)
    info = {"path": str(path), "duration": float(data.get("format", {}).get("duration", 0) or 0)}
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in info:
            if s.get("disposition", {}).get("attached_pic"):
                continue
            info["width"], info["height"] = int(s["width"]), int(s["height"])
            rot = 0
            for sd in s.get("side_data_list", []) or []:
                if "rotation" in sd:
                    rot = int(sd["rotation"])
            rot = int(s.get("tags", {}).get("rotate", rot) or rot)
            if abs(rot) in (90, 270):
                info["width"], info["height"] = info["height"], info["width"]
            num, _, den = (s.get("avg_frame_rate") or "0/1").partition("/")
            info["fps"] = float(num) / float(den or 1) if float(den or 1) else 0.0
            info["vcodec"] = s.get("codec_name")
        elif s.get("codec_type") == "audio" and "audio" not in info:
            info["audio"] = True
            info["sample_rate"] = int(s.get("sample_rate", 0) or 0)
    info.setdefault("audio", False)
    return info


IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mts"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}


def media_kind(path) -> str:
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    if ext in AUDIO_EXT:
        return "audio"
    return "other"


def norm_token(text: str) -> str:
    """Lowercase, strip accents-insensitive punctuation; keep letters/digits."""
    t = unicodedata.normalize("NFC", text.lower().strip())
    return re.sub(r"[^\w']+", "", t).strip("'")


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def slug(text: str, maxlen: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", strip_accents(text.lower())).strip("-")
    return s[:maxlen].strip("-") or "item"


# ---------------------------------------------------------------- project ---

class Project:
    """A project folder: raw/ (inputs), work/ (intermediates), out/ (deliverables)."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.raw = self.root / "raw"
        self.work = self.root / "work"
        self.out = self.root / "out"
        self.meta_path = self.root / "project.json"

    @property
    def meta(self) -> dict:
        return read_json(self.meta_path, {})

    def save_meta(self, meta: dict) -> None:
        write_json(self.meta_path, meta)

    def update_meta(self, **kv) -> dict:
        m = self.meta
        m.update(kv)
        self.save_meta(m)
        return m

    def require(self) -> "Project":
        if not self.meta_path.exists():
            raise OseError(f"{self.root} is not an ose project (run `ose init`)")
        return self

    @property
    def source(self) -> Path:
        src = self.meta.get("source")
        if not src:
            raise OseError("project has no source video")
        p = Path(src)
        return p if p.is_absolute() else self.root / p

    # canonical file locations
    transcript = property(lambda self: self.work / "transcript.json")
    edl = property(lambda self: self.work / "edl.json")
    cut = property(lambda self: self.work / "cut.mp4")
    cut_words = property(lambda self: self.work / "cut_words.json")
    plan = property(lambda self: self.work / "plan.json")
    captions_ass = property(lambda self: self.work / "captions.ass")
    final = property(lambda self: self.out / "final.mp4")


# --------------------------------------------------------------- timeline ---

def segment_offsets(segments: list[dict]) -> list[float]:
    """Cut-timeline start of each kept source segment."""
    offs, acc = [], 0.0
    for s in segments:
        offs.append(acc)
        acc += s["out"] - s["in"]
    return offs


def src_to_cut(t: float, segments: list[dict], offsets: list[float] | None = None):
    """Map a source time to the cut timeline, or None if it was removed."""
    offsets = offsets or segment_offsets(segments)
    for s, off in zip(segments, offsets):
        if s["in"] - 1e-6 <= t <= s["out"] + 1e-6:
            return off + (min(max(t, s["in"]), s["out"]) - s["in"])
    return None


def remap_words(words: list[dict], segments: list[dict]) -> list[dict]:
    """Return words that survive the cut, with start/end on the cut timeline."""
    offsets = segment_offsets(segments)
    out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        for s, off in zip(segments, offsets):
            if s["in"] <= mid <= s["out"]:
                a = off + max(w["start"], s["in"]) - s["in"]
                b = off + min(w["end"], s["out"]) - s["in"]
                if b > a:
                    out.append({**w, "start": round(a, 3), "end": round(b, 3)})
                break
    return out


def cut_duration(segments: list[dict]) -> float:
    return sum(s["out"] - s["in"] for s in segments)


def which(name: str) -> str | None:
    return shutil.which(name)


def fmt_time(t: float) -> str:
    m, s = divmod(max(t, 0), 60)
    return f"{int(m):02d}:{s:05.2f}"


def normalize_plan(plan: dict) -> dict:
    """Accept start+duration or start+end everywhere; store zooms/texts as start/end and b-roll as start/duration."""
    def span(item):
        s = float(item.get("start", 0))
        if "end" not in item and "duration" in item:
            item["end"] = round(s + float(item["duration"]), 3)
        if "duration" not in item and "end" in item:
            item["duration"] = round(float(item["end"]) - s, 3)
        if "end" not in item:
            raise OseError(f"plan item needs 'end' or 'duration': {item}")
        return item

    for key in ("zooms", "texts"):
        plan[key] = [{k: v for k, v in span(i).items() if k != "duration"} for i in plan.get(key, [])]
    plan["broll"] = [{k: v for k, v in span(i).items() if k != "end"} for i in plan.get("broll", [])]
    for s in plan.get("sfx", []):
        if "asset" not in s and "file" in s:
            s["asset"] = s.pop("file")
        if "at" not in s and "start" in s:
            s["at"] = s.pop("start")
    return plan


def load_plan(project) -> dict:
    return normalize_plan(read_json(project.plan, {}))
