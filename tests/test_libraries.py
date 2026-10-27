from pathlib import Path

import pytest

from ose import broll, music


@pytest.fixture(autouse=True)
def isolated_libraries(tmp_path, monkeypatch):
    music_dir = tmp_path / "music"
    broll_dir = tmp_path / "broll"
    monkeypatch.setattr(music, "MUSIC_DIR", music_dir)
    monkeypatch.setattr(music, "INDEX", music_dir / "index.json")
    monkeypatch.setattr(broll, "BROLL_DIR", broll_dir)
    monkeypatch.setattr(broll, "INDEX", broll_dir / "index.json")
    monkeypatch.setattr(broll, "INBOX", broll_dir / "_inbox")
    monkeypatch.setattr(broll, "UNSORTED", broll_dir / "_unsorted")
    monkeypatch.setattr(broll, "THUMBS", broll_dir / ".thumbs")
    monkeypatch.setattr(music, "analyse", lambda path: {
        "duration": 10.0, "bpm": 120, "energy": 0.5, "brightness": 0.5,
        "onset": 0.5, "mood_guess": ["upbeat"],
    })
    monkeypatch.setattr(broll, "probe", lambda path: {
        "duration": 10.0, "width": 1920, "height": 1080, "audio": True,
    })
    monkeypatch.setattr(broll, "detect_scenes", lambda path: [[0, 10]])
    real_make_thumbs = broll.make_thumbs

    def fake_thumbs(item, **kwargs):
        assert Path(item["path"]).is_file()
        directory = kwargs.get("directory", broll.THUMBS)
        thumb = asset(directory / f"{item['id']}_0.jpg", b"thumbnail")
        return [str(thumb)]

    def forbidden(*args, **kwargs):
        raise AssertionError("external media processing is forbidden")

    monkeypatch.setattr(broll, "make_thumbs", fake_thumbs)
    monkeypatch.setattr(broll, "ffmpeg", forbidden)
    monkeypatch.setattr(music, "run", forbidden)
    return real_make_thumbs


def asset(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_music_same_name_preserves_existing_bytes_and_metadata(tmp_path):
    first = asset(tmp_path / "first" / "track.mp3", b"first audio")
    second = asset(tmp_path / "second" / "track.mp3", b"other audio")
    original = music.add(str(first), tags=["favorite"], vibe="quiet", license="owned")
    music.mark_used(original["id"])
    original = music.load_index()[0]

    imported = music.add(str(second), tags=["new"])

    assert Path(original["path"]).read_bytes() == b"first audio"
    assert Path(imported["path"]).read_bytes() == b"other audio"
    assert imported["id"] != original["id"]
    assert music.find(music.load_index(), original["id"]) == original
    assert len(music.load_index()) == 2
    assert music.add(original["path"], tags=["replacement"]) == original
    assert len(music.load_index()) == 2


def test_music_preserves_unindexed_same_named_file(tmp_path):
    stored = asset(music.MUSIC_DIR / "track.mp3", b"unindexed audio")
    source = asset(tmp_path / "incoming" / "track.mp3", b"new audio")

    imported = music.add(str(source))

    assert stored.read_bytes() == b"unindexed audio"
    assert Path(imported["path"]).read_bytes() == b"new audio"


@pytest.mark.parametrize("renamed", [False, True])
def test_music_duplicate_preserves_legacy_record(tmp_path, renamed):
    stored = asset(music.MUSIC_DIR / "track.mp3", b"original audio")
    legacy = {"id": "m1234567", "path": str(stored), "title": "Curated",
              "tags": ["favorite"], "moods": ["calm"], "uses": 9,
              "license": "owned", "vibe": "quiet", "source_url": None}
    music.save_index([legacy])
    source = asset(tmp_path / "incoming" / ("renamed.mp3" if renamed else "track.mp3"),
                   b"original audio")

    assert music.add(str(source), tags=["replacement"], title="New") == legacy
    assert music.load_index() == [legacy]
    assert source.read_bytes() == stored.read_bytes() == b"original audio"
    assert music.resolve(legacy["id"]) == legacy


def test_broll_equal_size_same_name_distinct_content(tmp_path):
    first = asset(tmp_path / "first" / "clip.mp4", b"aaaa")
    second = asset(tmp_path / "second" / "clip.mp4", b"bbbb")

    added = broll.ingest([first, second])

    assert len(added) == 2
    assert added[0]["id"] != added[1]["id"]
    assert [Path(item["path"]).read_bytes() for item in added] == [b"aaaa", b"bbbb"]
    assert broll.load_index() == added
    assert first.exists() and second.exists()


def test_broll_duplicate_in_batch_and_reimport_preserves_record(tmp_path):
    first = asset(tmp_path / "clip.mp4", b"same video")
    renamed = asset(tmp_path / "renamed.mp4", b"same video")
    added = broll.ingest([first, renamed, first])
    assert len(added) == 1
    broll.label(added[0]["id"], category="city", labels=["street"])
    broll.mark_used(added[0]["id"])
    original = broll.load_index()

    assert broll.ingest([renamed]) == []
    assert broll.load_index() == original
    assert Path(original[0]["path"]).read_bytes() == b"same video"


def test_broll_duplicate_preserves_legacy_id_and_path(tmp_path):
    stored = asset(broll.BROLL_DIR / "city" / "b1234567_clip.mp4", b"legacy video")
    legacy = {"id": "b1234567", "path": str(stored), "labels": ["street"], "uses": 8}
    broll.save_index([legacy])
    incoming = asset(tmp_path / "renamed.mp4", b"legacy video")

    assert broll.ingest([incoming]) == []
    assert broll.load_index() == [legacy]
    assert broll.resolve(legacy["id"]) == legacy
    assert stored.read_bytes() == incoming.read_bytes() == b"legacy video"


@pytest.mark.parametrize("failure", ["probe", "make_thumbs", "save_index"])
def test_broll_failure_preserves_source_and_prior_success(monkeypatch, failure):
    first = asset(broll.INBOX / "a.mp4", b"good video")
    failed = asset(broll.INBOX / "b.mp4", b"bad video")
    original_operation = getattr(broll, failure)

    def fail_second(value, **kwargs):
        if failure == "save_index":
            should_fail = len(value) == 2
        else:
            path = value["path"] if failure == "make_thumbs" else value
            should_fail = Path(path).read_bytes() == b"bad video"
        if should_fail:
            if failure == "make_thumbs":
                original_operation(value, **kwargs)
            raise OSError("injected failure")
        return original_operation(value, **kwargs)

    monkeypatch.setattr(broll, failure, fail_second)

    with pytest.raises(OSError, match="injected failure"):
        broll.ingest()

    assert failed.exists(), "failed import must leave its inbox source intact"
    assert failed.read_bytes() == b"bad video"
    committed = broll.load_index()
    assert len(committed) == 1, "earlier successes must already be indexed"
    assert Path(committed[0]["path"]).read_bytes() == b"good video"
    assert Path(committed[0]["thumbs"][0]).read_bytes() == b"thumbnail"
    assert len(list(broll.UNSORTED.iterdir())) == 1
    assert not first.exists()
    monkeypatch.setattr(broll, failure, original_operation)
    assert len(broll.ingest()) == 1
    assert len(broll.load_index()) == 2
    assert not failed.exists()


@pytest.mark.parametrize("suffix", [".mp4", ".jpg"])
def test_broll_thumbnail_storage_does_not_overwrite_existing(
    tmp_path, monkeypatch, isolated_libraries, suffix,
):
    source = asset(tmp_path / f"clip{suffix}", b"media")
    sentinel = asset(broll.THUMBS / f"{broll._id(source)}_0.jpg", b"existing thumbnail")
    monkeypatch.setattr(broll, "make_thumbs", isolated_libraries)

    def fake_ffmpeg(args):
        asset(Path(args[-1]), b"new thumbnail")

    monkeypatch.setattr(broll, "ffmpeg", fake_ffmpeg)
    imported = broll.ingest([source])[0]

    assert sentinel.read_bytes() == b"existing thumbnail"
    assert Path(imported["thumbs"][0]).read_bytes() == b"new thumbnail"
    broll.label(imported["id"], category="city")
    labeled = broll.load_index()[0]
    assert Path(labeled["path"]).read_bytes() == b"media"
    assert Path(labeled["thumbs"][0]).read_bytes() == b"new thumbnail"


def test_broll_inbox_copy_retains_source():
    source = asset(broll.INBOX / "clip.mp4", b"video")
    added = broll.ingest(copy=True)
    assert len(added) == 1
    assert source.read_bytes() == Path(added[0]["path"]).read_bytes() == b"video"


@pytest.mark.parametrize("failure", ["analyse", "save_index"])
def test_music_failure_preserves_source_and_existing_library(tmp_path, monkeypatch, failure):
    stored = asset(music.MUSIC_DIR / "track.mp3", b"original audio")
    legacy = {"id": "m1234567", "path": str(stored), "tags": ["favorite"], "uses": 9}
    music.save_index([legacy])
    source = asset(tmp_path / "incoming" / "track.mp3", b"new audio")

    def fail(*args, **kwargs):
        raise OSError("injected failure")

    monkeypatch.setattr(music, failure, fail)
    with pytest.raises(OSError, match="injected failure"):
        music.add(str(source))

    assert source.read_bytes() == b"new audio"
    assert stored.read_bytes() == b"original audio"
    assert music.load_index() == [legacy]
    assert set(music.MUSIC_DIR.iterdir()) == {stored, music.INDEX}