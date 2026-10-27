"""End-to-end smoke test on synthetic media (no Whisper needed: the transcript is written directly)."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OSE = ROOT / "skills" / "one-shot-editing" / "bin" / "ose"

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def ose(*args, env):
    r = subprocess.run([str(OSE), *map(str, args)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]
    return r.stdout


def frames(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v",
                          "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout
    return int(out.strip())


def test_full_pipeline(tmp_path):
    env = {**os.environ, "OSE_HOME": str(tmp_path / "home")}
    src = tmp_path / "talk.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=12",
                    "-f", "lavfi", "-i", "sine=f=220:d=12", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(src)], check=True)
    img = tmp_path / "home" / "library" / "broll" / "_inbox" / "shot.png"
    img.parent.mkdir(parents=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=800x600", "-frames:v", "1",
                    str(img)], check=True)

    proj = tmp_path / "proj"
    ose("init", proj, "--video", src, "--lang", "en", env=env)
    words = []
    for text, start in [("This is take one of the line.", 0.5), ("This is take one of the line.", 3.5),
                        ("um and here is more content now.", 7.0)]:
        t = start
        for w in text.split():
            words.append({"word": w, "start": round(t, 3), "end": round(t + 0.25, 3), "prob": 0.9})
            t += 0.3
    (proj / "work" / "transcript.json").write_text(json.dumps({"language": "en", "words": words}))

    ose("roughcut", proj, env=env)
    edl = json.loads((proj / "work" / "edl.json").read_text())
    assert edl["stats"]["by_reason"] == {"retake": 1, "filler": 1}
    ose("roughcut", proj, "--hook-range", "7.3-8.5", env=env)  # cold open must not play twice
    segs = json.loads((proj / "work" / "edl.json").read_text())["segments"]
    assert segs[0]["hook"] and all(s["out"] <= 7.3 or s["in"] >= 8.5 for s in segs[1:])
    ose("roughcut", proj, env=env)
    ose("cut", proj, "--reframe", "center", "--draft", env=env)
    assert json.loads((proj / "project.json").read_text())["cut_draft"] is True
    cut = proj / "work" / "cut.mp4"
    expected = sum(round((s["out"] - s["in"]) * 30) for s in json.loads((proj / "work" / "edl.json").read_text())["segments"])
    assert frames(cut) == expected

    ose("broll", "ingest", env=env)
    bid = json.loads(ose("broll", "pending", env=env))[0]["id"]
    ose("broll", "label", bid, "--category", "ui", "--labels", "blue,screen", env=env)
    ose("plan", proj, "--set", "hook.text=Test hook", "--set", "cta.text=Follow",
        "--add-broll", json.dumps({"asset": bid, "start": 1.0, "duration": 1.0, "mode": "pip"}),
        "--add-zoom", json.dumps({"start": 0, "duration": 0.8, "scale": 1.2, "style": "punch"}),
        "--add-sfx", json.dumps({"at": 1.0, "asset": "pop"}), env=env)
    ose("pacing", proj, "--apply", env=env)
    r = json.loads(ose("render", proj, env=env))
    assert json.loads((proj / "project.json").read_text())["cut_draft"] is False
    assert r["size"] == "1080x1920"
    q = json.loads(ose("qa", proj, "--json", env=env))
    failed = [c for c in q["checks"] if c["status"] == "error"]
    assert not failed, failed
    assert (proj / "out" / "contact_sheet.jpg").exists()
