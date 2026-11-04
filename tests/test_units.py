import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
from conftest import sentence

from ose.captions import build_ass, chunk_words
from ose.common import OseError, normalize_plan, remap_words, segment_offsets
from ose.cut import quantize_segments
from ose.pacing import analyse, fill_gaps
from ose.render import zoom_expr
from ose.transcribe import transcribe_whisperx


def test_chunks_respect_word_and_char_limits(words_factory):
    w = words_factory(sentence("one two three four five six seven extraordinarily", 0))
    chunks = chunk_words(w, max_words=3, max_chars=18)
    assert all(len(c["words"]) <= 3 for c in chunks)
    assert all(sum(len(x["word"]) + 1 for x in c["words"]) - 1 <= 18 or len(c["words"]) == 1 for c in chunks)
    assert [x["word"] for c in chunks for x in c["words"]] == [x["word"] for x in w]
    assert all(a["end"] <= b["start"] + 1e-6 for a, b in zip(chunks, chunks[1:]))


def test_chunks_break_on_sentence_end(words_factory):
    w = words_factory(sentence("Stop. Go now", 0))
    assert [len(c["words"]) for c in chunk_words(w)] == [1, 2]


def test_fast_caption_chunks_do_not_overlap(words_factory):
    words = words_factory([("One", 0.0, 0.08), ("two", 0.08, 0.16), ("three", 0.16, 0.24)])
    chunks = chunk_words(words, max_words=1)
    assert all(chunk["end"] > chunk["start"] for chunk in chunks)
    assert all(left["end"] <= right["start"] for left, right in zip(chunks, chunks[1:]))


def test_caption_linger_stops_at_video_end(words_factory):
    words = words_factory([("Last", 0.6, 0.8), ("word.", 0.8, 1.0)])
    _, chunks = build_ass(words, {}, duration=1.0)
    assert chunks[-1]["end"] == 1.0


def test_cold_open_words_follow_output_timeline(words_factory):
    words = words_factory([("Opening", 0.0, 0.4), ("Hook", 5.0, 5.4)])
    segments = [{"in": 4.9, "out": 5.5}, {"in": 0.0, "out": 0.5}]
    remapped = remap_words(words, segments)
    assert [word["word"] for word in remapped] == ["Hook", "Opening"]
    assert remapped[0]["start"] == pytest.approx(0.1)
    assert remapped[1]["start"] == pytest.approx(0.6)
    assert words[0]["start"] == 0.0


def test_ass_contains_cards(words_factory):
    w = words_factory(sentence("hello there friend", 0))
    ass, _ = build_ass(w, {"hook": {"text": "Big hook"}, "cta": {"text": "Follow"}}, 5.0)
    assert "Card,,0,0,0,,{\\fad(80,120)}Big hook" in ass
    assert "Follow" in ass and "HELLO" in ass


def test_remap_words_to_cut_timeline(words_factory):
    w = words_factory([("a", 0.0, 0.4), ("cut", 1.0, 1.4), ("b", 2.0, 2.4)])
    segs = [{"in": 0.0, "out": 0.5}, {"in": 1.9, "out": 2.5}]
    assert segment_offsets(segs) == [0.0, 0.5]
    out = remap_words(w, segs)
    assert [x["word"] for x in out] == ["a", "b"]
    assert out[1]["start"] == pytest.approx(0.6)


def test_quantize_segments_whole_frames():
    segs = quantize_segments([{"in": 0.0, "out": 1.01}, {"in": 2.0, "out": 3.333}], fps=30)
    for s in segs:
        frames = (s["out"] - s["in"]) * 30
        assert abs(frames - round(frames)) < 0.05  # ms-rounded; cut.py trims to exact frames


def test_normalize_plan_accepts_duration_or_end():
    plan = normalize_plan({"zooms": [{"start": 1, "duration": 2}], "broll": [{"asset": "x", "start": 1, "end": 3}],
                           "sfx": [{"start": 2, "file": "pop"}]})
    assert plan["zooms"] == [{"start": 1, "end": 3.0}]
    assert plan["broll"][0]["duration"] == 2.0 and "end" not in plan["broll"][0]
    assert plan["sfx"] == [{"at": 2, "asset": "pop"}]
    with pytest.raises(OseError):
        normalize_plan({"texts": [{"text": "x", "start": 1}]})


def test_pacing_finds_and_fills_gaps():
    segs = [{"in": 0, "out": 10}]
    plan = {"zooms": []}
    r = analyse(plan, segs, 10.0, max_gap=3.0)
    assert not r["ok"] and r["gaps"]
    fill_gaps(plan, r["gaps"])
    assert analyse(plan, segs, 10.0, max_gap=3.0)["ok"]


def test_zoom_expr():
    assert zoom_expr([]) == "1"
    e = zoom_expr([{"start": 1, "end": 2, "scale": 1.2, "style": "punch"}])
    assert e.startswith("1+") and "between(t,1.000,2.000)" in e


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
@pytest.mark.parametrize("duration", [0.04, 0.2, 2.0])
def test_smooth_zoom_returns_to_base_without_a_jump(duration):
    start, end = 0.1, 0.1 + duration
    expression = zoom_expr([{"start": start, "end": end, "scale": 1.2, "style": "smooth"}])
    luminance = expression.replace("t", "T")
    result = subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=s=16x16:r=100:d={end + 0.1}",
        "-vf", f"format=yuv444p,geq=lum='({luminance}-1)*200':cb=128:cr=128",
        "-threads", "1", "-f", "rawvideo", "-pix_fmt", "yuv444p", "pipe:1",
    ], capture_output=True, check=True)
    samples = result.stdout[::16 * 16 * 3]
    first, last = round(start * 100), round(end * 100)
    assert max(samples[:first + 1]) <= 1
    assert max(samples[last:]) <= 1
    assert samples[round((start + end) / 2 * 100)] == pytest.approx(40, abs=1)
    assert samples[last - 1] <= (20 if duration == 0.04 else 2)


@pytest.mark.parametrize("missing", ["start", "end", "all-words", "missing-words"])
def test_whisperx_does_not_drop_unaligned_words(monkeypatch, missing):
    word = {"word": "20", "start": 0.1, "end": 0.3}
    if missing in ("start", "end"):
        del word[missing]
    segment = {"start": 0, "end": 1, "text": "20", "words": [word]}
    if missing == "all-words":
        segment["words"] = []
    if missing == "missing-words":
        del segment["words"]
    backend = SimpleNamespace(
        load_model=lambda *args, **kwargs: SimpleNamespace(
            transcribe=lambda *args, **kwargs: {"language": "en", "segments": [segment]}),
        load_audio=lambda *args: [],
        load_align_model=lambda **kwargs: (None, None),
        align=lambda *args, **kwargs: {"segments": [segment]},
    )
    monkeypatch.setitem(sys.modules, "whisperx", backend)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False)))
    with pytest.raises(OseError, match="align.*20"):
        transcribe_whisperx("unused.wav", "en", "small", True)
