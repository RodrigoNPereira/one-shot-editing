from conftest import sentence

from ose.roughcut import build_edl


def kept_text(words, edl):
    out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        if any(s["in"] <= mid <= s["out"] for s in edl["segments"]):
            out.append(w["word"])
    return " ".join(out)


def test_hard_fillers_removed_en_and_pt(words_factory):
    w = words_factory(sentence("So um this is uh great.", 0))
    edl = build_edl(w, language="en")
    assert kept_text(w, edl) == "So this is great."
    w = words_factory(sentence("Então hã isso é éé ótimo.", 0))
    assert kept_text(w, build_edl(w, language="pt")) == "Então isso é ótimo."


def test_soft_fillers_only_when_aggressive(words_factory):
    w = words_factory(sentence("It is like you know really fast.", 0))
    assert "like" in kept_text(w, build_edl(w, language="en"))
    assert kept_text(w, build_edl(w, language="en", aggressive=True)) == "It is really fast."


def test_stutter_removed(words_factory):
    w = words_factory(sentence("I I think the the plan works.", 0))
    assert kept_text(w, build_edl(w)) == "I think the plan works."


def test_retake_keeps_last_take(words_factory):
    first = sentence("This is the best way to edit videos.", 0)
    second = sentence("This is the best way to edit video.", 4.0)
    w = words_factory(first, second)
    edl = build_edl(w)
    assert kept_text(w, edl) == "This is the best way to edit video."
    assert [d["reason"] for d in edl["decisions"]] == ["retake"]
    # reverting the decision brings the first take back
    edl2 = build_edl(w, keep_ids=["r1"])
    assert kept_text(w, edl2).count("best way") == 2


def test_false_start_dropped(words_factory):
    w = words_factory(sentence("The secret is", 0), sentence("The secret is consistency every day.", 2.0))
    edl = build_edl(w)
    assert kept_text(w, edl) == "The secret is consistency every day."
    assert edl["decisions"][0]["reason"] == "false-start"


def test_long_pauses_compressed(words_factory):
    w = words_factory(sentence("First part here.", 0), sentence("Second part here.", 5.0))
    edl = build_edl(w, pace="tight")
    assert len(edl["segments"]) == 2
    assert edl["stats"]["cut_duration"] < 2.2


def test_manual_cut_range(words_factory):
    w = words_factory(sentence("Keep this. Drop this part. Keep end.", 0, gap=0.0))
    edl = build_edl(w, cut_ranges=[(0.6, 1.45)])
    assert kept_text(w, edl) == "Keep this. Keep end."


def test_distinct_sentences_untouched(words_factory):
    w = words_factory(sentence("Coffee is great.", 0), sentence("Tea is also fine.", 1.2))
    edl = build_edl(w)
    assert not edl["decisions"]
    assert kept_text(w, edl) == "Coffee is great. Tea is also fine."
