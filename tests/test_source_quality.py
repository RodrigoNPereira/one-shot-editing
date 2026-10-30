import shutil
from fractions import Fraction

import pytest

from ose.common import Project, ffmpeg, probe, read_json, run, write_json
from ose.cut import render_cut
from ose.provenance import adopt
from ose.render import run_render

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def frame_hashes(path, frames=None):
    command = ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0"]
    if frames:
        command.extend(["-frames:v", str(frames)])
    result = run([*command, "-f", "framemd5", "-"], capture=True)
    return [line.rsplit(",", 1)[-1].strip() for line in result.stdout.splitlines() if not line.startswith("#")]


@pytest.mark.parametrize("pixel, fps", [("yuv420p", "60"), ("yuv420p10le", "60000/1001")])
def test_source_master_has_no_generation_loss(tmp_path, pixel, fps):
    p = Project(tmp_path / "project")
    p.root.mkdir()
    p.save_meta({"source": "input.mp4"})
    ffmpeg(["-f", "lavfi", "-i", f"testsrc2=s=90x160:r={fps}:d=1",
            "-f", "lavfi", "-i", "sine=f=220:r=48000:d=1",
            "-c:v", "libx264", "-qp", "0", "-preset", "ultrafast", "-pix_fmt", pixel,
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-color_range", "tv", "-c:a", "alac", "-shortest", p.source])
    duration = 40 / float(Fraction(fps))
    write_json(p.transcript, {"language": "en", "words": [{"word": "Hello", "start": 0, "end": duration}]})
    write_json(p.edl, {"segments": [{"in": 0, "out": duration}]})
    adopt(p)
    write_json(p.plan, {"output": {"profile": "source"}, "audio": {"normalization": "off"}})
    render_cut(p, reframe="center", jobs=1)
    run_render(p, captions=False)
    original = frame_hashes(p.source, frames=40)
    assert frame_hashes(p.cut) == original
    assert frame_hashes(p.final) == original
    info = probe(p.final)
    assert (info["width"], info["height"]) == (90, 160)
    assert info["pix_fmt"] == pixel
    assert info["fps"] == pytest.approx(float(Fraction(fps)), abs=0.001)
    assert info["color_primaries"] == "bt709"
    assert read_json(p.work / "cut.provenance.json")["draft"] is False
    if pixel == "yuv420p":
        from ose.review import deletion_reel
        reel = deletion_reel(p)
        assert reel["clips"] == 1
        assert probe(reel["file"])["audio"]


def test_otio_export_round_trips_source_cuts(tmp_path):
    otio = pytest.importorskip("opentimelineio")
    from ose.interchange import export_otio
    p = Project(tmp_path)
    p.save_meta({"source": "input.mp4"})
    ffmpeg(["-f", "lavfi", "-i", "testsrc2=s=90x160:r=30:d=1", "-c:v", "libx264", p.source])
    write_json(p.transcript, {"words": [{"word": "Hi", "start": 0, "end": 0.5}]})
    write_json(p.edl, {"segments": [{"in": 0.5, "out": 1}, {"in": 0, "out": 0.5}]})
    adopt(p)
    write_json(p.plan, {})
    result = export_otio(p)
    timeline = otio.adapters.read_from_file(result["file"])
    assert len(timeline.tracks[0]) == 2
    assert timeline.tracks[0][0].source_range.start_time.to_seconds() == 0.5
    assert timeline.duration().to_seconds() == 1


def test_visual_qa_measures_glyphs_and_collisions(tmp_path):
    from ose.captions import _header
    from ose.render import PLATFORMS
    from ose.visual import inspect_overlays
    p = Project(tmp_path)
    p.work.mkdir()
    p.out.mkdir()
    ffmpeg(["-f", "lavfi", "-i", "color=c=blue:s=180x320:r=30:d=1", "-c:v", "libx264", p.final])
    p.captions_ass.write_text(
        _header("bold-pop") + "\n"
        r"Dialogue: 0,0:00:00.00,0:00:01.00,Cap,,0,0,0,,{\pos(500,800)}HELLO" + "\n"
        r"Dialogue: 1,0:00:00.00,0:00:01.00,Title,,0,0,0,,{\pos(500,800)}WORLD" + "\n"
        r"Dialogue: 1,0:00:00.00,0:00:01.00,Card,,0,0,0,,{\pos(1050,50)}OUTSIDE" + "\n")
    layout = inspect_overlays(p, p.final, PLATFORMS["tiktok"]["safe"])
    assert layout["sampled"] == 3
    assert layout["outside_safe_zone"]
    assert layout["overlay_collisions"]
    assert all(0 < item["box"][2] - item["box"][0] < 1080 for item in layout["bounds"])


def test_many_short_cuts_keep_every_frame_and_sync(tmp_path):
    p = Project(tmp_path)
    p.save_meta({"source": "input.mp4"})
    ffmpeg(["-f", "lavfi", "-i", "testsrc2=s=90x160:r=60:d=2",
            "-f", "lavfi", "-i", "sine=r=48000:d=2",
            "-c:v", "libx264", "-qp", "0", "-c:a", "alac", "-shortest", p.source])
    segments = [{"in": i / 10, "out": i / 10 + 0.05} for i in range(20)]
    write_json(p.transcript, {"words": [{"word": "Hi", "start": 0, "end": 0.04}]})
    write_json(p.edl, {"segments": segments})
    adopt(p)
    write_json(p.plan, {"audio": {"normalization": "off"}})
    render_cut(p, reframe="center", jobs=1)
    run_render(p, captions=False)
    original = frame_hashes(p.source)
    expected = [frame for i in range(20) for frame in original[i * 6:i * 6 + 3]]
    assert frame_hashes(p.cut) == expected
    assert frame_hashes(p.final) == expected
    assert probe(p.final)["duration"] == pytest.approx(1, abs=1 / 60)


def test_dynamic_crop_trajectory_reaches_ffmpeg(tmp_path, monkeypatch):
    from ose import cut
    p = Project(tmp_path)
    p.save_meta({"source": "input.mp4"})
    ffmpeg(["-f", "lavfi", "-i", "testsrc2=s=320x180:r=30:d=1",
            "-c:v", "libx264", "-qp", "0", p.source])
    write_json(p.transcript, {"words": [{"word": "Hi", "start": 0, "end": 1}]})
    write_json(p.edl, {"segments": [{"in": 0, "out": 1}]})
    adopt(p)
    write_json(p.plan, {})
    monkeypatch.setattr(cut, "face_tracks", lambda *args: (
        [[{"time": 0, "center": 0.2}, {"time": 0.5, "center": 0.29375}, {"time": 1, "center": 0.3875}]], {}))
    render_cut(p, reframe="face", jobs=1)
    expected = tmp_path / "expected.mkv"
    ffmpeg(["-i", p.source, "-vf", "crop=100:180:x='14+60*t':y=0",
            "-c:v", "ffv1", expected])
    assert frame_hashes(p.cut) == frame_hashes(expected)
