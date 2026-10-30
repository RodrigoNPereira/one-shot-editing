"""Sample libass-rendered glyph bounds, overlaps and visible faces."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

from .common import ASSETS, H, W, ffmpeg


def _seconds(value):
    hours, minutes, seconds = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def inspect_overlays(project, target, safe, max_samples=24):
    from PIL import Image
    import cv2
    import numpy as np
    from .render import _esc
    text = project.captions_ass.read_text(encoding="utf-8")
    header = text[:text.index("Dialogue:")] if "Dialogue:" in text else text
    events, seen = [], set()
    for line in text.splitlines():
        if not line.startswith("Dialogue:"):
            continue
        fields = line.split(",", 9)
        clean = re.sub(r"\{[^}]*\}", "", fields[9])
        key = (fields[3], clean)
        if key in seen:
            continue
        seen.add(key)
        start, end = _seconds(fields[1]), _seconds(fields[2])
        if end > start:
            events.append({"style": fields[3], "text": clean, "start": start, "end": end, "line": line})
    # Longest rendered strings are the most likely to overflow; report sampling explicitly.
    selected = sorted(events, key=lambda event: len(event["text"]), reverse=True)[:max_samples]
    bounds, outside, face_overlaps, collisions = [], [], [], []
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    face_samples = 0
    with tempfile.TemporaryDirectory(prefix="layout-", dir=project.work) as directory:
        directory = Path(directory)
        for i, event in enumerate(selected):
            time = event["start"] + min(0.15, (event["end"] - event["start"]) / 2)
            ass = directory / "event.ass"
            ass.write_text(header + event["line"] + "\n", encoding="utf-8")
            png = directory / f"overlay-{i}.png"
            vf = f"setpts=PTS+{time}/TB,ass=filename=event.ass:fontsdir='{_esc(ASSETS / 'fonts')}':alpha=1"
            ffmpeg(["-f", "lavfi", "-i", f"color=black@0:s={W}x{H}:r=30:d=0.1,format=rgba",
                    "-vf", vf, "-frames:v", "1", "-threads", "1", png], cwd=directory)
            with Image.open(png) as image:
                box = image.getchannel("A").point(lambda value: 255 if value > 8 else 0).getbbox()
            if box is None:
                outside.append({"text": event["text"], "reason": "no visible glyphs at sampled time"})
                continue
            bounds.append({**{key: event[key] for key in ("style", "text", "start", "end")}, "box": list(box)})
            x1, y1, x2, y2 = box
            if x1 < safe["left"] or y1 < safe["top"] or x2 > W - safe["right"] or y2 > H - safe["bottom"]:
                outside.append({"text": event["text"], "box": list(box)})
            frame = directory / f"frame-{i}.png"
            ffmpeg(["-ss", str(time), "-i", target, "-vf", f"scale={W}:{H}",
                    "-frames:v", "1", "-threads", "1", frame])
            with Image.open(frame) as image:
                gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
            faces = cascade.detectMultiScale(gray, 1.15, 5, minSize=(60, 60))
            face_samples += bool(len(faces))
            if any(overlap(box, (x, y, x + width, y + height)) for x, y, width, height in faces):
                face_overlaps.append(event["text"])
    for i, left in enumerate(bounds):
        for right in bounds[i + 1:]:
            if left["style"] != right["style"] and left["start"] < right["end"] and right["start"] < left["end"]:
                if overlap(left["box"], right["box"]):
                    collisions.append([left["text"], right["text"]])
    return {"sampled": len(selected), "unique_overlays": len(events), "bounds": bounds,
            "outside_safe_zone": outside, "overlay_collisions": collisions, "face_overlaps": face_overlaps,
            "samples_with_detected_faces": face_samples,
            "coverage": "sampled rendered bounds; face detection and unobserved frames still require human review"}
