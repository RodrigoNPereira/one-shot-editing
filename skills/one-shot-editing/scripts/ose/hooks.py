"""Hook library (starter set + your own) and the performance log that ranks what works for your audience."""
from __future__ import annotations

import csv
import datetime as dt
import re
import math
from collections import defaultdict

from .common import ASSETS, OSE_HOME, PERF_CSV, OseError, read_json, strip_accents, write_json
from .locking import locked

USER_HOOKS = OSE_HOME / "hooks.user.json"
PERF_FIELDS = ["date", "platform", "url", "topic", "hook", "hook_pattern", "language", "duration_s", "views",
               "avg_view_duration_s", "retention_3s_pct", "completion_pct", "likes", "comments", "shares", "saves",
               "follows"]


def library() -> dict:
    base = read_json(ASSETS / "hooks.json")
    user = read_json(USER_HOOKS, {"hooks": []})
    base["hooks"] = base["hooks"] + [{**h, "user": True} for h in user["hooks"]]
    return base


def _words(t):
    return {w for w in re.findall(r"[a-z0-9]+", strip_accents((t or "").lower())) if len(w) > 2}


def list_hooks(*, pattern=None, lang="en", search=None, n=200) -> list[dict]:
    lib = library()
    q = _words(search)
    out = []
    for h in lib["hooks"]:
        if pattern and h["pattern"] != pattern:
            continue
        text = h.get(lang) or h.get("en") or h.get("pt")
        if q and not (q & _words(text + " " + h["pattern"] + " " + " ".join(lib["patterns"].get(h["pattern"], {}).get("best_for", [])))):
            continue
        out.append({"id": h["id"], "pattern": h["pattern"], "text": text, **({"user": True} if h.get("user") else {})})
    return out[:n]


def add_hook(*, pattern, en=None, pt=None) -> dict:
    lib = library()
    if pattern not in lib["patterns"]:
        raise OseError(f"unknown pattern {pattern}; one of {', '.join(lib['patterns'])}")
    if not (en or pt):
        raise OseError("give --en and/or --pt text")
    with locked(USER_HOOKS):
        user = read_json(USER_HOOKS, {"hooks": []})
        h = {"id": f"u{len(user['hooks']) + 1}", "pattern": pattern, **({"en": en} if en else {}), **({"pt": pt} if pt else {})}
        user["hooks"].append(h)
        write_json(USER_HOOKS, user)
    return h


def _num(v):
    try:
        number = float(str(v).replace(",", "").replace("%", "")) if str(v).strip() else None
        return number if number is not None and math.isfinite(number) else None
    except ValueError:
        return None


def perf_rows() -> list[dict]:
    if not PERF_CSV.exists():
        return []
    with PERF_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def perf_add(**kv) -> dict:
    row = {k: "" for k in PERF_FIELDS}
    row["date"] = dt.date.today().isoformat()
    for k, v in kv.items():
        if k in row and v is not None:
            row[k] = v
    PERF_CSV.parent.mkdir(parents=True, exist_ok=True)
    for key in PERF_FIELDS[7:]:
        if row[key] != "":
            value = _num(row[key])
            if value is None or value < 0 or (key.endswith("_pct") and value > 100):
                raise OseError(f"{key} must be nonnegative and percentages must be <= 100")
    with locked(PERF_CSV):
        new = not PERF_CSV.exists()
        with PERF_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=PERF_FIELDS)
            if new:
                w.writeheader()
            w.writerow(row)
    return row


def perf_summary(top=5, *, platform=None, language=None, min_samples=5) -> dict:
    if min_samples < 2:
        raise OseError("min_samples must be at least 2")
    with locked(PERF_CSV):
        rows = [row for row in perf_rows() if (not platform or row.get("platform") == platform)
                and (not language or row.get("language") == language)]
    if not rows:
        return {"videos": 0, "note": "no performance data yet; rank hooks by topic fit only"}
    by = defaultdict(list)
    for r in rows:
        duration = _num(r.get("duration_s"))
        bucket = "unknown" if duration is None else ("0-30s" if duration <= 30 else "31-60s" if duration <= 60 else ">60s")
        by[(r.get("platform") or "unknown", r.get("language") or "unknown", bucket,
            r.get("hook_pattern") or "unknown")].append(r)

    def avg(rs, key):
        vals = [x for x in (_num(r.get(key)) for r in rs) if x is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    patterns = []
    for (pf, lang, bucket, p), rs in by.items():
        observations = [value for row in rs if (value := _num(row.get("retention_3s_pct"))) is not None]
        n = len(observations)
        se = None
        if n >= 2:
            mean = sum(observations) / n
            se = math.sqrt(sum((value - mean) ** 2 for value in observations) / (n - 1) / n)
        patterns.append({"platform": pf, "language": lang, "duration_bucket": bucket,
                         "pattern": p, "videos": len(rs), "retention_samples": n,
                         "sufficient_data": n >= min_samples and "unknown" not in (pf, lang, bucket),
                         "retention_standard_error": round(se, 2) if se is not None else None,
                         "avg_views": avg(rs, "views"),
                         "avg_retention_3s": avg(rs, "retention_3s_pct"), "avg_completion": avg(rs, "completion_pct"),
                         "avg_shares": avg(rs, "shares")})
    # rank by 3s retention first (the hook's actual job), then views
    patterns.sort(key=lambda p: (p["platform"], p["language"], p["duration_bucket"],
                                not p["sufficient_data"], -(p["avg_retention_3s"] or 0)))
    best = sorted(rows, key=lambda r: _num(r.get("views")) or 0, reverse=True)[:top]
    return {"videos": len(rows), "patterns": patterns, "minimum_samples": min_samples,
            "note": "Compare patterns only within matching cohorts. Observational means are not causal evidence.",
            "best_videos": [{k: r.get(k) for k in ("date", "hook", "hook_pattern", "views", "retention_3s_pct", "topic")}
                            for r in best]}
