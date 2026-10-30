"""Final render: zooms + b-roll overlays + captions/cards + voice cleanup + ducked music + SFX + loudness."""
from __future__ import annotations

from pathlib import Path
import json
import math
import re

from . import broll as broll_lib
from . import music as music_lib
from . import sfx as sfx_lib
from .common import ASSETS, OseError, Project, ffmpeg, load_plan, log, probe, read_json, validate_plan, write_json
from .provenance import check_cut, check_plan_revision, digest, render_assets, revision
from .quality import video_args

PLATFORMS = {
    # safe zones in px on a 1080x1920 canvas (UI overlays: caption/username at bottom, buttons on the right)
    "tiktok": {"max_s": 600, "lufs": -14, "safe": {"top": 160, "bottom": 480, "left": 60, "right": 140}},
    "reels": {"max_s": 180, "lufs": -14, "safe": {"top": 220, "bottom": 420, "left": 60, "right": 120}},
    "shorts": {"max_s": 180, "lufs": -14, "safe": {"top": 160, "bottom": 400, "left": 60, "right": 120}},
}
PLATFORM_SOURCES = {
    "checked": "2026-10-30",
    "shorts": "https://support.google.com/youtube/answer/15424877",
    "reels": "https://help.instagram.com/",
    "tiktok": "https://support.tiktok.com/en/using-tiktok/creating-videos",
    "note": "Duration values are conservative delivery presets; safe insets are editorial estimates, not platform guarantees.",
}


def zoom_expr(zooms):
    terms = []
    for z in zooms:
        a, b, s = float(z["start"]), float(z["end"]), float(z.get("scale", 1.12)) - 1
        style = z.get("style", "smooth")
        if style == "punch":
            terms.append(f"{s}*between(t,{a:.3f},{b:.3f})")
        elif style == "slow":
            terms.append(f"{s}*between(t,{a:.3f},{b:.3f})*(t-{a:.3f})/{max(b - a, 0.01):.3f}")
        else:  # smooth: ease in over 0.3s, hold, hard cut out
            terms.append(f"{s}*between(t,{a:.3f},{b:.3f})*min(1,(t-{a:.3f})/0.3)")
    return "1+" + "+".join(terms) if terms else "1"


def _esc(path: str) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_command(project: Project, plan: dict, *, out: Path, draft=False, captions=True, platform="tiktok",
                  measurements=None, analyze=False):
    cut_info = probe(project.cut)
    W, H = cut_info["width"], cut_info["height"]
    config = read_json(project.work / "cut.provenance.json")["inputs"]["quality"]
    FPS = config["fps"]
    dur = cut_info["duration"]
    inputs = [["-i", str(project.cut)]]
    fg = []
    # --- video: zooms (faces sit in the upper-middle, so zoom toward y=40%)
    zooms = plan.get("zooms", [])
    if zooms:
        e = zoom_expr(zooms)
        fg.append(f"[0:v]scale=w='trunc({W}*({e})/2)*2':h='trunc({H}*({e})/2)*2':eval=frame,"
                  f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*0.4,setsar=1[v0]")
    else:
        fg.append("[0:v]setsar=1[v0]")
    last = "v0"
    used_broll = []
    for k, b in enumerate(sorted(plan.get("broll", []), key=lambda x: x["start"])):
        asset = broll_lib.resolve(b["asset"])
        idx = len(inputs)
        start, d = float(b["start"]), float(b["duration"])
        if start >= dur:
            continue
        d = min(d, dur - start)
        mode = b.get("mode", "full")
        cover = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
        pip_width = int(W * 0.83) // 2 * 2
        if asset["kind"] == "image":
            inputs.append(["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", asset["path"]])
            push = f"(1+0.06*t/{d:.3f})"  # gentle Ken Burns push-in on stills
            if mode == "full":
                src = (f"[{idx}:v]{cover},scale=w='trunc({W}*{push}/2)*2':h='trunc({H}*{push}/2)*2':eval=frame,"
                       f"crop={W}:{H}")
            else:
                src = f"[{idx}:v]scale={pip_width}:-2:flags=lanczos"
        else:
            sin = float(b.get("source_in", 0))
            inputs.append(["-ss", f"{sin:.3f}", "-t", f"{d + 0.1:.3f}", "-i", asset["path"]])
            src = f"[{idx}:v]fps={FPS}," + (cover if mode == "full" else f"scale={pip_width}:-2:flags=lanczos")
        if mode == "pip":
            border = max(2, round(W / 180))
            src += f",pad=iw+{border * 2}:ih+{border * 2}:{border}:{border}:white"
            pos = f"x=(W-w)/2:y={round(H * 230 / 1920)}"
        else:
            pos = "x=0:y=0"
        fg.append(f"{src},setsar=1,setpts=PTS-STARTPTS+{start:.3f}/TB[b{k}]")
        fg.append(f"[{last}][b{k}]overlay={pos}:format=auto:enable='between(t,{start:.3f},{start + d:.3f})':eof_action=pass,"
                  f"format={config['pix_fmt']}[v{k + 1}]")
        last = f"v{k + 1}"
        if asset.get("id"):
            used_broll.append(asset["id"])
    if captions and project.captions_ass.exists():
        fonts = _esc(ASSETS / "fonts")
        fg.append(f"[{last}]ass=filename=captions.ass:fontsdir='{fonts}'[vass]")
        last = "vass"
    fg.append(f"[{last}]fps={FPS},format={config['pix_fmt']}[vout]")

    # --- audio
    audio_start = len(fg)
    audio = plan.get("audio", {})
    sample_rate = config["sample_rate"]
    voice = f"[0:a]aresample={sample_rate}"
    if audio.get("clean", False):
        voice += ",highpass=f=75,afftdn=nf=-28,acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=2"
    mix = []
    mus = plan.get("music") or {}
    music_id = None
    if mus.get("track"):
        track = music_lib.resolve(mus["track"])
        music_id = track.get("id")
        idx = len(inputs)
        inputs.append(["-stream_loop", "-1", "-ss", f"{float(mus.get('start_offset', 0)):.2f}", "-i", track["path"]])
        vol = float(mus.get("volume_db", -16))
        fo = min(1.5, dur / 4)
        chain = (f"[{idx}:a]aresample={sample_rate},aformat=channel_layouts=stereo,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
                 f"volume={vol}dB,afade=t=in:d=0.4,afade=t=out:st={dur - fo:.3f}:d={fo:.3f}")
        if mus.get("duck", True):
            fg.append(f"{voice},asplit=2[voice][vsc]")
            fg.append(f"{chain}[mraw]")
            fg.append("[mraw][vsc]sidechaincompress=threshold=0.015:ratio=8:attack=20:release=400:makeup=1[mus]")
        else:
            fg.append(f"{voice}[voice]")
            fg.append(f"{chain}[mus]")
        mix = ["[voice]", "[mus]"]
    else:
        fg.append(f"{voice}[voice]")
        mix = ["[voice]"]
    for k, s in enumerate(plan.get("sfx", [])):
        idx = len(inputs)
        inputs.append(["-i", str(sfx_lib.resolve(s["asset"]))])
        ms = int(float(s["at"]) * 1000)
        fg.append(f"[{idx}:a]aresample={sample_rate},aformat=channel_layouts=stereo,volume={float(s.get('volume_db', -8))}dB,"
                  f"adelay={ms}|{ms}[sfx{k}]")
        mix.append(f"[sfx{k}]")
    lufs = audio.get("lufs", PLATFORMS[platform]["lufs"])
    normalization = f"loudnorm=I={lufs}:TP={audio.get('true_peak', -1.5)}:LRA={audio.get('lra', 11)}"
    if measurements:
        normalization += (f":measured_I={measurements['input_i']}:measured_TP={measurements['input_tp']}"
                          f":measured_LRA={measurements['input_lra']}:measured_thresh={measurements['input_thresh']}"
                          f":offset={measurements['target_offset']}:linear=true")
    if analyze:
        normalization += ":print_format=json"
    if audio.get("normalization", "two-pass") == "off":
        normalization = "anull"
    fg.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,"
              f"{normalization},aresample={sample_rate}[aout]")

    script = project.work / ("audio_analysis_graph.txt" if analyze else "render_graph.txt")
    script.write_text(";\n".join(fg[audio_start:] if analyze else fg))
    args = [a for inp in inputs for a in inp]
    if analyze:
        return [*args, "-filter_complex_script", script.name, "-map", "[aout]", "-t", f"{dur:.9f}",
                "-f", "null", "-"], [], None
    audio_codec = (["-c:a", "alac"] if config["profile"] == "source" and not draft else
                   ["-c:a", "aac", "-b:a", "256k"])
    args += ["-filter_complex_script", script.name, "-map", "[vout]", "-map", "[aout]",
             *video_args(config, draft), "-r", str(FPS),
             *audio_codec, "-ar", str(sample_rate), "-movflags", "+faststart", "-t", f"{dur:.9f}", str(out)]
    return args, used_broll, music_id


def parse_loudness(stderr):
    blocks = re.findall(r'\{\s*"input_i".*?\}', stderr, re.S)
    if not blocks:
        raise OseError("audio analysis did not return loudness measurements")
    result = json.loads(blocks[-1])
    keys = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    if not all(key in result and math.isfinite(float(result[key])) for key in keys):
        raise OseError("audio analysis is non-finite (possibly silent input); choose audio.normalization=off explicitly")
    return {key: float(result[key]) for key in keys}


def run_render(project: Project, *, draft=False, captions=True, out=None, platform=None) -> dict:
    project.require()
    if not project.cut.exists():
        raise OseError("no cut yet: run `ose cut` first")
    record = check_cut(project)
    if not draft and project.meta.get("cut_draft", False):
        from .cut import render_cut
        log("rebuilding draft rough cut at full quality before final render")
        render_cut(project, reframe=project.meta.get("cut_reframe", "face"), draft=False)
    plan = load_plan(project)
    check_plan_revision(project, plan)
    validate_plan(plan, probe(project.cut)["duration"], assets=True)
    platform = platform or plan.get("platform", "tiktok")
    if captions and project.cut_words.exists():
        from .captions import run_captions
        run_captions(project, show_captions=(plan.get("captions") or {}).get("enabled", True))  # cards follow plan edits
    plan = load_plan(project)
    initial_plan = revision(plan)
    initial_assets = render_assets(plan)
    out = Path(out) if out else (project.out / ("draft.mp4" if draft else "final.mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    measurements = None
    if not draft and plan.get("audio", {}).get("normalization", "two-pass") == "two-pass":
        args, _, _ = build_command(project, plan, out=out.resolve(), platform=platform, analyze=True)
        measurements = parse_loudness(ffmpeg(args, cwd=project.work, capture_stderr=True).stderr)
        write_json(project.work / "audio_measurements.json", measurements)
    pending = out.with_name(out.stem + ".pending" + out.suffix)
    args, used_broll, music_id = build_command(project, plan, out=pending.resolve(), draft=draft, captions=captions,
                                               platform=platform, measurements=measurements)
    log(f"rendering {'draft' if draft else 'final'} -> {out}")
    try:
        ffmpeg(args, cwd=project.work)
        check_cut(project, allow_draft=draft)
        if revision(load_plan(project)) != initial_plan:
            raise OseError("plan changed during render; retry after changes finish")
        if render_assets(plan) != initial_assets:
            raise OseError("render assets changed during render; retry after changes finish")
        pending.replace(out)
    finally:
        pending.unlink(missing_ok=True)
    # Caption generation persists the selected settings, so fingerprint the resulting plan.
    write_json(out.with_suffix(out.suffix + ".provenance.json"),
               {"file_sha256": digest(out), "cut_sha256": digest(project.cut),
                "plan_sha256": initial_plan, "edl_revision": check_plan_revision(project, plan),
                "draft": draft, "captions": captions, "quality": record["inputs"]["quality"],
                "assets": initial_assets, "ass_sha256": digest(project.captions_ass) if captions else None,
                "audio_measurements": measurements})
    if not draft:
        for b in used_broll:
            broll_lib.mark_used(b)
        if music_id:
            music_lib.mark_used(music_id)
        project.update_meta(rendered=str(out))
    info = probe(out)
    return {"out": str(out), "duration": round(info["duration"], 2), "size": f"{info.get('width')}x{info.get('height')}"}


def run_cover(project: Project, *, at: float, text: str = "", out=None) -> str:
    """Cover/thumbnail: a frame from the final video with an optional big title."""
    project.require()
    src = project.cut if text else (project.final if project.final.exists() else project.cut)
    out = Path(out) if out else project.out / "cover.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = "null"
    if text:
        ass = project.work / "cover.ass"
        from .captions import _header
        safe = text.replace("{", "(").replace("}", ")").upper()
        ass.write_text(_header("bold-pop") + f"\nDialogue: 1,0:00:00.00,0:00:10.00,Title,,0,0,0,,{{\\fs180\\bord10}}{safe}\n",
                       encoding="utf-8")
        vf = f"ass=filename=cover.ass:fontsdir='{_esc(ASSETS / 'fonts')}'"
    ffmpeg(["-ss", f"{at:.2f}", "-i", str(src.resolve()), "-frames:v", "1", "-vf", vf, "-q:v", "2", str(out.resolve())],
           cwd=project.work)
    return str(out)


def candidate_frames(project: Project, n=6) -> list[str]:
    """Extract n visually distinct candidate frames for the cover (agent views and picks one)."""
    src = project.final if project.final.exists() else project.cut
    dur = probe(src)["duration"]
    d = project.out / "cover_candidates"
    d.mkdir(parents=True, exist_ok=True)
    outs = []
    for i in range(n):
        t = dur * (i + 0.5) / n
        p = d / f"t{t:06.2f}.jpg"
        ffmpeg(["-ss", f"{t:.2f}", "-i", str(src), "-vf", "thumbnail=15,scale=540:-2", "-frames:v", "1", str(p)])
        outs.append(str(p))
    return outs


def ensure_plan(project: Project) -> dict:
    plan = read_json(project.plan, {})
    if not plan:
        plan = {"schema_version": 1, "platform": "tiktok", "output": {"profile": "source"},
                "hook": {}, "captions": {"style": "bold-pop", "words_per_chunk": 3},
                "music": {}, "broll": [], "zooms": [], "texts": [], "sfx": [], "cta": {},
                "audio": {"clean": False, "normalization": "two-pass"}}
        write_json(project.plan, plan)
    return plan
