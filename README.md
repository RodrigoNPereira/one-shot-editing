# one-shot-editing

<p align="center">
  <img src="assets/logo.svg" width="386" height="386" alt="One-Shot Editing: a paper target with a play button">
</p>

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
| 3 | **Reframe** | 16:9 → 9:16 with smoothed time-varying face crops, static/manual overrides or blur-fill; frame-exact segments |
| 4 | **Captions** | 2–3 words at a time, active-word highlight, 4 styles, platform safe zones |
| 5 | **Music** | Personal library: paste a link (yt-dlp) or a file, auto BPM/energy/mood, tag by vibe; suggestions by topic; ducked under the voice; licence tracking |
| 6 | **B-roll** | Drop files in an inbox; the agent looks at thumbnails, labels and files them; text search; full-screen or picture-in-picture; web captures (agent-browser) and **optional app footage** (Android emulator / iOS Simulator / your recordings) |
| 7 | **Pacing** | Purposeful changes tied to speech; static stretches are review prompts, not a quota of zooms or effects |
| 8 | **CTA** | Goal-matched call-to-action templates (EN/PT-BR) and an end card |
| + | **Finish** | Optional voice cleanup, measured two-pass loudness, rendered-overlay QA, contact sheet, cover, revision-bound approvals and cohort-aware performance summaries |

Rendering is **ffmpeg** by default (fast, native-looking). For designed output (kinetic type, embedded captions,
motion graphics, footage with animated overlays) the skill hands the cut to
**[HyperFrames](https://github.com/heygen-com/hyperframes)**. **Bang Motion** directs the visual explanation;
**Video Shotcraft** supplies selected motion recipes, adapted to HyperFrames rather than switching renderers.
Optional **Earshot** supplies procedural SFX candidates. Styleframes, a semantic storyboard and a 10–15 s pilot
precede the full composition, with separate technical, artistic and listening review.
See [motion direction](skills/one-shot-editing/references/motion-direction.md) and
[SFX design](skills/one-shot-editing/references/earshot-sfx.md).

Inspired by a creator's "my videos are edited by Claude Code" workflow (hook doc → WhisperX rough cut → 2–3-word
subtitles → yt-dlp music library → auto-sorted B-roll + simulator recordings → pacing review → CTA). This
project turns that workflow into a reusable, open toolkit.

## Install

Requirements: **ffmpeg with libass**, and either [uv](https://docs.astral.sh/uv/) or Python 3.10–3.12.
Node.js 22+ is required for the optional HyperFrames route; Node is also used for web capture.
Designed output additionally requires Bang Motion and Video Shotcraft skills; see companion setup below.
adb and Xcode are optional (app capture).

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

For hosted installation, replace `"$PWD"` with `RodrigoNPereira/one-shot-editing`.
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
checkout, or `npx skills add RodrigoNPereira/one-shot-editing -g`. Select the target agents when prompted.
With skill-only installation, invoke `bin/ose` from the installed skill directory; the Python toolkit
installs itself on first run.

The first transcription downloads a Whisper model (~0.5 GB). Libraries live in `~/.one-shot-editing/`
(`OSE_HOME`).

Dependencies live in the skill's `pyproject.toml` and `uv.lock`, including optional `alignment`, `isolation`,
`interchange` and `semantic` extras. Install extras with `bash skills/one-shot-editing/scripts/setup.sh --extra interchange`
(repeat `--extra` to combine). Setup synchronizes a dedicated environment exactly; specify all wanted extras.
The wrapper refreshes its managed environment when the lock changes, retaining the last selected extras.
An explicit `OSE_VENV` is caller-managed. Only one OpenCV distribution is installed.

### Design companion setup

The marketplace and `install.sh` install **one-shot-editing only**. They do not vendor, download or update
Bang Motion, Video Shotcraft, HyperFrames or Earshot. The native FFmpeg route remains independent of them.
**When the skill runs, the agent automatically installs missing companions into the current harness before
their first use**, using the [bootstrap instructions and pinned sources](skills/one-shot-editing/references/oss-resources.md#design-companion-setup).
It announces setup without asking for separate confirmation, respects host permissions, and reuses existing
installations without overwriting or updating them. Earshot is installed when its optional stage is selected;
its Python CLI is bootstrapped separately when needed, isolated from ose's environment.

At intake, the agent resolves actual installed skill locations and records revisions. After cut approval it
loads Bang Motion; before storyboard approval, Shotcraft; after visual cue timing, Earshot only when needed.
Installation is verified in the active harness; a required restart or failed setup is reported explicitly.
HyperFrames remains the compositor and mixer. No automatic Remotion migration, `real-sound` workflow,
model downloads, audio uploads or upstream full-promo pipelines.

The pinned revisions are research baselines, not end-to-end compatibility certification. This integration
changes instructions and packaging, not the CLI or plan schema. A real-media pilot is still required before
claiming improved animation or sound quality.

## Source-quality contract

**New projects default to `--quality source`.** Supported SDR, constant-frame-rate YUV footage retains its
native frame rate, bit depth, chroma format and color tags. Portrait footage retains its dimensions; landscape
footage uses a native-resolution portrait crop rather than automatically reducing 4K to 1080p. Intermediates
are lossless FFV1/float-PCM (`work/cut.mkv`); final MP4 uses lossless H.264 (QP 0) and ALAC. These files can be
large and are archival/editing masters, not universally compatible upload files.

Cropping, zooming, blur-fill, captions and compositing intentionally change pixels. Lossless encoding prevents
additional codec generation loss; it cannot recover cropped detail or make a zoom sharper than its source.
Unchanged-frame regression checks compare decoded source, intermediate and final pixels, including 10-bit
59.94 fps. This is not a quality guarantee for every creative treatment.

Use `ose init proj --video raw.mp4 --quality social` for an **explicit** 1080×1920/30 fps, 8-bit H.264/AAC
delivery conversion. Existing projects can set `output.profile=social`, then rebuild the cut and review timed
placements. HDR/Dolby Vision are blocked pending a color-managed workflow; source-quality also rejects
unsupported pixel formats, non-square pixels and ambiguous/VFR rates rather than silently downgrading them.

## Use it

Just ask your agent. It follows [`SKILL.md`](skills/one-shot-editing/SKILL.md) and stops for approval at the
hook, after the rough cut, and before the final render. To skip the stops, say "one shot" / "faz tudo".

Or drive the CLI yourself:
```bash
ose init proj --video raw.mp4
ose transcribe proj && ose text proj
ose roughcut proj --report            # then --keep r3 / --cut 12.4-15 / --hook-range 41-45
ose cut proj                          # native-resolution, lossless rough cut
ose review proj --reel                # deleted footage with context; red border marks deletions
ose review proj --approve cut --note "Reviewed deletions and framing"
ose music add "https://…" --tags "lofi,focus" --vibe "calm night coding" --license royalty-free
ose plan proj --set hook.text="Nobody tells you this" --set cta.text="Follow for part 2" --set music.track=<id>
ose broll ingest && ose broll pending # label with: ose broll label <id> --category ui --labels "…"
ose plan proj --add-broll '{"asset":"<id>","start":4.2,"duration":2}'
ose pacing proj --apply
ose render proj && ose qa proj && ose cover proj --at 3 --text "TITLE"
ose review proj --approve final --note "Watched this exact render and checked audio/captions"
ose auto proj                         # reuse transcript/reviewed EDL, then cut, pacing, render and QA
ose auto proj --rebuild-edl            # deliberately replace cuts; recheck timed plan items afterward
```
Full command list: `ose -h` and `ose <command> -h`.

Optional tools:
```bash
ose export proj                      # .otio source cuts/audio; effects are metadata only
ose export proj --format browser     # explicit 8-bit H.264/AAC cut for HyperFrames
ose broll index-semantic             # optional local OpenCLIP model download and thumbnail index
ose broll search "a rainy street" --semantic
ose perf summary --platform shorts --language pt --min-samples 5
ose benchmark corpus.json --out results.json
```
Semantic search does not upload media. Model language coverage varies; evaluate Portuguese separately.
See [evaluation.md](skills/one-shot-editing/references/evaluation.md) for the consented real-media corpus format.
No real-person benchmark footage or empirical retention claims are bundled.

## Editing safeguards

Review the rough-cut report before decorating the timeline. Similar takes with changed numbers or negation
remain for review; the detector does not prove semantic equivalence. Portuguese `um` is not treated as an
English filler. Invalid timestamps/ranges and unaligned WhisperX words stop processing instead of silently
discarding speech. Cold-open captions follow output order, and fast caption chunks do not overlap.

`auto` preserves EDLs and caption choices. Source bytes, transcripts, EDLs, cut files, render assets and plans
are fingerprinted; stale dependencies stop rendering/QA. Final rendering promotes draft-quality cuts.
Changing the cut requires reviewing timed placements and `ose plan proj --accept-timeline`.
`qa` and `auto` return status 1 on technical errors; editorial approval is reported separately.

Version 2 requires rebuilding old `cut.mp4` intermediates. Re-transcribe legacy projects, or explicitly assert
the current source/transcript relationship with `ose provenance proj --adopt` **after reviewing it**.
Adoption does not establish that the speech or old timestamps are correct.

Music/B-roll imports use content deduplication and isolated storage so same-named files do not overwrite
earlier assets. Failed B-roll imports preserve their source and previously indexed successes.
Whole-index transactions use Unix advisory locks; atomic JSON writes have unique temporary files.
Relabeling copies before indexing and removes the old file only after commit. Hard termination can still
leave unindexed duplicate files; it must not invalidate previously indexed media.

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
  references/              editorial guides, motion-direction, earshot-sfx, HyperFrames handoff and evaluation
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
uv sync --project skills/one-shot-editing --locked --extra interchange
OSE_VENV="$PWD/skills/one-shot-editing/.venv" skills/one-shot-editing/.venv/bin/python -m pytest -q tests
```
CI runs the locked environment on Linux/macOS and Python 3.10/3.12. To deliberately update dependencies,
edit the skill's `pyproject.toml` and run `uv lock --project skills/one-shot-editing`; commit both files.

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
Design companions are separate upstream projects: Bang Motion and Earshot (MIT), Video Shotcraft (Apache-2.0).
No upstream code or third-party media is bundled by this integration.
