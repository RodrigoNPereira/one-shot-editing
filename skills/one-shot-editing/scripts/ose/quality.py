"""Explicit source-quality and social-delivery contracts."""
from __future__ import annotations

from fractions import Fraction
import json

from .common import H, W, OseError, read_json, run, write_json

PIXEL_FORMATS = {"yuv420p", "yuv422p", "yuv444p", "yuv420p10le", "yuv422p10le", "yuv444p10le"}


def settings(info, plan, *, reframe="face"):
    profile = plan.get("output", {}).get("profile", "source")
    if info.get("color_transfer") in {"smpte2084", "arib-std-b67"}:
        raise OseError("HDR input requires a color-managed workflow; refusing to discard HDR metadata or tone-map silently")
    if any("DOVI" in item.get("side_data_type", "").upper() for item in info.get("video_side_data", [])):
        raise OseError("Dolby Vision input requires a color-managed workflow")
    if profile == "social":
        return {"width": W, "height": H, "fps": "30/1", "pix_fmt": "yuv420p",
                "profile": profile, "sample_rate": 48000, "color": colors(info)}
    pixel = info.get("pix_fmt", "yuv420p")
    if info.get("sample_aspect_ratio", "1:1") not in ("1:1", "0:1", None):
        raise OseError("source-quality requires square pixels; choose output.profile=social for explicit resampling")
    if pixel not in PIXEL_FORMATS:
        raise OseError(f"source-quality export does not support {pixel}; use a supported YUV source or explicitly select output.profile=social")
    width, height = info["width"], info["height"]
    if width % 2 or height % 2:
        raise OseError("source-quality export requires even dimensions; use an explicitly resized source")
    if width / height > W / H + 0.02:
        width = int(height * W / H) // 2 * 2
    rate = info.get("fps_ratio") or str(info.get("fps", 30))
    if Fraction(rate) <= 0:
        raise OseError("source frame rate is unavailable")
    nominal = info.get("nominal_fps_ratio")
    if nominal and Fraction(nominal) > 0 and Fraction(nominal) != Fraction(rate):
        raise OseError("variable/ambiguous frame rate: source-quality requires a verified CFR source; "
                       "choose output.profile=social to explicitly convert to 30 fps")
    return {"width": width, "height": height, "fps": str(Fraction(rate)),
            "pix_fmt": pixel, "profile": profile, "sample_rate": info.get("sample_rate") or 48000,
            "color": colors(info)}


def colors(info):
    return {key: info[key] for key in ("color_range", "color_space", "color_transfer", "color_primaries")
            if info.get(key) not in (None, "unknown", "unspecified", "reserved")}


def color_args(config):
    flags = {"color_range": "-color_range", "color_space": "-colorspace",
             "color_transfer": "-color_trc", "color_primaries": "-color_primaries"}
    return [value for key, val in config.get("color", {}).items() for value in (flags[key], val)]


def video_args(config, draft=False):
    if draft:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-pix_fmt", config["pix_fmt"]]
    quantizer = ["-qp", "0"] if config["profile"] == "source" else ["-crf", "16"]
    return ["-c:v", "libx264", "-preset", "medium", *quantizer,
            "-pix_fmt", config["pix_fmt"], *color_args(config)]


def verify_cfr(project, info, source_sha256):
    record = project.work / "frame_timing.json"
    cached = read_json(record, {})
    if cached.get("source_sha256") == source_sha256 and cached.get("verified_cfr"):
        return
    result = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                  "frame=best_effort_timestamp_time", "-of", "json", str(project.source)], capture=True)
    frames = json.loads(result.stdout).get("frames", [])
    if not frames or any("best_effort_timestamp_time" not in frame for frame in frames):
        raise OseError("cannot verify source frame timing; use an explicit social delivery conversion")
    times = [float(frame["best_effort_timestamp_time"]) for frame in frames]
    interval = 1 / float(Fraction(info["fps_ratio"]))
    tick = float(Fraction(info.get("time_base") or "1/1000000"))
    tolerance = min(interval / 4, tick * 1.1 + 1e-6)
    if any(abs((b - a) - interval) > tolerance for a, b in zip(times, times[1:])):
        raise OseError("variable frame timestamps detected; source-quality will not silently convert VFR to CFR. "
                       "Choose output.profile=social for explicit conversion")
    write_json(record, {"source_sha256": source_sha256, "verified_cfr": True, "frames": len(times)})
