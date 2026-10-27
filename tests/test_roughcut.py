import pytest

from conftest import sentence

from ose.common import OseError, Project, load_edl, read_json, write_json
from ose.roughcut import build_edl, parse_ranges, run_roughcut


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


@pytest.mark.parametrize("first, second, language", [
    ("This treatment is safe.", "This treatment is not safe.", "en"),
    ("I can recommend this product.", "I can't recommend this product.", "en"),
    ("Use 10 drops every day.", "Use 20 drops every day.", "en"),
    ("Take one tablet every day.", "Take two tablets every day.", "en"),
    ("Isso funciona para todos.", "Isso não funciona para todos.", "pt"),
    ("Use dois copos de agua.", "Use tres copos de agua.", "pt"),
])
def test_meaning_changing_retakes_need_review(words_factory, first, second, language):
    words = words_factory(sentence(first, 0), sentence(second, 4))
    edl = build_edl(words, language=language)
    assert kept_text(words, edl) == f"{first} {second}"
    assert edl["review"][0]["reason"] == "meaning-change"


def test_retake_does_not_delete_unrelated_between_take_speech(words_factory):
    words = words_factory(sentence("This is the best method.", 0),
                          sentence("But it costs more.", 2),
                          sentence("This is the best method.", 4))
    edl = build_edl(words)
    assert "But it costs more." in kept_text(words, edl)
    assert not any(item["reason"] == "retake-junk" for item in edl["decisions"])


def test_two_word_repetition_across_long_pause_is_not_a_stutter(words_factory):
    words = words_factory(sentence("Keep going", 0), sentence("keep going forward.", 25))
    assert kept_text(words, build_edl(words)) == "Keep going keep going forward."


def test_portuguese_um_is_not_an_english_filler(words_factory):
    words = words_factory(sentence("Use um copo de agua.", 0))
    assert kept_text(words, build_edl(words, language="pt")) == "Use um copo de agua."


@pytest.mark.parametrize("spec", ["nonsense", "1-1", "2-1", "-1-2", "1-inf", "nan-2"])
def test_invalid_manual_ranges_are_rejected(spec):
    with pytest.raises(OseError, match="range"):
        parse_ranges(spec)


def test_empty_transcript_has_actionable_error():
    with pytest.raises(OseError, match="no words"):
        build_edl([])


@pytest.mark.parametrize("start, end", [(-1, 0.5), (1, 1), (2, 1), (0, float("nan")), (0, 11)])
def test_invalid_word_timing_is_rejected(start, end):
    with pytest.raises(OseError, match="timestamp"):
        build_edl([{"word": "Hello", "start": start, "end": end}], duration=10)


def test_cut_range_cannot_exceed_source(words_factory):
    words = words_factory(sentence("Keep this phrase.", 0))
    with pytest.raises(OseError, match="range"):
        build_edl(words, duration=10, cut_ranges=[(9, 12)])


def test_edl_fingerprint_ignores_metadata_but_detects_changed_words(tmp_path, monkeypatch, words_factory):
    from ose import roughcut
    project = Project(tmp_path)
    project.save_meta({"source": "source.mp4"})
    monkeypatch.setattr(roughcut, "probe", lambda path: {"duration": 4})
    transcript = {"language": "en", "elapsed_s": 1, "words": words_factory(sentence("Keep my edit.", 0))}
    write_json(project.transcript, transcript)
    run_roughcut(project)
    reviewed = read_json(project.edl)
    transcript["elapsed_s"] = 99
    transcript["words"][0]["alignment_note"] = "metadata only"
    write_json(project.transcript, transcript)
    assert load_edl(project) == reviewed
    transcript["words"][0]["word"] = "Changed"
    write_json(project.transcript, transcript)
    with pytest.raises(OseError, match="transcript changed"):
        load_edl(project)
