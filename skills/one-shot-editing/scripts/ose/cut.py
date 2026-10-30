"""Render the rough cut (EDL) into work/cut.mp4 on a 9:16 canvas, with optional face-tracked reframe."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

from .common import FPS, H, W, OseError, Project, ffmpeg, load_edl, load_plan, log, probe, read_json, remap_words, write_json
from .provenance import check_plan_revision, cut_inputs, record_cut
from .quality import color_args, settings, verify_cfr


def quantize_segments(segments, fps=FPS):
    """Snap segment durations to whole frames so audio/video never drift across many cuts."""
    out = []
    for s in segments:
        rate = float(fps)
        frames = max(1, round((s["out"] - s["in"]) * rate))
        start = round(s["in"] * rate) / rate
        out.append({**s, "in": start, "out": start + frames / rate})
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


def smooth_track(samples, max_speed=0.15):
    """Bound movement in normalized source-width/second; hold on missed detections."""
    out = []
    center = next((value for _, value in samples if value is not None), 0.5)
    for time, value in samples:
        if value is not None:
            dt = time - out[-1]["time"] if out else 0
            delta = max(-max_speed * dt, min(max_speed * dt, value - center))
            if abs(value - center) > 0.015:
                center += delta
        out.append({"time": round(time, 4), "center": round(center, 6)})
    return out or [{"time": 0.0, "center": 0.5}]


def face_tracks(src, segments, max_speed=0.15):
    import cv2
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened() or cascade.empty():
        raise OseError("cannot initialize face tracking; choose --reframe center or a manual framing.center")
    tracks, missing, multiple = [], 0, 0
    try:
        for segment in segments:
            samples, time, previous = [], segment["in"], None
            while time < segment["out"]:
                cap.set(cv2.CAP_PROP_POS_MSEC, time * 1000)
                ok, frame = cap.read()
                center = None
                if ok:
                    small = cv2.resize(frame, (640, max(1, int(640 * frame.shape[0] / frame.shape[1]))))
                    faces = cascade.detectMultiScale(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), 1.15, 5, minSize=(40, 40))
                    if len(faces):
                        multiple += len(faces) > 1
                        face = (max(faces, key=lambda face: face[2] * face[3]) if previous is None else
                                min(faces, key=lambda face: abs((face[0] + face[2] / 2) / 640 - previous)))
                        center = (face[0] + face[2] / 2) / 640
                        previous = center
                missing += center is None
                samples.append((time - segment["in"], center))
                time += 0.5
            tracks.append(smooth_track(samples, max_speed))
    finally:
        cap.release()
    if missing or multiple:
        log(f"framing review: {missing} samples without a face, {multiple} with multiple faces; "
            "tracking holds on misses and follows the nearest face, not the active speaker")
    return tracks, {"missing_samples": missing, "multiple_face_samples": multiple}


def crop_expression(track, sw, cw):
    xs = [(point["time"], min(max(point["center"] * sw - cw / 2, 0), sw - cw)) for point in track]
    terms = [f"{xs[0][1]:.6f}"]
    for (a, x), (b, y) in zip(xs, xs[1:]):
        if b > a and abs(y - x) > 0.001:
            terms.append(f"{(y - x) / (b - a):.6f}*clip(t-{a:.4f},0,{b - a:.4f})")
    return "+".join(terms)


def video_filter(info, mode, center=0.5, *, config=None, track=None):
    config = config or {"width": W, "height": H, "fps": str(FPS), "pix_fmt": "yuv420p"}
    width, height = config["width"], config["height"]
    sw, sh = info["width"], info["height"]
    vertical = sw / sh <= W / H + 0.02
    fit = f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,crop={width}:{height}"
    if vertical or mode == "fill":
        vf = fit
    elif mode == "blur":
        vf = (f"split[a][b];[a]{fit},boxblur=24:2[bg];[b]scale={width}:-2:flags=lanczos[fg];"
              f"[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:  # face / center: crop a 9:16 window out of the landscape frame
        cw = int(sh * W / H) // 2 * 2
        x = crop_expression(track, sw, cw) if track else str(int(min(max(center * sw - cw / 2, 0), sw - cw)))
        vf = f"crop={cw}:{sh}:'{x}':0,scale={width}:{height}:flags=lanczos"
    return f"setpts=PTS-STARTPTS,{vf},setsar=1,fps={config['fps']},format={config['pix_fmt']}"


def render_cut(project: Project, *, reframe="face", draft=False, jobs=None) -> dict:
    project.require()
    edl = load_edl(project)
    plan = load_plan(project)
    check_plan_revision(project, plan)
    src = project.source
    info = probe(src)
    if "width" not in info:
        raise OseError("source has no video stream")
    config = settings(info, plan, reframe=reframe)
    original_inputs = cut_inputs(project, config, reframe)
    if config["profile"] == "source":
        verify_cfr(project, info, original_inputs["source"])
    rate = float(Fraction(config["fps"]))
    segs = quantize_segments(edl["segments"], rate)
    if any(segment["in"] >= info["duration"] or segment["out"] > info["duration"] + 1 / rate for segment in segs):
        raise OseError("EDL segment exceeds source duration")

    landscape = info["width"] / info["height"] > W / H + 0.02
    centers = [0.5] * len(segs)
    tracks = [None] * len(segs)
    framing = plan.get("framing", {})
    tracking_report = {}
    if "center" in framing:
        centers = [framing["center"]] * len(segs)
    elif landscape and reframe == "face" and framing.get("tracking", "dynamic") == "dynamic":
        tracks, tracking_report = face_tracks(src, segs, framing.get("max_speed", 0.15))
    elif landscape and reframe == "face":
        log("tracking face for 9:16 reframe")
        centers = face_centers(src, segs)

    tmp = project.work / "segments"
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("seg_*.mkv"):
        f.unlink()
    has_audio = info["audio"]

    def one(i):
        s = segs[i]
        dur = s["out"] - s["in"]
        fade = min(0.012, dur / 4)
        out = tmp / f"seg_{i:04d}.mkv"
        frames = round(dur * rate)
        args = ["-ss", f"{s['in']:.4f}", "-t", f"{dur + 0.5:.4f}", "-i", src]
        if not has_audio:
            args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono"]
        # exactly `frames` video frames and frames/FPS seconds of audio: no drift across hundreds of cuts
        vf = (f"{video_filter(info, reframe, centers[i], config=config, track=tracks[i])},tpad=stop_mode=clone:stop_duration=0.5,"
              f"trim=end_frame={frames},setpts=PTS-STARTPTS")
        script = tmp / f"filter_{i:04d}.txt"
        script.write_text(vf)
        video = (["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26"] if draft else
                 ["-c:v", "ffv1", "-level", "3"])
        args += ["-filter_script:v", script,
                 "-af", f"aresample={config['sample_rate']},apad,atrim=0:{dur:.9f},asetpts=PTS-STARTPTS,"
                        f"afade=t=in:d={fade},afade=t=out:st={dur - fade:.9f}:d={fade}",
                 "-map", "0:v:0", "-map", "0:a:0" if has_audio else "1:a:0",
                 *video, "-threads", "2", *color_args(config), "-c:a", "pcm_f32le", out]
        ffmpeg(args)
        return out

    log(f"rendering {len(segs)} segments")
    with ThreadPoolExecutor(jobs or max(1, min(4, (os.cpu_count() or 2) // 2))) as ex:
        files = list(ex.map(one, range(len(segs))))

    listing = tmp / "concat.txt"
    listing.write_text("".join(f"file '{f.name}'\n" for f in files))
    pending = project.work / "cut.pending.mkv"
    total = sum(segment["out"] - segment["in"] for segment in segs)
    codec = (["-c:v", "libx264", "-preset", "ultrafast", "-crf", "26"] if draft else
             ["-c:v", "ffv1", "-level", "3"])
    # Reset packet timestamps once: Matroska's millisecond time base must not accumulate at each seam.
    ffmpeg(["-f", "concat", "-safe", "0", "-i", listing.name,
            "-vf", f"setpts=N/({config['fps']}*TB)", "-r", config["fps"],
            "-af", f"asetpts=N/SR/TB,apad,atrim=0:{total:.9f}",
            *codec, "-threads", "2", *color_args(config), "-c:a", "pcm_f32le", pending.resolve()], cwd=tmp)
    if cut_inputs(project, config, reframe) != original_inputs:
        pending.unlink(missing_ok=True)
        raise OseError("editing inputs changed during cut; retry after changes finish")
    pending.replace(project.cut)

    tr = read_json(project.transcript)
    words = remap_words(tr["words"], segs)
    write_json(project.cut_words, {"language": tr.get("language"), "words": words, "segments": segs})
    write_json(project.work / "framing.json", {"tracks": tracks, **tracking_report})
    dur = probe(project.cut)["duration"]
    project.update_meta(cut_draft=bool(draft), cut_reframe=reframe)
    record_cut(project, config, reframe, draft)
    log(f"cut -> {project.cut} ({dur:.2f}s)")
    return {"cut": str(project.cut), "duration": dur, "segments": len(segs), "words": len(words)}
