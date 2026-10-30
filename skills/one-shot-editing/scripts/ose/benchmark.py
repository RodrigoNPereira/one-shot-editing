"""Evaluate locally supplied, consented EN/PT-BR recordings; no fabricated quality scores."""
from __future__ import annotations

import math
from pathlib import Path

from .common import OseError, Project, load_edl, norm_token, read_json, write_json


def word_metrics(reference, actual):
    from rapidfuzz.distance import Levenshtein
    if not reference:
        raise OseError("benchmark reference_words must be nonempty")
    for word in [*reference, *actual]:
        if not isinstance(word.get("word"), str) or not all(
                isinstance(word.get(key), (float, int)) and math.isfinite(word[key]) for key in ("start", "end")):
            raise OseError("benchmark words need text and finite start/end")
        if not 0 <= word["start"] < word["end"]:
            raise OseError("benchmark word end must be after start")
    ref = [norm_token(word["word"]) for word in reference]
    got = [norm_token(word["word"]) for word in actual]
    errors = Levenshtein.distance(ref, got)
    offsets = []
    for tag, a, b, c, _ in Levenshtein.opcodes(ref, got):
        if tag == "equal":
            for index in range(b - a):
                offsets.extend(abs(reference[a + index][key] - actual[c + index][key]) for key in ("start", "end"))
    return {"wer": errors / len(ref), "word_errors": errors, "reference_words": len(ref),
            "aligned_words": len(offsets) // 2,
            "boundary_mae_s": sum(offsets) / len(offsets) if offsets else None}


def _union(intervals):
    out = []
    for start, end in sorted(intervals):
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            raise OseError("benchmark intervals must be finite, positive ranges")
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out


def deletion_metrics(expected_keep, segments):
    expected = _union(expected_keep)
    actual = _union([(segment["in"], segment["out"]) for segment in segments])
    expected_s = sum(end - start for start, end in expected)
    actual_s = sum(end - start for start, end in actual)
    intersection = sum(max(0, min(b, d) - max(a, c)) for a, b in expected for c, d in actual)
    return {"incorrectly_deleted_s": max(0, expected_s - intersection),
            "unwanted_retained_s": max(0, actual_s - intersection), "expected_keep_s": expected_s}


def evaluate(manifest, out):
    path = Path(manifest).resolve()
    corpus = read_json(path)
    if corpus.get("schema_version") != 1 or not corpus.get("cases"):
        raise OseError("benchmark needs schema_version=1 and nonempty cases")
    rows = []
    for case in corpus["cases"]:
        if case.get("consent_confirmed") is not True:
            raise OseError(f"case {case.get('id')}: confirm recording/benchmark consent before evaluation")
        project = Project(path.parent / case["project"]).require()
        edl = load_edl(project)
        transcript = read_json(project.transcript)
        if transcript.get("language") not in ("en", "pt"):
            raise OseError("benchmark currently requires EN/PT-BR projects")
        human = case.get("human_review", {})
        for key in ("crop_failures", "reviewed_frames", "correction_minutes"):
            if key in human and (not isinstance(human[key], (int, float)) or
                                 not math.isfinite(human[key]) or human[key] < 0):
                raise OseError(f"human_review.{key} must be finite and nonnegative")
        failures, frames = human.get("crop_failures"), human.get("reviewed_frames")
        if failures is not None and (not frames or failures > frames):
            raise OseError("crop_failures requires reviewed_frames >= crop_failures and > 0")
        rows.append({"id": case["id"], "language": transcript["language"],
                     **word_metrics(case["reference_words"], transcript["words"]),
                     **deletion_metrics(case["expected_keep"], edl["segments"]),
                     "transcription_seconds": transcript.get("elapsed_s"),
                     "crop_failure_rate": failures / frames if failures is not None else None,
                     "correction_minutes": human.get("correction_minutes")})
    result = {"cases": rows, "recordings": len(rows),
              "languages": sorted({row["language"] for row in rows}),
              "note": "Missing human annotations remain null. This does not measure viewer retention."}
    write_json(out, result)
    return result
