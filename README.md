<img src="assets/logo.svg" width="96" height="96" alt="One-Shot Editing: a paper target with a play button">

# one-shot-editing

An open-source **plugin marketplace** for Claude Code, GitHub Copilot, and Codex, shipping the
**one-shot-editing** skill. It also works with any agent that reads `SKILL.md`. The skill
turns raw talking-head footage into a finished, retention-optimised **vertical short** for TikTok, Reels or
Shorts. It works in one pass, and you approve the creative calls.

> "Edit this for TikTok: ~/Videos/raw.mp4" · "Edita esse vídeo pro Reels, tira as pausas e coloca legenda"

## What it does

| # | Step | How |
|---|---|---|
| 1 | **Hook** | Picks from a bilingual library of 90 proven templates (15 patterns), ranked by *your* past performance |
| 2 | **Rough cut** | Word-level timestamps (faster-whisper / WhisperX); cuts fillers (um, éé, hã…), stutters, false starts, dead air; detects **retakes** and keeps the best one; optional cold open |
| 3 | **Reframe** | 16:9 → 9:16 with face tracking (or blur-fill); frame-exact segments, no A/V drift |
| 4 | **Captions** | 2–3 words at a time, active-word highlight, 4 styles, platform safe zones |
| 5 | **Music** | Personal library: paste a link (yt-dlp) or a file, auto BPM/energy/mood, tag by vibe; suggestions by topic; ducked under the voice; licence tracking |
| 6 | **B-roll** | Drop files in an inbox; the agent looks at thumbnails, labels and files them; text search; full-screen or picture-in-picture; web captures (agent-browser) and **optional app footage** (Android emulator / iOS Simulator / your recordings) |
| 7 | **Pacing** | A visual change at least every ~3 s: hard cuts, punch/smooth zooms, on-screen text, SFX |
| 8 | **CTA** | Goal-matched call-to-action templates (EN/PT-BR) and an end card |
| + | **Finish** | Voice cleanup, −14 LUFS loudness, QA report (loudness, black frames, dead air, hook speed, pacing, captions, safe zones, music licence), contact sheet, cover image, performance log that feeds hook selection |

Rendering is **ffmpeg** by default (fast, native-looking). For designed output (kinetic type, embedded captions,
motion graphics) the skill hands the cut to **[HyperFrames](https://github.com/heygen-com/hyperframes)**.

Inspired by a creator's "my videos are edited by Claude Code" workflow (hook doc → WhisperX rough cut → 2–3-word
subtitles → yt-dlp music library → auto-sorted B-roll + simulator recordings → cuts every 3 s → CTA). This
project turns that workflow into a reusable, open toolkit.

## Install

Requirements: **ffmpeg with libass**, and either [uv](https://docs.astral.sh/uv/) or Python 3.10–3.12. Node is
optional (web capture). adb and Xcode are optional (app capture).

The toolkit uses Bash and Unix tools: use Linux, macOS, or WSL on Windows. Installing the plugin does not
install system dependencies or add `ose` to your shell's `PATH`.

### Marketplace installation

Run these commands from this checkout. Choose one client:

**Claude Code**
```bash
claude plugin marketplace add "$PWD"
claude plugin install one-shot-editing@one-shot-editing-marketplace
```

**GitHub Copilot CLI**
```bash
copilot plugin marketplace add "$PWD"
copilot plugin install one-shot-editing@one-shot-editing-marketplace
```

**Codex CLI**
```bash
codex plugin marketplace add "$PWD"
codex plugin add one-shot-editing@one-shot-editing-marketplace
```
On clients without `codex plugin add`, install from the plugin browser after registering the marketplace.

**VS Code Copilot**: open the Extensions view, search `@agentPlugins`, and use **Manage Plugin
Marketplaces** to add this repository's Git URL once published. You can also add its `OWNER/REPO` to
the `chat.plugins.marketplaces` setting. This requires a VS Code version with Agent Plugins support.

After publishing to GitHub, replace `"$PWD"` in the marketplace-add commands with the actual `OWNER/REPO`.
There is no configured remote in this checkout, so no hosted repository address is assumed here.
Restart your agent session after installation. Ask it to use `one-shot-editing`; in Claude Code, the
explicit command is `/one-shot-editing:one-shot-editing`.

The plugin bundles the CLI at `skills/one-shot-editing/bin/ose` relative to its installed root. Agents
should resolve that path from the loaded skill location, not assume a global skills directory. The first
CLI run sets up the Python toolkit. To expose `ose` in your terminal too, use the standalone installer below.
Choose either plugin installation or standalone skill installation for an agent to avoid duplicate skills.

### Standalone skill installation

From this checkout:
```bash
./install.sh            # links the skill into ~/.agents/skills (+ ~/.claude/.copilot/.codex skill dirs), puts `ose` on PATH
./install.sh --full     # + WhisperX (tighter word timing) and Demucs (voice isolation); large torch download
```
For other compatible agents, use the [skills CLI](https://skills.sh): `npx skills add . -g` from this
checkout, or `npx skills add OWNER/REPO -g` after publishing. Select the target agents when prompted.
With skill-only installation, invoke `bin/ose` from the installed skill directory; the Python toolkit
installs itself on first run.

The first transcription downloads a Whisper model (~0.5 GB). Libraries live in `~/.one-shot-editing/`
(`OSE_HOME`).

## Use it

Just ask your agent. It follows [`SKILL.md`](skills/one-shot-editing/SKILL.md) and stops for approval at the
hook, after the rough cut, and before the final render. To skip the stops, say "one shot" / "faz tudo".

Or drive the CLI yourself:
```bash
ose init proj --video raw.mp4
ose transcribe proj && ose text proj
ose roughcut proj --report            # then --keep r3 / --cut 12.4-15 / --hook-range 41-45
ose cut proj                          # 1080x1920 rough cut
ose music add "https://…" --tags "lofi,focus" --vibe "calm night coding" --license royalty-free
ose plan proj --set hook.text="Nobody tells you this" --set cta.text="Follow for part 2" --set music.track=<id>
ose broll ingest && ose broll pending # label with: ose broll label <id> --category ui --labels "…"
ose plan proj --add-broll '{"asset":"<id>","start":4.2,"duration":2}'
ose pacing proj --apply
ose render proj && ose qa proj && ose cover proj --at 3 --text "TITLE"
ose auto proj                         # reuse transcript/reviewed EDL, then cut, pacing, render and QA
ose auto proj --rebuild-edl            # deliberately replace cuts; recheck timed plan items afterward
```
Full command list: `ose -h` and `ose <command> -h`.

## Editing safeguards

Review the rough-cut report before decorating the timeline. Similar takes with changed numbers or negation
remain for review; the detector does not prove semantic equivalence. Portuguese `um` is not treated as an
English filler. Invalid timestamps/ranges and unaligned WhisperX words stop processing instead of silently
discarding speech. Cold-open captions follow output order, and fast caption chunks do not overlap.

`auto` preserves existing EDLs and caption choices. New EDLs fingerprint their transcript, and final renders
promote draft-quality cuts automatically. Changing the source recording still requires retranscription;
changing the cut requires rechecking timed placements. `qa` and `auto` return status 1 on QA errors.

Music/B-roll imports use content deduplication and isolated storage so same-named files do not overwrite
earlier assets. Failed B-roll imports preserve their source and previously indexed successes.

See the [engineering comparison and remaining limits](skills/one-shot-editing/references/oss-resources.md)
for the Auto-Editor, stable-ts, WhisperX and ClipsAI ideas used in this pass. The pipeline has regression and
synthetic-media tests, not evidence that it has the best retention or editing quality across all projects.

## Layout
```
plugin.json                portable Agent Plugins manifest (Codex and compatible hosts)
.claude-plugin/            Claude plugin manifest and marketplace catalog
.github/plugin/            Copilot marketplace catalog
.agents/plugins/           Codex marketplace catalog
skills/one-shot-editing/
  SKILL.md                 orchestrator the agent follows
  bin/ose                  CLI wrapper (own Python 3.12 venv)
  scripts/ose/             toolkit: transcribe, roughcut, cut, captions, music, broll, pacing, render, qa, hooks
  scripts/capture_*.sh     web (agent-browser), Android (adb), iOS Simulator (simctl + idb) capture
  scripts/setup.sh         environment setup
  references/              hooks, CTA, retention rules, caption styles, platforms, music, B-roll, app footage, …
  assets/hooks.json        starter hook library (EN + PT-BR)
  assets/fonts/            Montserrat + Anton (SIL OFL)
tests/                     pytest suite (synthetic media, no model download)
```

All three catalogs publish `one-shot-editing` from the repository root, sharing one skill and toolkit.
The version helper keeps both manifests and the Claude/Copilot catalog entries in sync when releasing.

## Development
Lint all Python code with the same pinned Ruff version used in CI:
```bash
uvx --from ruff==0.14.2 ruff check .
uvx --from ruff==0.14.2 ruff check . --fix   # apply safe automatic fixes
```
Rules and Python compatibility are configured in [ruff.toml](ruff.toml). Ruff runs as an independent
CI job on pushes and pull requests. Formatting is not enforced.

```bash
~/.one-shot-editing/venv/bin/python -m pip install pytest   # or: uv pip install --python ~/.one-shot-editing/venv/bin/python pytest
~/.one-shot-editing/venv/bin/python -m pytest -q tests
```

Packaging-only checks (no model downloads or media processing):
```bash
python3 -m pytest -q tests/test_marketplace.py
claude plugin validate .   # optional native validation when Claude Code is installed
```

### Versioning

Pull requests targeting `main` run **PR Validation / Plugin versions**, following the marketplace's
explicit version-bump workflow. Changes to the skill, installer, license, manifests, or catalogs require
an increased plugin version and increased Claude/Copilot marketplace metadata versions. Documentation
outside the skill, tests, and CI-only changes do not require a bump. Initial marketplace publication is
allowed when the base commit has no manifests yet.

Before submitting a release change:
```bash
python3 scripts/plugin_versions.py bump --level patch
git fetch origin main
python3 scripts/plugin_versions.py check --base-ref origin/main
```

Use `patch` for compatible fixes, `minor` for added functionality, and `major` for breaking changes.
The helper increments both marketplace metadata versions by one patch and updates both plugin manifests
and catalog plugin versions together. Codex's catalog has no version field; it uses the portable manifest.
Checks include committed, staged, unstaged, and untracked release files relative to the merge base.

Commit the version changes with the implementation. CI validates only: it does not push commits, tag
releases, or approve PRs. A repository administrator must make **Plugin versions** a required status
check in the `main` branch rules to enforce it before merging.

## Credits and licences
MIT (see [LICENSE](LICENSE)). Built on FFmpeg, faster-whisper, WhisperX, rapidfuzz, yt-dlp, librosa,
PySceneDetect, OpenCV, Demucs and agent-browser. See
[references/oss-resources.md](skills/one-shot-editing/references/oss-resources.md). The fonts are under the SIL
Open Font License. **Music you download is your responsibility**: the skill tracks licences and warns, but
trending songs should be added in-app, not baked in.
