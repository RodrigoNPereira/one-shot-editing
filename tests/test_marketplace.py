import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CATALOGS = (
    ".claude-plugin/marketplace.json",
    ".github/plugin/marketplace.json",
    ".agents/plugins/marketplace.json",
)


@pytest.mark.parametrize("catalog_path", CATALOGS)
def test_marketplace_resolves_complete_plugin(catalog_path):
    catalog = json.loads((ROOT / catalog_path).read_text())
    assert catalog["name"] == "one-shot-editing-marketplace"
    assert len(catalog["plugins"]) == 1
    entry = catalog["plugins"][0]
    source = entry["source"]
    if isinstance(source, dict):
        assert source["source"] == "local"
        source = source["path"]
        assert entry["policy"]["installation"] == "AVAILABLE"
        assert entry["policy"]["authentication"] in {"ON_INSTALL", "ON_USE"}
    assert source.startswith("./")
    assert ".." not in Path(source).parts
    plugin_root = (ROOT / source).resolve()
    assert plugin_root.is_relative_to(ROOT)
    manifest = json.loads((plugin_root / "plugin.json").read_text())
    assert entry["name"] == manifest["name"] == "one-shot-editing"
    if "version" in entry:
        assert entry["version"] == manifest["version"]
    skill_root = plugin_root / "skills" / entry["name"]
    assert "name: one-shot-editing\n" in (skill_root / "SKILL.md").read_text()
    for asset in (
        "bin/ose",
        "scripts/setup.sh",
        "scripts/ose/__main__.py",
        "references/plan-schema.md",
        "assets/hooks.json",
        "assets/plan.schema.json",
        "pyproject.toml",
        "uv.lock",
    ):
        assert (skill_root / asset).is_file(), asset


def test_client_metadata_stays_in_sync():
    portable = json.loads((ROOT / "plugin.json").read_text())
    claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    assert portable["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    for field in ("name", "version", "description", "author", "license", "keywords"):
        assert portable[field] == claude[field]
    assert json.loads((ROOT / CATALOGS[0]).read_text()) == json.loads((ROOT / CATALOGS[1]).read_text())
    interface = portable["extensions"]["com.openai"]["interface"]
    for field in ("logo", "composerIcon"):
        assert (ROOT / interface[field]).is_file()


@pytest.fixture
def version_repo(tmp_path):
    for relative in ("plugin.json", ".claude-plugin/plugin.json", *CATALOGS, "scripts/plugin_versions.py"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        if target.suffix == ".json":
            document = json.loads(target.read_text())
            if "version" in document:
                document["version"] = "1.0.0"
            if "metadata" in document:
                document["metadata"]["version"] = "1.0.0"
                document["plugins"][0]["version"] = "1.0.0"
            target.write_text(json.dumps(document))
    skill = tmp_path / "skills/one-shot-editing/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("initial skill\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "Before marketplace"],
        cwd=tmp_path, check=True,
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-qm", "Initial package"],
        cwd=tmp_path, check=True,
    )
    return tmp_path


def version_command(root, *args):
    return subprocess.run(
        [sys.executable, str(root / "scripts/plugin_versions.py"), *args],
        cwd=root, text=True, capture_output=True,
    )


def test_version_check_allows_unchanged_package(version_repo):
    (version_repo / "README.md").write_text("Documentation only\n")
    result = version_command(version_repo, "check", "--base-ref", "HEAD")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("path", ["skills/one-shot-editing/SKILL.md", "skills/new.txt", "install.sh"])
def test_version_check_rejects_unversioned_changes(version_repo, path):
    (version_repo / path).write_text("changed content\n")
    result = version_command(version_repo, "check", "--base-ref", "HEAD")
    assert result.returncode == 1
    assert "plugin version must increase" in result.stdout
    assert "marketplace metadata.version must increase" in result.stdout


@pytest.mark.parametrize("level, expected", [("patch", "1.0.1"), ("minor", "1.1.0"), ("major", "2.0.0")])
def test_bump_updates_every_version(version_repo, level, expected):
    result = version_command(version_repo, "bump", "--level", level)
    assert result.returncode == 0, result.stdout + result.stderr
    for path in ("plugin.json", ".claude-plugin/plugin.json"):
        assert json.loads((version_repo / path).read_text())["version"] == expected
    for path in CATALOGS[:2]:
        catalog = json.loads((version_repo / path).read_text())
        assert catalog["plugins"][0]["version"] == expected
        assert catalog["metadata"]["version"] == "1.0.1"
    result = version_command(version_repo, "check", "--base-ref", "HEAD")
    assert result.returncode == 0, result.stdout + result.stderr


def test_version_check_rejects_manifest_drift(version_repo):
    path = version_repo / ".claude-plugin/plugin.json"
    manifest = json.loads(path.read_text())
    manifest["version"] = "2.0.0"
    path.write_text(json.dumps(manifest))
    result = version_command(version_repo, "check", "--base-ref", "HEAD")
    assert result.returncode == 1
    assert "version mismatch" in result.stdout


def test_version_check_rejects_missing_base(version_repo):
    result = version_command(version_repo, "check", "--base-ref", "missing-ref")
    assert result.returncode == 1
    assert "Cannot compare" in result.stdout


def test_version_check_allows_initial_marketplace_publication(version_repo):
    result = version_command(version_repo, "check", "--base-ref", "HEAD~1")
    assert result.returncode == 0, result.stdout + result.stderr