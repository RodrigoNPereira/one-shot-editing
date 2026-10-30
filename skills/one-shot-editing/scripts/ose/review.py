"""Contextual deletion previews and approvals tied to immutable edit revisions."""
from __future__ import annotations

import datetime as dt
import tempfile
from pathlib import Path

from .common import OseError, ffmpeg, load_edl, load_plan, probe, read_json, write_json
from .provenance import digest, edl_revision, render_assets, revision


def approvals(project):
    return read_json(project.work / "approvals.json", [])


def approve(project, *, stage, note):
    if not note.strip():
        raise OseError("approval needs a nonempty review rationale")
    load_edl(project)
    record = {"stage": stage, "note": note.strip(), "edl_revision": edl_revision(project),
              "date": dt.datetime.now(dt.timezone.utc).isoformat()}
    if stage == "final":
        from .provenance import check_cut
        check_cut(project, allow_draft=False)
        if not project.final.is_file():
            raise OseError("render the final before approving it")
        rendered = read_json(project.final.with_suffix(".mp4.provenance.json"))
        if (rendered["plan_sha256"] != revision(load_plan(project)) or rendered["file_sha256"] != digest(project.final)
                or rendered.get("assets") != render_assets(load_plan(project))):
            raise OseError("final output is stale; render again before approval")
        record.update(plan_sha256=revision(load_plan(project)), file_sha256=digest(project.final),
                      assets=rendered["assets"])
    records = approvals(project)
    records.append(record)
    write_json(project.work / "approvals.json", records)
    return record


def approved(project, stage, target=None):
    current = edl_revision(project)
    matches = [item for item in approvals(project) if item["stage"] == stage and item["edl_revision"] == current]
    if stage == "final":
        target = target or project.final
        matches = [item for item in matches if item.get("plan_sha256") == revision(load_plan(project))
                   and item.get("assets") == render_assets(load_plan(project))
                   and target.is_file() and item.get("file_sha256") == digest(target)]
    return bool(matches)


def removed_ranges(segments, duration):
    merged = []
    for segment in sorted(segments, key=lambda item: item["in"]):
        if merged and segment["in"] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], segment["out"])
        else:
            merged.append([segment["in"], segment["out"]])
    cursor, removed = 0.0, []
    for start, end in merged:
        if start > cursor + 0.02:
            removed.append((cursor, start))
        cursor = end
    if duration > cursor + 0.02:
        removed.append((cursor, duration))
    return removed


def deletion_reel(project, context=0.5):
    if not 0 <= context <= 5:
        raise OseError("review context must be between 0 and 5 seconds")
    edl = load_edl(project)
    info = probe(project.source)
    ranges = removed_ranges(edl["segments"], info["duration"])
    if not ranges:
        return {"clips": 0, "note": "nothing was removed"}
    project.out.mkdir(parents=True, exist_ok=True)
    output = project.out / "deletion_review.mp4"
    manifest, offset = [], 0.0
    with tempfile.TemporaryDirectory(prefix="review-", dir=project.work) as temp:
        temp = Path(temp)
        for i, (start, end) in enumerate(ranges):
            a, b = max(0, start - context), min(info["duration"], end + context)
            # A red border marks the deletion; the handles show its original context.
            vf = (f"scale=640:-2,fps=30,drawbox=x=0:y=0:w=iw:h=ih:color=red:t=8:"
                  f"enable='between(t,{start - a},{end - a})'")
            ffmpeg(["-ss", str(a), "-t", str(b - a), "-i", project.source,
                    "-vf", vf, "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                    "-c:a", "aac", "-ar", "48000", temp / f"{i}.mp4"])
            actual = probe(temp / f"{i}.mp4")["duration"]
            manifest.append({"source_start": a, "source_end": b, "removed_start": start, "removed_end": end,
                             "reel_start": offset, "reel_end": offset + actual})
            offset += actual
        (temp / "concat.txt").write_text("".join(f"file '{i}.mp4'\n" for i in range(len(ranges))))
        ffmpeg(["-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", output], cwd=temp)
    write_json(project.out / "deletion_review.json", {"edl_revision": edl_revision(project), "clips": manifest})
    return {"file": str(output), "clips": len(manifest), "legend": "red border = removed footage; surrounding footage = context"}
