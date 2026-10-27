"""Rough cut: build an edit decision list (EDL) from word timestamps.

Removes filler words, stutters, false starts, repeated takes (keeping the better one) and
compresses every pause/breath to a tight gap. Output is `work/edl.json`, the single source of
truth for every later step. All decisions are listed with ids so they can be reverted
(`--keep r3,r7`) or extended (`--cut 12.4-15.0`).
"""
from __future__ import annotations

import math

from .common import OseError, Project, cut_duration, fmt_time, log, norm_token, probe, read_json, strip_accents, transcript_fingerprint, write_json

FILLERS = {
    "en": {"um", "umm", "ummm", "uh", "uhh", "uhm", "erm", "er", "ah", "ahh", "hmm", "hm", "mm", "mmm", "mhm"},
    "pt": {"hã", "ãh", "ã", "ahn", "hum", "hmm", "hm", "éé", "ééé", "éééé", "eh", "ehh", "uhm", "ah", "ahh", "mmm"},
    "es": {"eh", "ehh", "em", "emm", "mmm", "hmm", "ah", "uhm"},
}
# Words that are fillers only sometimes; removed with --aggressive.
SOFT_FILLERS = {
    "en": {"like", "basically", "literally", "actually", ("you", "know"), ("i", "mean"), ("kind", "of"), ("sort", "of")},
    "pt": {"tipo", "né", ("tipo", "assim"), ("sabe",), ("vamos", "dizer"), ("quer", "dizer")},
    "es": {("o", "sea"), "pues", "bueno", ("es", "que")},
}
SENTENCE_END = (".", "?", "!", "…")
MEANING_WORDS = set((
    "no not never neither nor without cannot cant wont dont isnt arent wasnt werent wouldnt shouldnt couldnt "
    "nao nunca jamais nem sem tampoco ni sin "
    "zero one two three four five six seven eight nine ten eleven twelve hundred thousand million billion "
    "um uma dois duas tres quatro cinco seis sete oito nove dez cem mil milhao "
    "uno una dos cuatro siete ocho nueve diez cien"
).split())

PACE = {
    # max_gap: pauses longer than this are cut; pads: silence kept before/after speech at each cut.
    "tight": {"max_gap": 0.22, "pad_before": 0.05, "pad_after": 0.08},
    "natural": {"max_gap": 0.45, "pad_before": 0.10, "pad_after": 0.16},
    "loose": {"max_gap": 0.80, "pad_before": 0.15, "pad_after": 0.25},
}


def _ratio(a: str, b: str) -> float:
    from rapidfuzz import fuzz
    return fuzz.ratio(a, b)


def _phrase_text(words, idx):
    return " ".join(norm_token(words[i]["word"]) for i in idx if norm_token(words[i]["word"]))


def _phrase_score(words, idx, removed):
    probs = [words[i].get("prob", 1.0) for i in idx]
    fill = sum(1 for i in idx if removed.get(i, ("",))[0] in ("filler", "stutter"))
    complete = words[idx[-1]]["word"].rstrip().endswith(SENTENCE_END)
    return sum(probs) / len(probs) - 0.08 * fill + (0.05 if complete else 0)


def _meaning_tokens(words, indices):
    tokens = []
    for index in indices:
        raw = words[index]["word"].lower().replace("’", "'")
        token = strip_accents(norm_token(raw))
        if any(character.isdigit() for character in raw):
            tokens.append(raw.strip(".,;:!? "))
        elif token in MEANING_WORDS or token.endswith("n't"):
            tokens.append(token)
    return tokens


def parse_ranges(spec: str | None) -> list[tuple[float, float]]:
    out = []
    if not spec:
        return out
    for part in (spec or "").split(","):
        try:
            start, end = (float(value) for value in part.split("-", 1))
        except ValueError as error:
            raise OseError(f"invalid time range {part!r}; use START-END in seconds") from error
        _validate_range(start, end)
        out.append((start, end))
    return out


def _validate_range(start, end, duration=None):
    if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
        raise OseError(f"invalid time range: {start}-{end}")
    if duration is not None and end > duration:
        raise OseError(f"time range {start}-{end} exceeds source duration {duration}")


def build_edl(words: list[dict], *, language="en", duration=None, pace="tight", aggressive=False,
              prefer="last", keep_ids=(), cut_ranges=(), lookahead=3, max_retake_gap=20.0) -> dict:
    if not words:
        raise OseError("transcript has no words; transcribe or correct it before cutting")
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise OseError("source duration must be finite and positive")
    previous_start = 0.0
    for index, word in enumerate(words):
        try:
            start, end = word["start"], word["end"]
            valid = (math.isfinite(start) and math.isfinite(end) and previous_start <= start < end
                     and (duration is None or end <= duration + 0.001))
        except (KeyError, TypeError) as error:
            raise OseError(f"invalid word timestamp at index {index}") from error
        if not valid:
            raise OseError(f"invalid word timestamp at index {index}: {start}-{end}")
        previous_start = start
    duration = duration if duration is not None else words[-1]["end"] + 0.5
    for start, end in cut_ranges:
        _validate_range(start, end, duration)
    lang = (language or "en")[:2]
    p = PACE[pace]
    n = len(words)
    toks = [norm_token(w["word"]) for w in words]
    removed: dict[int, tuple[str, str]] = {}  # word index -> (reason, decision id)
    decisions: list[dict] = []
    review: list[dict] = []
    keep_ids = set(keep_ids)

    def decide(reason, idxs, detail=""):
        did = f"r{len(decisions) + 1}"
        decisions.append({"id": did, "reason": reason, "start": words[idxs[0]]["start"], "end": words[idxs[-1]]["end"],
                          "text": " ".join(words[i]["word"] for i in idxs), "detail": detail,
                          "kept": did in keep_ids})
        if did not in keep_ids:
            for i in idxs:
                removed.setdefault(i, (reason, did))

    # 1. fillers
    hard = FILLERS.get(lang, FILLERS["en"])
    soft = SOFT_FILLERS.get(lang, set()) if aggressive else set()
    soft_multi = sorted((s for s in soft if isinstance(s, tuple)), key=lambda sequence: (-len(sequence), sequence))
    soft_single = {s for s in soft if isinstance(s, str)}
    i = 0
    while i < n:
        matched = False
        for seq in soft_multi:
            if tuple(toks[i:i + len(seq)]) == seq:
                decide("filler", list(range(i, i + len(seq))), "soft")
                i += len(seq)
                matched = True
                break
        if matched:
            continue
        if toks[i] in hard or toks[i] in soft_single:
            decide("filler", [i], "hard" if toks[i] in hard else "soft")
        i += 1

    # 2. stutters: "I I think" / "the the" / "we should we should"
    for i in range(n - 1):
        if i in removed or not toks[i]:
            continue
        if toks[i] == toks[i + 1] and words[i + 1]["start"] - words[i]["end"] < 0.7:
            decide("stutter", [i])
            continue
        repeated_pair = i + 3 < n and toks[i:i + 2] == toks[i + 2:i + 4] and all(toks[i:i + 2])
        if repeated_pair and words[i + 2]["start"] - words[i + 1]["end"] < 0.7:
            decide("stutter", [i, i + 1])

    # 3. phrases over the remaining words (split on pauses and sentence ends)
    phrases: list[list[int]] = []
    cur: list[int] = []
    for i in range(n):
        if i in removed:
            continue
        if cur and (words[i]["start"] - words[cur[-1]]["end"] > 0.45 or
                    words[cur[-1]]["word"].rstrip().endswith(SENTENCE_END)):
            phrases.append(cur)
            cur = []
        cur.append(i)
    if cur:
        phrases.append(cur)

    # 4. retakes and false starts
    dropped = set()
    for a in range(len(phrases)):
        if a in dropped:
            continue
        ta = _phrase_text(words, phrases[a])
        na = len(ta.split())
        if na < 2:
            continue
        for b in range(a + 1, min(a + 1 + lookahead, len(phrases))):
            if b in dropped:
                continue
            if words[phrases[b][0]]["start"] - words[phrases[a][-1]]["end"] > max_retake_gap:
                break
            tb = _phrase_text(words, phrases[b])
            nb = len(tb.split())
            full = min(na, nb) >= 3 and _ratio(ta, tb) >= 78
            prefix = (not full and na <= nb and tb.split()[0] == ta.split()[0]
                      and _ratio(ta, " ".join(tb.split()[:na])) >= 85)
            if not (full or prefix):
                continue
            if _meaning_tokens(words, phrases[a]) != _meaning_tokens(words, phrases[b]):
                review.append({"reason": "meaning-change", "start": words[phrases[a][0]]["start"],
                               "end": words[phrases[a][-1]]["end"], "text": ta,
                               "candidate_start": words[phrases[b][0]]["start"], "candidate": tb})
                continue
            loser = a
            if full and prefer == "best":
                sa = _phrase_score(words, phrases[a], removed)
                sb = _phrase_score(words, phrases[b], removed)
                loser = b if sa > sb + 0.08 else a
            dropped.add(loser)
            kind = "retake" if full else "false-start"
            decide(kind, phrases[loser], f"kept take at {fmt_time(words[phrases[b if loser == a else a][0]]['start'])}")
            break

    # 5. forced cuts
    for (ca, cb) in cut_ranges:
        idx = [i for i in range(n) if words[i]["start"] >= ca - 0.01 and words[i]["end"] <= cb + 0.01]
        if idx:
            decide("manual", idx, f"{ca}-{cb}")

    # 6. segments: runs of kept words, cut wherever a pause is too long or a word was removed
    segments = []
    run_start = None
    for i in range(n):
        if i in removed:
            continue
        if run_start is None:
            run_start = i
        nxt = next((j for j in range(i + 1, n) if j not in removed), None)
        contiguous = nxt == i + 1 and words[nxt]["start"] - words[i]["end"] <= p["max_gap"]
        if not contiguous:
            prev_end = words[run_start - 1]["end"] if run_start > 0 else 0.0
            next_start = words[i + 1]["start"] if i + 1 < n else duration
            s = max(words[run_start]["start"] - p["pad_before"], prev_end, 0.0)
            e = min(words[i]["end"] + p["pad_after"], next_start, duration)
            if segments and s - segments[-1]["out"] < 0.04:
                segments[-1]["out"] = round(e, 3)
            else:
                segments.append({"in": round(s, 3), "out": round(e, 3)})
            run_start = None
    for cs, ce in cut_ranges:  # also strip forced ranges that contain no words
        segments = [x for seg in segments for x in _subtract(seg, cs, ce)]

    removed_time = sum(d["end"] - d["start"] for d in decisions if not d["kept"])
    return {
        "segments": segments,
        "decisions": decisions,
        "review": review,
        "params": {"pace": pace, **p, "aggressive": aggressive, "prefer": prefer, "language": lang},
        "stats": {
            "source_duration": round(duration, 2),
            "cut_duration": round(cut_duration(segments), 2),
            "segments": len(segments),
            "removed_speech_s": round(removed_time, 2),
            "by_reason": _count(decisions),
            "review_required": len(review),
        },
    }


def _subtract(seg, a, b):
    if b <= seg["in"] or a >= seg["out"]:
        return [seg]
    out = []
    if a > seg["in"]:
        out.append({"in": seg["in"], "out": round(a, 3)})
    if b < seg["out"]:
        out.append({"in": round(b, 3), "out": seg["out"]})
    return out


def _count(decisions):
    c = {}
    for d in decisions:
        if not d["kept"]:
            c[d["reason"]] = c.get(d["reason"], 0) + 1
    return c


def run_roughcut(project: Project, *, pace="tight", aggressive=False, prefer="last", keep="", cut="",
                 hook_range=None) -> dict:
    project.require()
    tr = read_json(project.transcript)
    duration = probe(project.source)["duration"]
    hook = parse_ranges(hook_range)
    if hook_range:
        if len(hook) != 1:
            raise OseError("hook range must contain exactly one START-END interval")
        _validate_range(*hook[0], duration)
    edl = build_edl(tr["words"], language=tr.get("language", "en"), duration=duration, pace=pace,
                    aggressive=aggressive, prefer=prefer,
                    keep_ids=[k.strip() for k in keep.split(",") if k.strip()],
                    cut_ranges=parse_ranges(cut))
    if hook:
        (ha, hb), = hook
        rest = [x for seg in edl["segments"] for x in _subtract(seg, ha, hb)]  # don't play the line twice
        edl["segments"] = [{"in": ha, "out": hb, "hook": True}, *[x for x in rest if x["out"] - x["in"] > 0.05]]
        edl["stats"]["segments"] = len(edl["segments"])
        edl["stats"]["cut_duration"] = round(cut_duration(edl["segments"]), 2)
    edl["source"] = str(project.source)
    edl["transcript_sha256"] = transcript_fingerprint(tr)
    edl["transcript_fingerprint_version"] = 1
    write_json(project.edl, edl)
    s = edl["stats"]
    log(f"rough cut: {s['source_duration']}s -> {s['cut_duration']}s, {s['segments']} segments, removed {s['by_reason']}")
    return edl


def report(edl: dict) -> str:
    lines = [f"{d['id']:>4} {'KEPT ' if d['kept'] else 'CUT  '}{d['reason']:<12} {fmt_time(d['start'])}  "
             f"{d['text'][:70]!r} {d['detail']}" for d in edl["decisions"]]
    lines.extend(f"REVIEW {item['reason']} {fmt_time(item['start'])} {item['text']!r} vs "
                 f"{fmt_time(item['candidate_start'])} {item['candidate']!r} (both preserved)"
                 for item in edl.get("review", []))
    s = edl["stats"]
    lines.append(f"\n{s['source_duration']}s -> {s['cut_duration']}s ({s['segments']} segments)")
    return "\n".join(lines)
