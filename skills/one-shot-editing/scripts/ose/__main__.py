"""ose: one-shot-editing CLI. Every command prints JSON (or a readable report) to stdout; logs go to stderr."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .common import ASSETS, BROLL_DIR, MUSIC_DIR, OSE_HOME, OseError, Project, fmt_time, probe, read_json, which, write_json


def out(data) -> None:
    if isinstance(data, str):
        print(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


# ------------------------------------------------------------------ commands

def cmd_doctor(a):
    checks = {}
    for b in ("ffmpeg", "ffprobe", "yt-dlp"):
        checks[b] = bool(which(b))
    for mod in ("faster_whisper", "rapidfuzz", "librosa", "cv2", "scenedetect", "whisperx", "demucs"):
        try:
            __import__(mod)
            checks[mod] = True
        except Exception:  # noqa: BLE001
            checks[mod] = False
    checks["agent-browser (web capture, optional)"] = bool(which("agent-browser") or which("npx"))
    checks["adb (android capture, optional)"] = bool(which("adb"))
    checks["xcrun (ios capture, macOS only)"] = bool(which("xcrun"))
    checks["fonts"] = (ASSETS / "fonts" / "Montserrat-ExtraBold.ttf").exists()
    required = ["ffmpeg", "ffprobe", "yt-dlp", "faster_whisper", "rapidfuzz", "librosa", "cv2", "fonts"]
    ok = all(checks[r] for r in required)
    out({"home": str(OSE_HOME), "ok": ok, "checks": checks,
         "hint": "run scripts/setup.sh (add --full for WhisperX + Demucs)"})
    if not ok:
        raise SystemExit(1)


def cmd_init(a):
    p = Project(a.project)
    src = Path(a.video).expanduser().resolve()
    if not src.exists():
        raise OseError(f"video not found: {src}")
    for d in (p.raw, p.work, p.out):
        d.mkdir(parents=True, exist_ok=True)
    dest = p.raw / src.name
    if not dest.exists():
        if a.copy:
            shutil.copy2(src, dest)
        else:
            dest.symlink_to(src)
    info = probe(dest)
    p.save_meta({**p.meta, "source": f"raw/{src.name}", "language": a.lang, "platform": a.platform,
                 "source_info": {k: info.get(k) for k in ("duration", "width", "height", "fps", "audio")}})
    from .render import ensure_plan
    plan = ensure_plan(p)
    plan["platform"] = a.platform
    write_json(p.plan, plan)
    out({"project": str(p.root), "source": str(dest), **p.meta["source_info"]})


def cmd_transcribe(a):
    from .transcribe import run_transcribe
    d = run_transcribe(Project(a.project), language=a.lang, model=a.model, engine=a.engine, keep_fillers=not a.no_fillers)
    out({k: d[k] for k in ("engine", "model", "language", "elapsed_s")} | {"words": len(d["words"])})


def cmd_text(a):
    p = Project(a.project).require()
    words = read_json(p.cut_words if a.cut else p.transcript)["words"]
    lines, cur, start = [], [], None
    for i, w in enumerate(words):
        if not cur:
            start = w["start"]
        cur.append(w["word"])
        nxt = words[i + 1] if i + 1 < len(words) else None
        if not nxt or nxt["start"] - w["end"] > 0.6 or w["word"].rstrip().endswith((".", "?", "!")):
            lines.append(f"[{fmt_time(start)}-{fmt_time(w['end'])}] {' '.join(cur)}")
            cur = []
    out("\n".join(lines))


def cmd_roughcut(a):
    from .roughcut import report, run_roughcut
    edl = run_roughcut(Project(a.project), pace=a.pace, aggressive=a.aggressive, prefer=a.prefer, keep=a.keep or "",
                       cut=a.cut or "", hook_range=a.hook_range)
    out(report(edl) if a.report else edl["stats"])


def cmd_cut(a):
    from .cut import render_cut
    out(render_cut(Project(a.project), reframe=a.reframe, draft=a.draft))


def cmd_captions(a):
    from .captions import run_captions
    out(run_captions(Project(a.project), style=a.style, max_words=a.words, show_captions=not a.none))


def _set_path(d, dotted, value):
    keys = dotted.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def cmd_plan(a):
    p = Project(a.project).require()
    from .render import ensure_plan
    plan = ensure_plan(p)
    for kv in a.set or []:
        k, _, v = kv.partition("=")
        try:
            val = json.loads(v)
        except json.JSONDecodeError:
            val = v
        _set_path(plan, k, val)
    for js in a.add_broll or []:
        plan.setdefault("broll", []).append(json.loads(js))
    for js in a.add_zoom or []:
        plan.setdefault("zooms", []).append(json.loads(js))
    for js in a.add_text or []:
        plan.setdefault("texts", []).append(json.loads(js))
    for js in a.add_sfx or []:
        plan.setdefault("sfx", []).append(json.loads(js))
    if a.clear:
        plan[a.clear] = [] if isinstance(plan.get(a.clear), list) else {}
    from .common import normalize_plan
    plan = normalize_plan(plan)
    write_json(p.plan, plan)
    out(plan)


def cmd_pacing(a):
    from .pacing import run_pacing
    out(run_pacing(Project(a.project), max_gap=a.max, apply=a.apply, jumpcut=a.jumpcut, scale=a.scale,
                   style=a.style, reset_auto=a.reset))


def cmd_render(a):
    from .render import run_render
    out(run_render(Project(a.project), draft=a.draft, captions=not a.no_captions, out=a.out))


def cmd_qa(a):
    from .qa import run_qa
    r = run_qa(Project(a.project), target=a.file)
    if a.json:
        out(r)
        return
    icon = {"pass": "✔", "warn": "⚠", "error": "✘"}
    lines = [f"{icon[c['status']]} {c['check']:<20} {c['detail']}" for c in r["checks"]]
    lines.append(f"\n{r['errors']} errors, {r['warnings']} warnings. Contact sheet: {r['contact_sheet']}")
    out("\n".join(lines))


def cmd_cover(a):
    from .render import candidate_frames, run_cover
    p = Project(a.project).require()
    if a.at is None:
        out({"candidates": candidate_frames(p, a.n)})
    else:
        out({"cover": run_cover(p, at=a.at, text=a.text or "")})


def cmd_audio(a):
    """Optional heavy voice isolation with Demucs (installed by setup.sh --full)."""
    from .common import ffmpeg, run
    p = Project(a.project).require()
    if not which("demucs") and not (OSE_HOME / "venv/bin/demucs").exists():
        raise OseError("demucs not installed: run scripts/setup.sh --full")
    wav = p.work / "voice_in.wav"
    ffmpeg(["-i", str(p.source), "-vn", "-ac", "2", "-ar", "44100", str(wav)])
    run(["demucs", "--two-stems", "vocals", "-o", str(p.work / "demucs"), str(wav)])
    vocals = next((p.work / "demucs").rglob("vocals.wav"))
    iso = p.raw / (p.source.stem + "_isolated.mp4")
    ffmpeg(["-i", str(p.source), "-i", str(vocals), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "256k", str(iso)])
    p.update_meta(source=f"raw/{iso.name}", original_source=str(p.source))
    out({"source": str(iso), "note": "project now uses the isolated voice; re-run transcribe/cut"})


def cmd_music(a):
    from . import music as m
    if a.mcmd == "add":
        out(m.add(a.source, tags=(a.tags or "").split(","), vibe=a.vibe or "", license=a.license, title=a.title))
    elif a.mcmd == "tag":
        out(m.tag(a.id, tags=a.tags.split(",") if a.tags else None, moods=a.moods.split(",") if a.moods else None,
                  vibe=a.vibe, license=a.license, title=a.title))
    elif a.mcmd == "suggest":
        out(m.suggest(a.query or "", mood=a.mood, energy=a.energy, min_duration=a.min_duration, n=a.n))
    elif a.mcmd == "list":
        out([{k: i.get(k) for k in ("id", "title", "bpm", "energy", "moods", "tags", "vibe", "license", "uses")}
             for i in m.load_index()])
    elif a.mcmd == "remove":
        m.remove(a.id, delete_file=a.delete)
        out({"removed": a.id})


def cmd_broll(a):
    from . import broll as b
    if a.bcmd == "ingest":
        out([{k: i[k] for k in ("id", "kind", "original_name", "duration", "thumbs")}
             for i in b.ingest(a.paths or None, source=a.source, project=a.project_name, copy=a.copy)])
    elif a.bcmd == "pending":
        out(b.pending())
    elif a.bcmd == "label":
        out(b.label(a.id, category=a.category, labels=(a.labels or "").split(","), description=a.desc or "",
                    sort=not a.no_sort))
    elif a.bcmd == "search":
        out(b.search(a.query, kind=a.kind, n=a.n, min_duration=a.min_duration, project=a.project_name))
    elif a.bcmd == "list":
        out([{k: i.get(k) for k in ("id", "kind", "status", "category", "labels", "duration", "uses")} for i in b.load_index()])


def cmd_hooks(a):
    from . import hooks as h
    if a.hcmd == "list":
        out(h.list_hooks(pattern=a.pattern, lang=a.lang, search=a.search, n=a.n))
    elif a.hcmd == "patterns":
        out(h.library()["patterns"])
    elif a.hcmd == "add":
        out(h.add_hook(pattern=a.pattern, en=a.en, pt=a.pt))


def cmd_perf(a):
    from . import hooks as h
    if a.pcmd == "add":
        fields = {k: getattr(a, k) for k in h.PERF_FIELDS if hasattr(a, k)}
        out(h.perf_add(**fields))
    else:
        out(h.perf_summary())


def cmd_auto(a):
    """Unattended draft: transcribe -> roughcut -> cut -> captions -> pacing -> render -> qa."""
    from .captions import run_captions
    from .cut import render_cut
    from .pacing import run_pacing
    from .qa import run_qa
    from .render import run_render
    from .roughcut import run_roughcut
    from .transcribe import run_transcribe
    p = Project(a.project).require()
    if not p.transcript.exists():
        run_transcribe(p, language=a.lang, model=a.model)
    run_roughcut(p, pace=a.pace)
    render_cut(p, reframe=a.reframe)
    run_captions(p)
    run_pacing(p, apply=True, reset_auto=True)
    r = run_render(p, draft=a.draft)
    q = run_qa(p, target=r["out"])
    out({"render": r, "errors": q["errors"], "warnings": q["warnings"], "contact_sheet": q["contact_sheet"]})


def cmd_paths(a):
    out({"home": str(OSE_HOME), "music": str(MUSIC_DIR), "broll": str(BROLL_DIR), "broll_inbox": str(BROLL_DIR / "_inbox"),
         "performance_csv": str(OSE_HOME / "performance.csv"), "skill_assets": str(ASSETS)})


# ------------------------------------------------------------------ parser

def build_parser():
    ap = argparse.ArgumentParser(prog="ose", description="one-shot-editing: talking-head footage -> finished short")
    sp = ap.add_subparsers(dest="cmd", required=True)

    def proj(name, fn, help_):
        s = sp.add_parser(name, help=help_)
        s.add_argument("project", help="project folder")
        s.set_defaults(fn=fn)
        return s

    s = sp.add_parser("doctor", help="check dependencies")
    s.set_defaults(fn=cmd_doctor)
    s = sp.add_parser("paths", help="show library/data locations")
    s.set_defaults(fn=cmd_paths)

    s = proj("init", cmd_init, "create a project from a raw video")
    s.add_argument("--video", required=True)
    s.add_argument("--lang", choices=["en", "pt", "es"], default=None, help="spoken language (default: auto)")
    s.add_argument("--platform", choices=["tiktok", "reels", "shorts"], default="tiktok")
    s.add_argument("--copy", action="store_true", help="copy the video instead of symlinking")

    s = proj("transcribe", cmd_transcribe, "word-level transcription")
    s.add_argument("--lang", default=None)
    s.add_argument("--model", default="small", help="tiny|base|small|medium|large-v3|turbo")
    s.add_argument("--engine", default="auto", choices=["auto", "faster-whisper", "whisperx"])
    s.add_argument("--no-fillers", action="store_true", help="don't prompt Whisper to keep um/uh")

    s = proj("text", cmd_text, "print the transcript as timestamped lines")
    s.add_argument("--cut", action="store_true", help="use the cut timeline (after `ose cut`)")

    s = proj("roughcut", cmd_roughcut, "build the EDL: remove fillers, pauses, stutters, retakes")
    s.add_argument("--pace", choices=["tight", "natural", "loose"], default="tight")
    s.add_argument("--aggressive", action="store_true", help="also remove soft fillers (like, tipo, né...)")
    s.add_argument("--prefer", choices=["last", "best"], default="last", help="which take wins on retakes")
    s.add_argument("--keep", help="decision ids to revert, e.g. r3,r7")
    s.add_argument("--cut", help="force-remove source ranges, e.g. 12.4-15.0,40-41.2")
    s.add_argument("--hook-range", help="copy a source range to the very start as a cold-open hook, e.g. 31.2-34.0")
    s.add_argument("--report", action="store_true", help="print every decision")

    s = proj("cut", cmd_cut, "render the EDL to work/cut.mp4 (9:16)")
    s.add_argument("--reframe", choices=["face", "center", "blur", "fill"], default="face")
    s.add_argument("--draft", action="store_true")

    s = proj("captions", cmd_captions, "build captions + hook/CTA cards (ASS)")
    s.add_argument("--style", choices=["bold-pop", "impact", "clean", "minimal"])
    s.add_argument("--words", type=int, help="max words per caption chunk (default 3)")
    s.add_argument("--none", action="store_true", help="cards only, no word captions (HyperFrames route)")

    s = proj("plan", cmd_plan, "show or edit work/plan.json")
    s.add_argument("--set", action="append", help="dotted.key=value (JSON values allowed), e.g. hook.text='...'")
    s.add_argument("--add-broll", action="append", help='{"asset":"<id|path>","start":3.2,"duration":2,"mode":"full|pip"}')
    s.add_argument("--add-zoom", action="append", help='{"start":4,"end":6,"scale":1.15,"style":"punch|smooth|slow"}')
    s.add_argument("--add-text", action="append", help='{"text":"...","start":1,"end":2.5,"style":"Title|Card"}')
    s.add_argument("--add-sfx", action="append", help='{"asset":"/path/whoosh.mp3","at":3.2,"volume_db":-8}')
    s.add_argument("--clear", choices=["broll", "zooms", "texts", "sfx", "music", "hook", "cta"])

    s = proj("pacing", cmd_pacing, "check (and fix) that something changes every N seconds")
    s.add_argument("--max", type=float, default=3.0)
    s.add_argument("--apply", action="store_true", help="add zooms into long static stretches")
    s.add_argument("--jumpcut", action="store_true", help="also punch-in on every other jump cut")
    s.add_argument("--scale", type=float, default=1.12)
    s.add_argument("--style", choices=["punch", "smooth", "slow"], default="smooth")
    s.add_argument("--reset", action="store_true", help="drop previously auto-added zooms first")

    s = proj("render", cmd_render, "final render to out/final.mp4")
    s.add_argument("--draft", action="store_true", help="fast low-quality preview to out/draft.mp4")
    s.add_argument("--no-captions", action="store_true", help="skip burned captions (e.g. for HyperFrames captions)")
    s.add_argument("--out")

    s = proj("qa", cmd_qa, "technical + editorial checks and a contact sheet")
    s.add_argument("--file", help="file to check (default out/final.mp4)")
    s.add_argument("--json", action="store_true")

    s = proj("cover", cmd_cover, "cover frame: list candidates, or render one with --at")
    s.add_argument("--at", type=float)
    s.add_argument("--text")
    s.add_argument("--n", type=int, default=6)

    s = proj("isolate-voice", cmd_audio, "Demucs voice isolation for noisy recordings (needs setup --full)")

    s = proj("auto", cmd_auto, "unattended draft of the whole pipeline")
    s.add_argument("--lang", default=None)
    s.add_argument("--model", default="small")
    s.add_argument("--pace", default="tight", choices=["tight", "natural", "loose"])
    s.add_argument("--reframe", default="face", choices=["face", "center", "blur", "fill"])
    s.add_argument("--draft", action="store_true")

    m = sp.add_parser("music", help="music library").add_subparsers(dest="mcmd", required=True)
    s = m.add_parser("add", help="add from URL (yt-dlp) or local file")
    s.add_argument("source")
    s.add_argument("--tags")
    s.add_argument("--vibe")
    s.add_argument("--title")
    s.add_argument("--license", default="unknown", choices=["unknown", "platform-only", "royalty-free", "owned", "cc-by"])
    s = m.add_parser("tag", help="set tags/moods/vibe/license")
    s.add_argument("id")
    s.add_argument("--tags")
    s.add_argument("--moods")
    s.add_argument("--vibe")
    s.add_argument("--title")
    s.add_argument("--license", choices=["unknown", "platform-only", "royalty-free", "owned", "cc-by"])
    s = m.add_parser("suggest", help="rank tracks for a topic/mood")
    s.add_argument("query", nargs="?")
    s.add_argument("--mood")
    s.add_argument("--energy", type=float)
    s.add_argument("--min-duration", type=float, default=0)
    s.add_argument("--n", type=int, default=5)
    m.add_parser("list")
    s = m.add_parser("remove")
    s.add_argument("id")
    s.add_argument("--delete", action="store_true")
    sp.choices["music"].set_defaults(fn=cmd_music)

    b = sp.add_parser("broll", help="b-roll library").add_subparsers(dest="bcmd", required=True)
    s = b.add_parser("ingest", help="ingest files/folders (default: the _inbox drop folder)")
    s.add_argument("paths", nargs="*")
    s.add_argument("--source", default="user", choices=["user", "web", "app", "screen"])
    s.add_argument("--project-name", dest="project_name")
    s.add_argument("--copy", action="store_true", help="copy instead of move when ingesting the inbox")
    b.add_parser("pending", help="unlabeled items with thumbnails to look at")
    s = b.add_parser("label", help="label + sort an item into a category folder")
    s.add_argument("id")
    s.add_argument("--category", required=True)
    s.add_argument("--labels")
    s.add_argument("--desc")
    s.add_argument("--no-sort", action="store_true")
    s = b.add_parser("search")
    s.add_argument("query")
    s.add_argument("--kind", choices=["video", "image"])
    s.add_argument("--n", type=int, default=8)
    s.add_argument("--min-duration", type=float, default=0)
    s.add_argument("--project-name", dest="project_name")
    b.add_parser("list")
    sp.choices["broll"].set_defaults(fn=cmd_broll)

    h = sp.add_parser("hooks", help="hook library").add_subparsers(dest="hcmd", required=True)
    s = h.add_parser("list")
    s.add_argument("--pattern")
    s.add_argument("--lang", default="en", choices=["en", "pt"])
    s.add_argument("--search")
    s.add_argument("--n", type=int, default=200)
    h.add_parser("patterns")
    s = h.add_parser("add")
    s.add_argument("--pattern", required=True)
    s.add_argument("--en")
    s.add_argument("--pt")
    sp.choices["hooks"].set_defaults(fn=cmd_hooks)

    pf = sp.add_parser("perf", help="performance log (feeds hook ranking)").add_subparsers(dest="pcmd", required=True)
    s = pf.add_parser("add")
    from .hooks import PERF_FIELDS
    for f in PERF_FIELDS:
        s.add_argument(f"--{f.replace('_', '-')}", dest=f)
    pf.add_parser("summary")
    sp.choices["perf"].set_defaults(fn=cmd_perf)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except OseError as e:
        print(f"[ose] error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
