"""Check release versions or bump the plugin and its marketplace catalogs."""

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json")
CATALOGS = (".claude-plugin/marketplace.json", ".github/plugin/marketplace.json")
CODEX = ".agents/plugins/marketplace.json"
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def parse_version(value):
    if not isinstance(value, str) or not VERSION.fullmatch(value):
        raise ValueError(f"Invalid version: {value!r}; expected major.minor.patch")
    return tuple(map(int, value.split(".")))


def bump(value, level):
    major, minor, patch = parse_version(value)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f"Git command failed: git {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def load_package():
    documents = {
        path: json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (*MANIFESTS, *CATALOGS, CODEX)
    }
    version = documents[MANIFESTS[0]]["version"]
    parse_version(version)
    for path in MANIFESTS:
        if documents[path]["name"] != "one-shot-editing" or documents[path]["version"] != version:
            raise ValueError(f"{path}: plugin name or version mismatch")
    marketplace_version = documents[CATALOGS[0]]["metadata"]["version"]
    parse_version(marketplace_version)
    for path in (*CATALOGS, CODEX):
        catalog = documents[path]
        if catalog["name"] != "one-shot-editing-marketplace":
            raise ValueError(f"{path}: marketplace name mismatch")
        if len(catalog["plugins"]) != 1 or catalog["plugins"][0]["name"] != "one-shot-editing":
            raise ValueError(f"{path}: expected the one-shot-editing plugin")
        if path != CODEX:
            if catalog["plugins"][0]["version"] != version:
                raise ValueError(f"{path}: plugin version mismatch")
            if catalog["metadata"]["version"] != marketplace_version:
                raise ValueError(f"{path}: marketplace version mismatch")
    return documents


def check(base):
    documents = load_package()
    try:
        baseline = git("merge-base", base, "HEAD")
    except ValueError as error:
        raise ValueError(f"Cannot compare with {base}; fetch the base branch first") from error
    changed = set(git("diff", "--name-only", "--no-renames", baseline).splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    release_files = {*MANIFESTS, *CATALOGS, CODEX, "install.sh", "LICENSE"}
    package_changed = any(path in release_files or path.startswith("skills/") for path in changed)
    errors = []
    if package_changed:
        existing = set(git("ls-tree", "-r", "--name-only", baseline).splitlines())
        for path in (*MANIFESTS, *CATALOGS):
            if path not in existing:
                continue
            old = json.loads(git("show", f"{baseline}:{path}"))
            current = documents[path]
            if path in MANIFESTS:
                old_version, current_version = old["version"], current["version"]
                label = "plugin version"
            else:
                old_version, current_version = old["metadata"]["version"], current["metadata"]["version"]
                label = "marketplace metadata.version"
            if parse_version(current_version) <= parse_version(old_version):
                errors.append(f"{path}: {label} must increase")
    if errors:
        print("\n".join(errors))
        return 1
    print("Version checks passed.")
    return 0


def update(level):
    documents = load_package()
    version = bump(documents[MANIFESTS[0]]["version"], level)
    marketplace_version = bump(documents[CATALOGS[0]]["metadata"]["version"], "patch")
    for path in MANIFESTS:
        documents[path]["version"] = version
    for path in CATALOGS:
        documents[path]["plugins"][0]["version"] = version
        documents[path]["metadata"]["version"] = marketplace_version
    for path in (*MANIFESTS, *CATALOGS):
        (ROOT / path).write_text(json.dumps(documents[path], indent=2) + "\n", encoding="utf-8")
    print(f"Plugin: {version}; marketplace: {marketplace_version}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    check_parser = commands.add_parser("check")
    check_parser.add_argument("--base-ref", default="origin/main")
    bump_parser = commands.add_parser("bump")
    bump_parser.add_argument("--level", choices=("patch", "minor", "major"), default="patch")
    args = parser.parse_args()
    try:
        if args.action == "check":
            return check(args.base_ref)
        update(args.level)
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Version check/update failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())