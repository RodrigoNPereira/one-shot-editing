"""Content-addressed dependencies, separate from creative decisions."""
from __future__ import annotations

import hashlib
import json

from .common import ASSETS, OseError, read_json, transcript_fingerprint, write_json


def digest(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError as error:
        raise OseError(f"cannot fingerprint {path}: {error}") from error
    return h.hexdigest()


def revision(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def edl_revision(project):
    edl = read_json(project.edl)
    return revision({"segments": edl["segments"], "transcript": edl.get("transcript_sha256"),
                     "source": edl.get("source_sha256")})


def check_source(project, transcript=None):
    transcript = read_json(project.transcript) if transcript is None else transcript
    expected = transcript.get("source_sha256")
    if not expected:
        raise OseError("transcript has no source provenance; re-transcribe, or explicitly adopt it with `ose provenance --adopt` after review")
    if not project.source.is_file() or digest(project.source) != expected:
        raise OseError("source footage changed; re-transcribe and review the cut before continuing")
    return expected


def adopt(project):
    """Explicit migration for manually supplied or legacy transcripts."""
    project.require()
    tr = read_json(project.transcript)
    tr["source_sha256"] = digest(project.source)
    tr["provenance"] = "explicit-user-adoption"
    write_json(project.transcript, tr)
    if project.edl.exists():
        edl = read_json(project.edl)
        edl.update(source_sha256=tr["source_sha256"], transcript_sha256=transcript_fingerprint(tr),
                   transcript_fingerprint_version=1)
        write_json(project.edl, edl)
    return {"source_sha256": tr["source_sha256"], "note": "Adopted current source/transcript; run cut to rebuild intermediates"}


def has_timed_items(plan):
    return any(plan.get(k) for k in ("broll", "zooms", "texts", "sfx")) or plan.get("cta", {}).get("start") is not None


def check_plan_revision(project, plan):
    current = edl_revision(project)
    if has_timed_items(plan) and plan.get("edl_revision") != current:
        raise OseError("timed plan belongs to a different or unreviewed EDL; review placements, then run `ose plan --accept-timeline`")
    return current


def render_assets(plan):
    from . import broll, music, sfx
    result = {f"font:{path.name}": digest(path) for path in sorted((ASSETS / "fonts").glob("*.ttf"))}
    for index, item in enumerate(plan.get("broll", [])):
        result[f"broll:{index}:{item['asset']}"] = digest(broll.resolve(item["asset"])["path"])
    if plan.get("music", {}).get("track"):
        result["music"] = digest(music.resolve(plan["music"]["track"])["path"])
    for index, item in enumerate(plan.get("sfx", [])):
        result[f"sfx:{index}:{item['asset']}"] = digest(sfx.resolve(item["asset"]))
    return result


def cut_inputs(project, config, reframe):
    tr = read_json(project.transcript)
    return {"source": check_source(project, tr), "transcript": transcript_fingerprint(tr),
            "edl": edl_revision(project), "quality": config, "reframe": reframe,
            "framing": read_json(project.plan, {}).get("framing", {})}


def record_cut(project, config, reframe, draft):
    write_json(project.work / "cut.provenance.json",
               {"inputs": cut_inputs(project, config, reframe), "draft": draft,
                "cut": digest(project.cut), "words": digest(project.cut_words)})


def check_cut(project, *, allow_draft=True):
    from .common import load_edl, load_plan, probe
    from .quality import settings
    load_edl(project)
    record = read_json(project.work / "cut.provenance.json", {})
    if not record:
        raise OseError("cut has no provenance; run `ose cut`")
    mode = record["inputs"]["reframe"]
    config = settings(probe(project.source), load_plan(project), reframe=mode)
    if record["inputs"] != cut_inputs(project, config, mode):
        raise OseError("cut is stale (source, EDL, transcript, framing or quality changed); run `ose cut`")
    if digest(project.cut) != record["cut"] or digest(project.cut_words) != record["words"]:
        raise OseError("cut media or remapped words changed; run `ose cut`")
    if not allow_draft and record["draft"]:
        raise OseError("draft cut cannot be used for final output")
    return record
