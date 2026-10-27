"""Final render: zooms + b-roll overlays + captions/cards + voice cleanup + ducked music + SFX + loudness."""
from __future__ import annotations

from pathlib import Path

from . import broll as broll_lib
from . import music as music_lib
from . import sfx as sfx_lib
from .common import ASSETS, FPS, H, W, OseError, Project, ffmpeg, load_plan, log, probe, read_json, write_json

PLATFORMS = {
    # safe zones in px on a 1080x1920 canvas (UI overlays: caption/username at bottom, buttons on the right)
    "tiktok": {"max_s": 600, "lufs": -14, "safe": {"top": 160, "bottom": 480, "left": 60, "right": 140}},
    "reels": {"max_s": 180, "lufs": -14, "safe": {"top": 220, "bottom": 420, "left": 60, "right": 120}},
    "shorts": {"max_s": 180, "lufs": -14, "safe": {"top": 160, "bottom": 400, "left": 60, "right": 120}},
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


def build_command(project: Project, plan: dict, *, out: Path, draft=False, captions=True, platform="tiktok"):
    cut_info = probe(project.cut)
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
        cover = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
        if asset["kind"] == "image":
            inputs.append(["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", asset["path"]])
            push = f"(1+0.06*t/{d:.3f})"  # gentle Ken Burns push-in on stills
            if mode == "full":
                src = (f"[{idx}:v]{cover},scale=w='trunc({W}*{push}/2)*2':h='trunc({H}*{push}/2)*2':eval=frame,"
                       f"crop={W}:{H}")
            else:
                src = f"[{idx}:v]scale=900:-2"
        else:
            sin = float(b.get("source_in", 0))
            inputs.append(["-ss", f"{sin:.3f}", "-t", f"{d + 0.1:.3f}", "-i", asset["path"]])
            src = f"[{idx}:v]fps={FPS}," + (cover if mode == "full" else "scale=900:-2")
        if mode == "pip":
            src += ",pad=iw+12:ih+12:6:6:white"
            pos = "x=(W-w)/2:y=230"
        else:
            pos = "x=0:y=0"
        fg.append(f"{src},setsar=1,format=yuva420p,setpts=PTS-STARTPTS+{start:.3f}/TB[b{k}]")
        fg.append(f"[{last}][b{k}]overlay={pos}:enable='between(t,{start:.3f},{start + d:.3f})':eof_action=pass[v{k + 1}]")
        last = f"v{k + 1}"
        if asset.get("id"):
            used_broll.append(asset["id"])
    if captions and project.captions_ass.exists():
        fonts = _esc(ASSETS / "fonts")
        fg.append(f"[{last}]ass=filename=captions.ass:fontsdir='{fonts}'[vass]")
        last = "vass"
    fg.append(f"[{last}]fps={FPS},format=yuv420p[vout]")

    # --- audio
    audio = plan.get("audio", {})
    voice = "[0:a]aresample=48000"
    if audio.get("clean", True):
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
        chain = (f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS,"
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
        fg.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume={float(s.get('volume_db', -8))}dB,"
                  f"adelay={ms}|{ms}[sfx{k}]")
        mix.append(f"[sfx{k}]")
    lufs = PLATFORMS.get(platform, PLATFORMS["tiktok"])["lufs"]
    fg.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0,"
              f"loudnorm=I={lufs}:TP=-1.5:LRA=11,aresample=48000[aout]")

    script = project.work / "render_graph.txt"
    script.write_text(";\n".join(fg))
    args = [a for inp in inputs for a in inp]
    args += ["-filter_complex_script", script.name, "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "veryfast" if draft else "medium", "-crf", "26" if draft else "19",
             "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{dur:.3f}", str(out)]
    return args, used_broll, music_id


def run_render(project: Project, *, draft=False, captions=True, out=None, platform=None) -> dict:
    project.require()
    if not project.cut.exists():
        raise OseError("no cut yet: run `ose cut` first")
    if not draft and project.meta.get("cut_draft", False):
        from .cut import render_cut
        log("rebuilding draft rough cut at full quality before final render")
        render_cut(project, reframe=project.meta.get("cut_reframe", "face"), draft=False)
    plan = load_plan(project)
    platform = platform or plan.get("platform", "tiktok")
    if captions and project.cut_words.exists():
        from .captions import run_captions
        run_captions(project, show_captions=(plan.get("captions") or {}).get("enabled", True))  # cards follow plan edits
    out = Path(out) if out else (project.out / ("draft.mp4" if draft else "final.mp4"))
    out.parent.mkdir(parents=True, exist_ok=True)
    args, used_broll, music_id = build_command(project, plan, out=out.resolve(), draft=draft, captions=captions,
                                               platform=platform)
    log(f"rendering {'draft' if draft else 'final'} -> {out}")
    ffmpeg(args, cwd=project.work)
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
        plan = {"platform": "tiktok", "hook": {}, "captions": {"style": "bold-pop", "words_per_chunk": 3},
                "music": {}, "broll": [], "zooms": [], "texts": [], "sfx": [], "cta": {}, "audio": {"clean": True}}
        write_json(project.plan, plan)
    return plan

