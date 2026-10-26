import pytest
from conftest import sentence

from ose.captions import build_ass, chunk_words
from ose.common import OseError, normalize_plan, remap_words, segment_offsets
from ose.cut import quantize_segments
from ose.pacing import analyse, fill_gaps
from ose.render import zoom_expr


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
