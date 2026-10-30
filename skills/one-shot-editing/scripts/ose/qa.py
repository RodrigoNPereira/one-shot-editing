"""QA: technical checks + editorial checks + contact sheet for the agent to eyeball."""
from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path

from . import music as music_lib
from .captions import STYLES
from .common import FPS, H, W, OseError, Project, load_plan, ffmpeg, probe, read_json, run, write_json
from .provenance import check_cut, check_plan_revision, digest, render_assets, revision
from .pacing import analyse as pacing_analyse
from .render import PLATFORMS, PLATFORM_SOURCES


def measure(path) -> dict:
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-xerror", "-i", str(path),
               "-vf", "blackdetect=d=0.4:pix_th=0.08", "-af", "ebur128=peak=true,silencedetect=n=-45dB:d=1.2",
               "-f", "null", "-"], capture=True, check=False)
    err = res.stderr or ""
    if res.returncode:
        raise OseError(f"QA measurement failed ({res.returncode}): {err[-1500:]}")
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    if not lufs or not peak:
        raise OseError("QA measurement incomplete: no usable loudness/true-peak summary")
    blacks = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", err)]
    silences = re.findall(r"silence_start: ([\d.]+)", err)
    return {"lufs": float(lufs.group(1)) if lufs else None,
            "true_peak_db": float(peak.group(1)) if peak and peak.group(1) != "-inf" else None,
            "black_segments": blacks, "long_silences_at": [float(s) for s in silences]}


def contact_sheet(path, out, n=12) -> str:
    dur = probe(path)["duration"]
    cols = 6
    rows = (n + cols - 1) // cols
    ffmpeg(["-i", str(path), "-vf", f"fps={n / max(dur, 0.1):.4f},scale=270:-2,tile={cols}x{rows}:padding=6:color=black",
            "-frames:v", "1", "-q:v", "3", str(out)])
    return str(out)


def run_qa(project: Project, *, target=None) -> dict:
    project.require()
    path = Path(target) if target else project.final
    plan = load_plan(project)
    platform = plan.get("platform", "tiktok")
    pf = PLATFORMS.get(platform, PLATFORMS["tiktok"])
    info = probe(path)
    checks = []
    rendered = read_json(path.with_suffix(path.suffix + ".provenance.json"), {})

    def check(name, ok, detail, level="error"):
        checks.append({"check": name, "status": "pass" if ok else level, "detail": detail})

    try:
        check_cut(project)
        current = check_plan_revision(project, plan)
        valid = (rendered.get("file_sha256") == digest(path) and
                 rendered.get("cut_sha256") == digest(project.cut) and
                 rendered.get("plan_sha256") == revision(plan) and rendered.get("edl_revision") == current and
                 rendered.get("assets") == render_assets(plan))
        if rendered.get("captions"):
            valid = valid and rendered.get("ass_sha256") == digest(project.captions_ass)
        check("provenance", valid, "Output must match current source, cut, plan and file bytes")
    except (OseError, FileNotFoundError) as error:
        check("provenance", False, str(error))
    try:
        m = measure(path)
    except OseError as error:
        m = None
        check("measurements", False, str(error))

    config = rendered.get("quality", {"width": W, "height": H, "fps": str(FPS)})
    check("resolution", (info.get("width"), info.get("height")) == (config["width"], config["height"]),
          f"{info.get('width')}x{info.get('height')} ({config.get('profile', 'legacy')} profile)")
    check("fps", abs(info.get("fps", 0) - float(Fraction(config["fps"]))) < 0.01, f"{info.get('fps', 0):.4f}")
    if config.get("profile") == "source":
        check("pixel_format", info.get("pix_fmt") == config["pix_fmt"], f"{info.get('pix_fmt')} vs {config['pix_fmt']}")
        check("color_metadata", all(info.get(key) == value for key, value in config.get("color", {}).items()),
              f"expected {config.get('color', {})}")
        check("quality_profile", not rendered.get("draft", True),
              "Source profile uses lossless encoding of the edited image; crop/zoom/overlays alter source pixels", "warn")
    else:
        check("quality_profile", False, "Social delivery explicitly resizes/re-encodes; not a source-quality master", "warn")
    check("audio", info["audio"], "audio stream present" if info["audio"] else "no audio")
    check("duration", info["duration"] <= pf["max_s"], f"{info['duration']:.1f}s (max {pf['max_s']}s on {platform})")
    check("duration_sweet_spot", 12 <= info["duration"] <= 75, f"{info['duration']:.1f}s (editorial review heuristic, not retention evidence)", "warn")
    if m is not None:
        target_lufs = plan.get("audio", {}).get("lufs", pf["lufs"])
        if plan.get("audio", {}).get("normalization") != "off":
            check("loudness", m["lufs"] is not None and abs(m["lufs"] - target_lufs) <= 1.5,
                  f"{m['lufs']} LUFS (target {target_lufs})", "warn")
        check("true_peak", m["true_peak_db"] is not None and m["true_peak_db"] <= -0.5,
              f"{m['true_peak_db']} dBFS", "warn")
        check("black_frames", not m["black_segments"], f"{m['black_segments']}" if m["black_segments"] else "none")
        check("dead_air", not m["long_silences_at"],
              f"silences >1.2s at {m['long_silences_at']}" if m["long_silences_at"] else "none", "warn")

    # editorial
    try:
        words = read_json(project.cut_words)["words"]
        if not words:
            raise OseError("cut transcript has no words")
        first = words[0]["start"]
        check("hook_starts_fast", first <= 0.4, f"first word at {first:.2f}s (should be <0.4s)", "warn")
    except (OseError, ValueError, KeyError, TypeError) as error:
        check("hook_starts_fast", False, f"Cannot check cut transcript: {error}")
    try:
        edl = read_json(project.edl)
        segs = edl["segments"]
        if not segs:
            raise OseError("EDL has no segments")
        pace = pacing_analyse(plan, segs, info["duration"])
        check("pacing", pace["ok"], f"max static {pace['max_static']}s, {pace['changes_per_10s']} changes/10s; gaps: "
              f"{[(g['start'], g['end']) for g in pace['gaps']]}", "warn")
        pending = edl.get("review", [])
        check("retake_review", not pending, f"{len(pending)} potentially meaning-changing take pairs preserved; review edl.json", "warn")
    except (OseError, ValueError, KeyError, TypeError) as error:
        check("pacing", False, f"Cannot check EDL: {error}")
    caps = read_json(project.work / "captions.json", []) if rendered.get("captions", True) else []
    if caps:
        long_ = [c["text"] for c in caps if len(c["text"]) > 24]
        short = [c["text"] for c in caps if c["end"] - c["start"] < 0.18]
        check("caption_length", not long_, f"{len(long_)} chunks >24 chars {long_[:3]}", "warn")
        check("caption_flash", not short, f"{len(short)} chunks <0.18s {short[:3]}", "warn")
        style = STYLES.get(plan.get("captions", {}).get("style", "bold-pop"), STYLES["bold-pop"])
        check("caption_safe_zone", style["margin_v"] >= pf["safe"]["bottom"],
              f"caption bottom margin {style['margin_v']}px vs {platform} UI {pf['safe']['bottom']}px")
    layout = None
    if rendered.get("captions") and project.captions_ass.exists():
        from .visual import inspect_overlays
        try:
            layout = inspect_overlays(project, path, pf["safe"])
            check("rendered_safe_zones", not layout["outside_safe_zone"], str(layout["outside_safe_zone"]))
            check("overlay_collisions", not layout["overlay_collisions"], str(layout["overlay_collisions"]), "warn")
            check("face_occlusion", not layout["face_overlaps"], str(layout["face_overlaps"]), "warn")
        except OseError as error:
            check("visual_measurement", False, str(error))
    from .review import approved
    try:
        check("cut_approval", approved(project, "cut"), "Revision-bound editorial cut approval", "warn")
        check("final_approval", approved(project, "final", path), "Human review of this exact output", "warn")
    except (OseError, KeyError) as error:
        check("editorial_approval", False, str(error), "warn")
    if not (plan.get("hook") or {}).get("text"):
        check("hook_defined", False, "plan.hook.text is empty: pick a hook (references/hooks.md)", "warn")
    if not (plan.get("cta") or {}).get("text"):
        check("cta_defined", False, "plan.cta.text is empty: add a call to action (references/cta.md)", "warn")
    mus = plan.get("music") or {}
    if mus.get("track"):
        try:
            lic = music_lib.resolve(mus["track"]).get("license", "unknown")
        except Exception:  # noqa: BLE001
            lic = "unknown"
        if lic == "cc-by":
            check("music_license", False, "license=cc-by: credit the artist in the post caption", "warn")
        else:
            check("music_license", lic in ("royalty-free", "owned"),
                  f"license={lic}" + ("" if lic in ("royalty-free", "owned") else
                  ": for trending/copyrighted songs, publish without music and add the track from the platform's "
                  "in-app sound library (keeps the trend + avoids muting/claims)"), "warn")
        if platform == "shorts" and info["duration"] > 60:
            check("shorts_music_claim", False,
                  "Shorts over 60s with active Content ID claims are blocked; verify rights/claims independently", "warn")

    sheet = contact_sheet(path, project.out / "contact_sheet.jpg")
    result = {"file": str(path), "duration": round(info["duration"], 2), "measure": m, "checks": checks,
              "visual_layout": layout, "platform_sources": PLATFORM_SOURCES,
              "contact_sheet": sheet,
              "errors": sum(c["status"] == "error" for c in checks), "warnings": sum(c["status"] == "warn" for c in checks)}
    write_json(project.out / "qa.json", result)
    return result
