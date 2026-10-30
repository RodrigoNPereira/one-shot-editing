import os

import pytest

from ose.common import OseError, Project, load_edl, load_plan, normalize_plan, read_json, validate_plan, write_json
from ose.provenance import adopt, check_cut, check_plan_revision, edl_revision, record_cut
from ose.quality import settings
from ose.review import approve, approved


@pytest.fixture
def recorded_project(tmp_path, monkeypatch):
    from ose import common
    p = Project(tmp_path)
    p.save_meta({"source": "source.mp4"})
    p.source.write_bytes(b"source1")
    write_json(p.transcript, {"language": "en", "words": [{"word": "Hi", "start": 0, "end": 1}]})
    write_json(p.edl, {"segments": [{"in": 0, "out": 1}]})
    adopt(p)
    write_json(p.plan, {"output": {"profile": "source"}})
    p.cut.write_bytes(b"cut")
    write_json(p.cut_words, {"words": [{"word": "Hi", "start": 0, "end": 1}],
                             "segments": [{"in": 0, "out": 1}]})
    info = {"width": 90, "height": 160, "fps_ratio": "60/1", "pix_fmt": "yuv420p10le"}
    monkeypatch.setattr(common, "probe", lambda path: info)
    record_cut(p, settings(info, load_plan(p)), "center", False)
    return p


@pytest.mark.parametrize("plan, error", [
    ({"zooms": [{"start": -1, "end": 1}]}, "start"),
    ({"zooms": [{"start": 2, "end": 1}]}, "after start"),
    ({"zooms": [{"start": 0, "end": 1, "scale": 0.5}]}, "scale"),
    ({"broll": [{"asset": "a", "start": 0, "duration": -1}]}, "duration"),
    ({"texts": [{"start": 0, "end": 1}]}, "text"),
    ({"platform": "typo"}, "platform"),
    ({"audio": {"lufs": float("nan")}}, "finite"),
    ({"captions": {"words_per_chunk": 0}}, "words_per_chunk"),
    ({"schema_version": 2}, "schema_version"),
    ({"outpt": {}}, "outpt"),
    ({"zooms": [{"start": "oops", "end": 1}]}, "start"),
    ({"sfx": "not a list"}, "sfx"),
    ({"cta": 3}, "cta"),
])
def test_plan_rejects_invalid_values(plan, error):
    with pytest.raises(OseError, match=error):
        validate_plan(normalize_plan(plan))


def test_plan_checks_bounds_and_consistency():
    with pytest.raises(OseError, match="after the cut"):
        validate_plan({"texts": [{"text": "Hi", "start": 1, "end": 3}]}, duration=2)
    with pytest.raises(OseError, match="inconsistent"):
        normalize_plan({"zooms": [{"start": 1, "end": 3, "duration": 7}]})


def test_source_replacement_detected_even_with_unchanged_stat(recorded_project):
    p = recorded_project
    stat = p.source.stat()
    p.source.write_bytes(b"source2")
    os.utime(p.source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(OseError, match="source footage changed"):
        load_edl(p)


@pytest.mark.parametrize("artifact", ["edl", "transcript", "cut", "cut_words", "plan"])
def test_cut_rejects_changed_dependencies(recorded_project, artifact):
    p = recorded_project
    if artifact == "cut":
        p.cut.write_bytes(b"replaced")
    else:
        path = getattr(p, artifact)
        document = read_json(path)
        if artifact == "edl":
            document["segments"][0]["out"] = 0.9
        elif artifact in ("transcript", "cut_words"):
            document["words"][0]["word"] = "Changed"
        else:
            document["framing"] = {"center": 0.3}
        write_json(path, document)
    with pytest.raises(OseError):
        check_cut(p)


def test_timed_plan_and_approval_are_bound_to_edit(recorded_project):
    p = recorded_project
    plan = {"texts": [{"text": "Hello", "start": 0, "end": 0.9}]}
    with pytest.raises(OseError, match="timed plan"):
        check_plan_revision(p, plan)
    plan["edl_revision"] = edl_revision(p)
    check_plan_revision(p, plan)
    approve(p, stage="cut", note="Reviewed every deletion with source context")
    assert approved(p, "cut")
    edl = read_json(p.edl)
    edl["segments"][0]["out"] = 0.8
    write_json(p.edl, edl)
    assert not approved(p, "cut")
    with pytest.raises(OseError, match="timed plan"):
        check_plan_revision(p, plan)


def test_source_profile_preserves_native_detail_and_rate():
    result = settings({"width": 3840, "height": 2160, "fps_ratio": "60000/1001",
                       "nominal_fps_ratio": "60000/1001", "pix_fmt": "yuv420p10le"}, {})
    assert result["height"] == 2160
    assert result["width"] > 1080
    assert result["fps"] == "60000/1001"
    assert result["pix_fmt"] == "yuv420p10le"


@pytest.mark.parametrize("extra, error", [
    ({"color_transfer": "smpte2084"}, "HDR"),
    ({"nominal_fps_ratio": "60/1"}, "frame rate"),
    ({"sample_aspect_ratio": "4:3"}, "square pixels"),
    ({"pix_fmt": "yuv420p12le"}, "support"),
])
def test_source_quality_never_silently_downgrades(extra, error):
    with pytest.raises(OseError, match=error):
        settings({"width": 1080, "height": 1920, "fps_ratio": "30/1", **extra}, {})


def test_vfr_is_detected_even_when_header_claims_constant_rate(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    from ose import quality
    p = Project(tmp_path)
    p.save_meta({"source": "input.mp4"})
    monkeypatch.setattr(quality, "run", lambda *args, **kwargs: SimpleNamespace(stdout=json.dumps({
        "frames": [{"best_effort_timestamp_time": t} for t in (0, 0.02, 0.0666667, 0.1)],
    })))
    with pytest.raises(OseError, match="variable frame timestamps"):
        quality.verify_cfr(p, {"fps_ratio": "30/1", "time_base": "1/15360"}, "source-hash")
