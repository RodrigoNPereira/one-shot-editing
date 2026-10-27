import json
from types import SimpleNamespace

import pytest

from ose import qa
from ose.__main__ import cmd_qa
from ose.common import OseError, Project, write_json


@pytest.fixture
def qa_project(tmp_path, monkeypatch):
    project = Project(tmp_path)
    project.save_meta({"source": "raw.mp4"})
    project.out.mkdir()
    write_json(project.plan, {"hook": {"text": "Hook"}, "cta": {"text": "Save"}})
    write_json(project.cut_words, {"words": [{"word": "Hello", "start": 0.1, "end": 0.5}]})
    write_json(project.edl, {"segments": [{"in": 0, "out": 20}]})
    monkeypatch.setattr(qa, "probe", lambda path: {
        "width": 1080, "height": 1920, "fps": 30, "audio": True, "duration": 20,
    })
    monkeypatch.setattr(qa, "measure", lambda path: {
        "lufs": -14, "true_peak_db": -1.5, "black_segments": [], "long_silences_at": [],
    })
    monkeypatch.setattr(qa, "contact_sheet", lambda path, out: str(out))
    return project


@pytest.mark.parametrize("returncode, stderr", [(1, "Decoder failed"), (0, "No summary available")])
def test_measurement_failure_is_not_a_pass(monkeypatch, returncode, stderr):
    monkeypatch.setattr(qa, "run", lambda *args, **kwargs: SimpleNamespace(returncode=returncode, stderr=stderr))
    with pytest.raises(OseError, match="measurement"):
        qa.measure("broken.mp4")


def test_recoverable_decode_errors_are_fatal_to_measurement(monkeypatch):
    def decode(command, **kwargs):
        return SimpleNamespace(returncode=1 if "-xerror" in command else 0,
                               stderr="Error while decoding stream\nSummary:\nI: -14.0 LUFS\nPeak: -1.5 dBFS")
    monkeypatch.setattr(qa, "run", decode)
    with pytest.raises(OseError, match="measurement failed"):
        qa.measure("partly-corrupted.mp4")


def test_failed_measurement_is_recorded_in_report(qa_project, monkeypatch):
    def fail(path):
        raise OseError("measurement failed")
    monkeypatch.setattr(qa, "measure", fail)
    result = qa.run_qa(qa_project)
    assert result["errors"] > 0
    assert any(item["check"] == "measurements" and item["status"] == "error" for item in result["checks"])
    assert not any(item["check"] == "black_frames" and item["status"] == "pass" for item in result["checks"])
    assert (qa_project.out / "qa.json").is_file()


@pytest.mark.parametrize("artifact", ["cut_words", "edl"])
def test_missing_editorial_evidence_is_an_error(qa_project, artifact):
    getattr(qa_project, artifact).unlink()
    result = qa.run_qa(qa_project)
    assert result["errors"] > 0


def test_cc_by_requires_visible_attribution_warning(qa_project, monkeypatch):
    write_json(qa_project.plan, {"music": {"track": "track-id"}})
    monkeypatch.setattr(qa.music_lib, "resolve", lambda track: {"license": "cc-by"})
    result = qa.run_qa(qa_project)
    assert next(item for item in result["checks"] if item["check"] == "music_license")["status"] == "warn"


def test_qa_surfaces_pending_retake_review(qa_project):
    write_json(qa_project.edl, {"segments": [{"in": 0, "out": 20}], "review": [{"reason": "meaning-change"}]})
    result = qa.run_qa(qa_project)
    assert any(item["check"] == "retake_review" and item["status"] == "warn" for item in result["checks"])


@pytest.mark.parametrize("json_output", [True, False])
def test_qa_command_returns_failure_after_printing_report(monkeypatch, capsys, json_output):
    monkeypatch.setattr(qa, "run_qa", lambda *args, **kwargs: {
        "errors": 1, "warnings": 0, "checks": [], "contact_sheet": "sheet.jpg",
    })
    with pytest.raises(SystemExit) as caught:
        cmd_qa(SimpleNamespace(project="unused", file=None, json=json_output))
    assert caught.value.code == 1
    output = capsys.readouterr().out
    assert json.loads(output)["errors"] == 1 if json_output else "1 errors" in output