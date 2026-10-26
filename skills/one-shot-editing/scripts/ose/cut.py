"""Render the rough cut (EDL) into work/cut.mp4 on a 9:16 canvas, with optional face-tracked reframe."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from .common import FPS, H, W, OseError, Project, ffmpeg, log, probe, read_json, remap_words, write_json


def quantize_segments(segments, fps=FPS):
    """Snap segment durations to whole frames so audio/video never drift across many cuts."""
    out = []
    for s in segments:
        frames = max(1, round((s["out"] - s["in"]) * fps))
        out.append({**s, "out": round(s["in"] + frames / fps, 4)})
    return out


def face_centers(src, segments, sample_every=0.5):
    """Median horizontal face center (0..1) per segment using OpenCV's bundled Haar cascade."""
    import cv2

    if not hasattr(cv2, "CascadeClassifier"):  # OpenCV 5 moved Haar cascades out of the main package
        from .common import log
        log("face tracking unavailable (needs opencv<5); using center crop")
        return [0.5] * len(segments)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(src))
    centers = []
    for s in segments:
        xs, t = [], s["in"]
        while t < s["out"]:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if ok:
                small = cv2.resize(frame, (640, int(640 * frame.shape[0] / frame.shape[1])))
                gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
                faces = cascade.detectMultiScale(gray, 1.15, 5, minSize=(40, 40))
                if len(faces):
                    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                    xs.append((x + w / 2) / small.shape[1])
            t += sample_every
        centers.append(sorted(xs)[len(xs) // 2] if xs else None)
    cap.release()
    # fill gaps with neighbours, and ignore tiny moves so the frame doesn't jitter between cuts
    last = next((c for c in centers if c is not None), 0.5)
    smoothed = []
    for c in centers:
        c = last if c is None else c
        if abs(c - last) < 0.06:
            c = last
        smoothed.append(c)
        last = c
    return smoothed


def video_filter(info, mode, center=0.5):
    sw, sh = info["width"], info["height"]
    vertical = sw / sh <= W / H + 0.02
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    if vertical or mode == "fill":
        vf = fit
    elif mode == "blur":
        vf = (f"split[a][b];[a]{fit},boxblur=24:2[bg];[b]scale={W}:-2[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:  # face / center: crop a 9:16 window out of the landscape frame
        cw = int(sh * W / H) // 2 * 2
        x = int(min(max(center * sw - cw / 2, 0), sw - cw))
        vf = f"crop={cw}:{sh}:{x}:0,scale={W}:{H}"
    return f"{vf},setsar=1,fps={FPS},format=yuv420p"


def render_cut(project: Project, *, reframe="face", draft=False, jobs=None) -> dict:
    project.require()
    edl = read_json(project.edl)
    src = project.source
    info = probe(src)
    if "width" not in info:
        raise OseError("source has no video stream")
    segs = quantize_segments(edl["segments"])
    edl["segments"] = segs
    write_json(project.edl, edl)

    landscape = info["width"] / info["height"] > W / H + 0.02
    centers = [0.5] * len(segs)
    if landscape and reframe == "face":
        log("tracking face for 9:16 reframe")
        centers = face_centers(src, segs)

    tmp = project.work / "segments"
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("seg_*.mkv"):
        f.unlink()
    crf, preset = ("24", "ultrafast") if draft else ("16", "veryfast")
    has_audio = info["audio"]

    def one(i):
        s = segs[i]
        dur = s["out"] - s["in"]
        fade = min(0.012, dur / 4)
        out = tmp / f"seg_{i:04d}.mkv"
        frames = round(dur * FPS)
        args = ["-ss", f"{s['in']:.4f}", "-t", f"{dur + 0.5:.4f}", "-i", src]
        if not has_audio:
            args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono"]
        # exactly `frames` video frames and frames/FPS seconds of audio: no drift across hundreds of cuts
        vf = (f"{video_filter(info, reframe, centers[i])},tpad=stop_mode=clone:stop_duration=0.5,"
              f"trim=end_frame={frames},setpts=PTS-STARTPTS")
        args += ["-vf", vf,
                 "-af", f"aresample=48000,apad,atrim=0:{dur:.4f},afade=t=in:d={fade},afade=t=out:st={dur - fade:.4f}:d={fade}",
                 "-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0",
                 "-c:v", "libx264", "-preset", preset, "-crf", crf, "-c:a", "pcm_s16le", "-ac", "1", out]
        ffmpeg(args)
        return out

    log(f"rendering {len(segs)} segments")
    with ThreadPoolExecutor(jobs or max(1, min(4, (os.cpu_count() or 2) // 2))) as ex:
        files = list(ex.map(one, range(len(segs))))

    listing = tmp / "concat.txt"
    listing.write_text("".join(f"file '{f.name}'\n" for f in files))
    ffmpeg(["-f", "concat", "-safe", "0", "-i", listing.name, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
            "-ar", "48000", "-movflags", "+faststart", project.cut.resolve()], cwd=tmp)

    tr = read_json(project.transcript)
    words = remap_words(tr["words"], segs)
    write_json(project.cut_words, {"language": tr.get("language"), "words": words})
    dur = probe(project.cut)["duration"]
    log(f"cut -> {project.cut} ({dur:.2f}s)")
    return {"cut": str(project.cut), "duration": dur, "segments": len(segs), "words": len(words)}
