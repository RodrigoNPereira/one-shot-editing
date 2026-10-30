"""Pacing: make sure something changes on screen at least every N seconds; add zooms where it doesn't."""
from __future__ import annotations

import math

from .common import Project, load_plan, log, probe, read_json, segment_offsets, write_json


def visual_events(plan: dict, segments: list[dict], duration: float, count_jump_cuts=True):
    ev = {0.0, round(duration, 3)}
    if count_jump_cuts:
        ev |= {round(o, 3) for o in segment_offsets(segments)[1:]}
    covered = []
    for b in plan.get("broll", []):
        a, e = b["start"], b["start"] + b["duration"]
        ev |= {round(a, 3), round(e, 3)}
        if b.get("mode", "full") == "full":
            covered.append((a, e))
    for z in plan.get("zooms", []):
        ev |= {round(z["start"], 3), round(z["end"], 3)}
    hook = plan.get("hook") or {}
    if hook.get("text") and hook.get("on_screen", True):
        ev.add(round(min(hook.get("duration", 2.6), duration), 3))
    cta = plan.get("cta") or {}
    if cta.get("text") and cta.get("on_screen", True):
        st = cta.get("start")
        ev.add(round(max(duration - cta.get("duration", 2.8), 0) if st is None else st, 3))
    for t in plan.get("texts", []):
        ev |= {round(t["start"], 3), round(t["end"], 3)}
    return sorted(e for e in ev if 0 <= e <= duration), covered


def analyse(plan, segments, duration, max_gap=3.0, count_jump_cuts=True) -> dict:
    events, covered = visual_events(plan, segments, duration, count_jump_cuts)
    gaps = []
    for a, b in zip(events, events[1:]):
        if b - a > max_gap:
            inside = any(ca - 1e-3 <= a and b <= ce + 1e-3 for ca, ce in covered)
            gaps.append({"start": round(a, 2), "end": round(b, 2), "length": round(b - a, 2), "under_broll": inside})
    intervals = [b - a for a, b in zip(events, events[1:])]
    return {"events": len(events) - 2, "max_static": round(max(intervals, default=0), 2),
            "avg_interval": round(sum(intervals) / max(len(intervals), 1), 2),
            "changes_per_10s": round(10 * (len(events) - 2) / max(duration, 0.1), 1),
            "gaps": gaps, "ok": not gaps}


def fill_gaps(plan, gaps, target=2.4, scale=1.12, style="smooth"):
    """Insert alternating zoom-in intervals into long static stretches."""
    added = []
    for g in gaps:
        if g["under_broll"]:
            continue
        a, b = g["start"], g["end"]
        k = math.ceil((b - a) / target)
        pts = [a + (b - a) * i / k for i in range(1, k)] + [b]
        # zoom in on [p1,p2], [p3,p4], ... so every change point is either a zoom start or end
        for i in range(0, len(pts) - 1, 2):
            z = {"start": round(pts[i], 3), "end": round(pts[i + 1], 3), "scale": scale, "style": style, "auto": True}
            added.append(z)
    plan.setdefault("zooms", []).extend(added)
    plan["zooms"].sort(key=lambda z: z["start"])
    return added


def jumpcut_zooms(plan, segments, scale=1.08):
    """Alternate framing on every other jump cut (punch-in), so cuts read as intentional."""
    offs = segment_offsets(segments)
    taken = [(z["start"], z["end"]) for z in plan.get("zooms", [])]
    added = []
    for i, (s, o) in enumerate(zip(segments, offs)):
        if i % 2 == 0:
            continue
        a, b = o, o + s["out"] - s["in"]
        if any(a < te and ta < b for ta, te in taken):
            continue
        z = {"start": round(a, 3), "end": round(b, 3), "scale": scale, "style": "punch", "auto": True}
        plan.setdefault("zooms", []).append(z)
        added.append(z)
    plan["zooms"].sort(key=lambda z: z["start"])
    return added


def run_pacing(project: Project, *, max_gap=3.0, apply=False, jumpcut=False, scale=1.12, style="smooth",
               reset_auto=False) -> dict:
    project.require()
    from .common import OseError, validate_plan
    from .provenance import check_cut, check_plan_revision
    if not math.isfinite(max_gap) or max_gap <= 0:
        raise OseError("pacing max gap must be finite and positive")
    check_cut(project)
    plan = load_plan(project)
    current = check_plan_revision(project, plan)
    segments = read_json(project.cut_words)["segments"]
    duration = probe(project.cut)["duration"]
    if reset_auto:
        plan["zooms"] = [z for z in plan.get("zooms", []) if not z.get("auto")]
    before = analyse(plan, segments, duration, max_gap)
    result = {"before": before}
    if apply:
        added = jumpcut_zooms(plan, segments) if jumpcut else []
        gaps = analyse(plan, segments, duration, max_gap)["gaps"]
        added += fill_gaps(plan, gaps, target=max_gap * 0.8, scale=scale, style=style)
        plan["edl_revision"] = current
        validate_plan(plan, duration)
        write_json(project.plan, plan)
        result["added_zooms"] = len(added)
        result["after"] = analyse(plan, segments, duration, max_gap)
        log(f"pacing: added {len(added)} zooms; max static {result['after']['max_static']}s")
    else:
        log(f"pacing: max static {before['max_static']}s, {len(before['gaps'])} gaps > {max_gap}s")
    return result
