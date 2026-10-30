"""Optional standards-based editing interchange."""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from .common import OseError, ffmpeg, load_edl, load_plan, probe
from .provenance import check_cut, check_plan_revision, edl_revision


def export_browser(project, out=None):
    record = check_cut(project, allow_draft=False)
    destination = Path(out) if out else project.out / "browser-cut.mp4"
    destination.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(["-i", project.cut, "-c:v", "libx264", "-crf", "16", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-r", record["inputs"]["quality"]["fps"],
            "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", destination])
    return {"file": str(destination), "words": str(project.cut_words),
            "note": "Explicit browser delivery conversion (8-bit H.264/AAC); lossless cut.mkv remains untouched."}


def export_otio(project, out=None):
    try:
        import opentimelineio as otio
    except ImportError as error:
        raise OseError("OTIO export needs the interchange extra; run setup.sh --extra interchange") from error
    edl = load_edl(project)
    plan = load_plan(project)
    check_plan_revision(project, plan)
    info = probe(project.source)
    fps = float(Fraction(info.get("fps_ratio") or str(info["fps"])))
    timeline = otio.schema.Timeline(name=project.root.name)
    reference = otio.schema.ExternalReference(
        target_url=project.source.resolve().as_uri(),
        available_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0, fps),
                                               otio.opentime.RationalTime(round(info["duration"] * fps), fps)))
    for kind in (["Video", "Audio"] if info["audio"] else ["Video"]):
        track = otio.schema.Track(name=kind, kind=kind)
        for i, segment in enumerate(edl["segments"]):
            start = round(segment["in"] * fps)
            length = max(1, round((segment["out"] - segment["in"]) * fps))
            track.append(otio.schema.Clip(
                name=f"take-{i + 1}", media_reference=reference.deepcopy(),
                source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(start, fps),
                                                    otio.opentime.RationalTime(length, fps))))
        timeline.tracks.append(track)
    timeline.metadata["one_shot_editing"] = {
        "edl_revision": edl_revision(project), "plan": plan,
        "note": "Source cuts/audio are editable. Crop, captions, B-roll and effects are metadata only, not NLE effects.",
    }
    destination = Path(out) if out else project.out / "edit.otio"
    destination.parent.mkdir(parents=True, exist_ok=True)
    otio.adapters.write_to_file(timeline, str(destination), adapter_name="otio_json")
    return {"file": str(destination), "segments": len(edl["segments"]), "effects": "metadata-only"}
