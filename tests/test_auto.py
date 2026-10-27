import hashlib

import pytest

from ose import captions, cut, pacing, qa, render, roughcut, transcribe
from ose.__main__ import build_parser, cmd_auto
from ose.common import OseError, Project, read_json, write_json


@pytest.fixture
def auto_project(tmp_path, monkeypatch):
    project = Project(tmp_path)
    project.save_meta({"source": "source.mp4"})
    write_json(project.transcript, {"words": [{"word": "Hi", "start": 0, "end": 1}]})
    write_json(project.edl, {"segments": [{"in": 0, "out": 1}], "reviewed": True})
    write_json(project.plan, {"captions": {"enabled": False}})
    calls = []
    monkeypatch.setattr(transcribe, "run_transcribe", lambda *args, **kwargs: calls.append("transcribe"))
    monkeypatch.setattr(roughcut, "run_roughcut", lambda *args, **kwargs: calls.append("roughcut"))
    monkeypatch.setattr(captions, "run_captions", lambda *args, **kwargs: calls.append("captions"))
    monkeypatch.setattr(cut, "render_cut", lambda *args, **kwargs: calls.append(("cut", kwargs)))
    monkeypatch.setattr(pacing, "run_pacing", lambda *args, **kwargs: calls.append("pacing"))
    monkeypatch.setattr(render, "run_render", lambda *args, **kwargs: {"out": str(project.final)})
    monkeypatch.setattr(qa, "run_qa", lambda *args, **kwargs: {"errors": 0, "warnings": 0, "contact_sheet": "sheet.jpg"})
    return project, calls


def test_auto_preserves_existing_edl_and_caption_choices(auto_project):
    project, calls = auto_project
    cmd_auto(build_parser().parse_args(["auto", str(project.root), "--draft"]))
    assert "roughcut" not in calls
    assert "transcribe" not in calls
    assert "captions" not in calls
    assert read_json(project.edl)["reviewed"] is True
    assert ("cut", {"reframe": "face", "draft": True}) in calls


def test_auto_rebuild_is_explicit(auto_project):
    project, calls = auto_project
    cmd_auto(build_parser().parse_args(["auto", str(project.root), "--rebuild-edl"]))
    assert "roughcut" in calls


def test_auto_rejects_edl_from_a_different_transcript(auto_project):
    project, calls = auto_project
    edl = read_json(project.edl)
    edl["transcript_sha256"] = hashlib.sha256(project.transcript.read_bytes()).hexdigest()
    write_json(project.edl, edl)
    write_json(project.transcript, {"words": [{"word": "Changed", "start": 2, "end": 3}]})
    with pytest.raises(OseError, match="transcript changed"):
        cmd_auto(build_parser().parse_args(["auto", str(project.root)]))
    assert not calls


def test_auto_exits_unsuccessfully_when_qa_fails(auto_project, monkeypatch):
    project, _ = auto_project
    monkeypatch.setattr(qa, "run_qa", lambda *args, **kwargs: {"errors": 1, "warnings": 0, "contact_sheet": "sheet.jpg"})
    with pytest.raises(SystemExit) as caught:
        cmd_auto(build_parser().parse_args(["auto", str(project.root)]))
    assert caught.value.code == 1