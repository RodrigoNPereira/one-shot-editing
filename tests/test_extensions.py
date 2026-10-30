import json
import multiprocessing
from pathlib import Path

import pytest

from ose import broll, hooks
from ose.benchmark import deletion_metrics, word_metrics
from ose.common import OseError, read_json, write_json
from ose.cut import crop_expression, smooth_track
from ose.render import parse_loudness
from ose.review import removed_ranges
from ose.semantic import rank


def _increment(index, count):
    from ose import broll
    broll.INDEX = Path(index)
    for _ in range(count):
        broll.mark_used("item")


def test_library_updates_are_serialized(tmp_path):
    path = tmp_path / "library" / "index.json"
    write_json(path, [{"id": "item", "uses": 0}])
    processes = [multiprocessing.get_context("spawn").Process(target=_increment, args=(str(path), 12))
                 for _ in range(3)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=30)
        assert process.exitcode == 0
    assert read_json(path)[0]["uses"] == 36


def test_relabel_rolls_back_files_if_index_write_fails(tmp_path, monkeypatch):
    root = tmp_path / "library"
    source = root / "incoming" / "clip.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"original")
    index = root / "index.json"
    write_json(index, [{"id": "item", "path": str(source)}])
    monkeypatch.setattr(broll, "INDEX", index)
    monkeypatch.setattr(broll, "BROLL_DIR", root)

    def fail(items):
        raise OSError("disk full")
    monkeypatch.setattr(broll, "save_index", fail)
    with pytest.raises(OSError, match="disk full"):
        broll.label("item", category="city")
    assert source.read_bytes() == b"original"
    assert read_json(index)[0]["path"] == str(source)
    assert not (root / "city" / "clip.mp4").exists()


def test_dynamic_crop_holds_misses_and_limits_speed():
    track = smooth_track([(0, 0.2), (0.5, 0.8), (1, None), (1.5, 0.9)], max_speed=0.1)
    assert track[1]["center"] == pytest.approx(0.25)
    assert track[2]["center"] == track[1]["center"]
    assert track[3]["center"] == pytest.approx(0.3)
    assert "clip(t-" in crop_expression(track, 1920, 608)


def test_benchmark_measures_errors_without_inventing_boundaries():
    reference = [{"word": "Olá", "start": 0, "end": 0.4}, {"word": "mundo", "start": 0.5, "end": 1}]
    actual = [{"word": "Olá", "start": 0.1, "end": 0.5}, {"word": "amigo", "start": 0.5, "end": 1}]
    result = word_metrics(reference, actual)
    assert result["wer"] == 0.5 and result["aligned_words"] == 1
    assert result["boundary_mae_s"] == pytest.approx(0.1)
    deletion = deletion_metrics([[0, 2]], [{"in": 0, "out": 1}, {"in": 3, "out": 4}])
    assert deletion["incorrectly_deleted_s"] == 1
    assert deletion["unwanted_retained_s"] == 1


def test_deletion_reel_ranges_cover_silence_and_reordered_hooks():
    assert removed_ranges([{"in": 5, "out": 6}, {"in": 0, "out": 2}, {"in": 1, "out": 3}], 8) == [(3, 5), (6, 8)]


def test_loudness_analysis_requires_finite_measured_values():
    stats = {"input_i": "-18", "input_tp": "-3", "input_lra": "4", "input_thresh": "-28", "target_offset": "0.1"}
    assert parse_loudness("logs\n" + json.dumps(stats))["input_i"] == -18
    stats["input_i"] = "-inf"
    with pytest.raises(OseError, match="non-finite"):
        parse_loudness(json.dumps(stats))
    with pytest.raises(OseError, match="did not return"):
        parse_loudness("no summary")


def test_semantic_ranking_filters_and_orders_actual_embeddings():
    items = [{"id": "a", "kind": "image"}, {"id": "b", "kind": "video", "duration": 5}]
    vectors = [{"id": "a", "vector": [1, 0]}, {"id": "b", "vector": [0, 1]}]
    assert rank(items, vectors, [0.1, 1])[0]["id"] == "b"
    assert rank(items, vectors, [0.1, 1], kind="image")[0]["id"] == "a"
    assert rank(items, vectors, [0.1, 1], kind="video", min_duration=6) == []


def test_performance_cohorts_do_not_pool_platforms_or_small_samples(tmp_path, monkeypatch):
    monkeypatch.setattr(hooks, "PERF_CSV", tmp_path / "performance.csv")
    for platform, duration, retention in [("tiktok", 20, 90), ("shorts", 20, 40), ("tiktok", 90, 50)]:
        hooks.perf_add(platform=platform, language="pt", duration_s=duration,
                       hook_pattern="curiosity-gap", retention_3s_pct=retention)
    summary = hooks.perf_summary(min_samples=2)
    assert len(summary["patterns"]) == 3
    assert not any(row["sufficient_data"] for row in summary["patterns"])
    hooks.perf_add(platform="tiktok", language="pt", duration_s=20,
                   hook_pattern="curiosity-gap", retention_3s_pct=70)
    selected = hooks.perf_summary(platform="tiktok", language="pt", min_samples=2)
    short = next(row for row in selected["patterns"] if row["duration_bucket"] == "0-30s")
    assert short["avg_retention_3s"] == 80 and short["sufficient_data"]
    assert short["retention_samples"] == 2


def test_semantic_index_roundtrip_and_staleness(tmp_path, monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace
    import numpy as np
    from PIL import Image
    from ose import semantic

    class Tensor:
        def __init__(self, value):
            self.value = np.asarray(value, dtype=float)

        def unsqueeze(self, axis):
            return Tensor(np.expand_dims(self.value, axis))

        def mean(self, dim):
            return Tensor(self.value.mean(axis=dim))

        def norm(self):
            return Tensor(np.linalg.norm(self.value))

        def item(self):
            return self.value.item()

        def tolist(self):
            return self.value.tolist()

        def __truediv__(self, other):
            return Tensor(self.value / other.value)

        def __getitem__(self, index):
            return Tensor(self.value[index])

    encoder = SimpleNamespace(encode_image=lambda tensor: tensor,
                              encode_text=lambda tokens: Tensor([[0, 1]]))
    torch = SimpleNamespace(inference_mode=nullcontext,
                            cat=lambda tensors: Tensor(np.concatenate([t.value for t in tensors])),
                            isfinite=lambda tensor: np.isfinite(tensor.value))
    monkeypatch.setattr(semantic, "_backend", lambda *args: (
        encoder, lambda image: Tensor([image.getpixel((0, 0))[0], image.getpixel((0, 0))[2]]),
        lambda texts: texts, torch))
    monkeypatch.setattr(broll, "BROLL_DIR", tmp_path)
    monkeypatch.setattr(broll, "INDEX", tmp_path / "index.json")
    items = []
    for name in ("red", "blue"):
        thumbnail = tmp_path / f"{name}.png"
        Image.new("RGB", (4, 4), name).save(thumbnail)
        items.append({"id": name, "kind": "image", "thumbs": [str(thumbnail)]})
    write_json(broll.INDEX, items)
    assert semantic.build_index()["indexed"] == 2
    assert semantic.search("blue")[0]["id"] == "blue"
    Image.new("RGB", (4, 4), "green").save(tmp_path / "blue.png")
    with pytest.raises(OseError, match="stale"):
        semantic.search("blue")


def test_corpus_runner_requires_consent_and_leaves_unmeasured_values_null(tmp_path):
    from ose.benchmark import evaluate
    from ose.common import Project
    from ose.provenance import adopt
    p = Project(tmp_path / "project")
    p.root.mkdir()
    p.save_meta({"source": "input.mp4"})
    p.source.write_bytes(b"synthetic test source")
    words = [{"word": "Oi", "start": 0.1, "end": 0.5}]
    write_json(p.transcript, {"language": "pt", "words": words})
    write_json(p.edl, {"segments": [{"in": 0, "out": 1}]})
    adopt(p)
    case = {"id": "test", "project": "project", "reference_words": words, "expected_keep": [[0, 1]]}
    manifest = tmp_path / "corpus.json"
    write_json(manifest, {"schema_version": 1, "cases": [case]})
    with pytest.raises(OseError, match="consent"):
        evaluate(manifest, tmp_path / "result.json")
    case["consent_confirmed"] = True
    write_json(manifest, {"schema_version": 1, "cases": [case]})
    result = evaluate(manifest, tmp_path / "result.json")
    assert result["cases"][0]["wer"] == 0
    assert result["cases"][0]["crop_failure_rate"] is None
    assert result["cases"][0]["correction_minutes"] is None
