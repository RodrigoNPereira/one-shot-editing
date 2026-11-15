# Open-source building blocks

Used by this skill, plus alternatives worth knowing when extending it.

## Used
| Tool | Role | Licence |
|---|---|---|
| [FFmpeg](https://ffmpeg.org) (+ libass) | Cutting, reframing, overlays, captions, mixing, loudness, QA measurements | LGPL/GPL |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Transcription with word timestamps (CTranslate2) | MIT |
| [WhisperX](https://github.com/m-bain/whisperX) (optional) | Forced alignment for tighter word timing | BSD-2 |
| [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) | Retake and false-start detection | MIT |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Music (and reference video) download | Unlicense |
| [librosa](https://librosa.org) | BPM, energy and brightness for the music library | ISC |
| [PySceneDetect](https://www.scenedetect.com) | Splitting B-roll into shots | BSD-3 |
| [OpenCV](https://opencv.org) | Face tracking for the 9:16 reframe | Apache-2.0 |
| [Demucs](https://github.com/facebookresearch/demucs) (optional) | Voice isolation | MIT |
| [agent-browser](https://github.com/vercel-labs/agent-browser) | Web screenshots and recordings | Apache-2.0 |
| adb / `xcrun simctl` / [idb](https://fbidb.io) | Android and iOS app capture | Apache-2.0 / Apple / MIT |
| Montserrat, Anton | Caption fonts | SIL OFL 1.1 |
| [HyperFrames](https://github.com/heygen-com/hyperframes) (designed route) | Deterministic HTML/GSAP composition and render; installed separately | Check installed distribution and asset terms |
| [Bang Motion](https://github.com/bangtutorial/bang-motion) (designed route) | Visual direction after cut lock; separate companion skill | MIT |
| [Video Shotcraft](https://github.com/Vincentwei1021/video-shotcraft) (designed route) | Selected shot recipes adapted to HyperFrames; separate companion skill | Apache-2.0 |
| [Earshot](https://github.com/Leonxlnx/earshot) (optional) | Local procedural SFX bank/kit and measurements; separate skill and CLI | MIT; inspect per-asset provenance |

## Design companion setup

### Automatic missing-skill bootstrap

When one-shot-editing needs a companion, install it automatically if it is absent from the **current harness**.
This is standing authorization for missing companion skills and local runtime prerequisites needed for the
selected stage, not permission to upgrade existing installations, install into other harnesses, fetch optional
analysis models or upload media. Announce what is missing and continue without a separate setup confirmation;
required host permissions still apply.

1. Identify the active harness from the session and its supported skill discovery mechanism, not merely which
   agent directories happen to exist. Check project, plugin and user scopes; a skill bundled in a plugin counts
   as installed. Reuse a readable, loadable installation and record its actual revision.
2. For missing skills, use the host's supported installer or the targeted skills CLI below. Choose user scope
   for that harness, outside this repository and ose's managed venv. Use the default checkout directory below
   unless the user configured another. If a shared canonical copy already exists, register/reuse it without
   overwriting it. A conflicting name, broken link or modified checkout requires an explicit repair decision,
   not a force install.
3. Install only the skills needed by the selected route/stage: Bang Motion and Shotcraft for designed output;
   Earshot when selected; HyperFrames and its CLI/registry/media skills before their respective operations.
   Do not use `--all`, wildcard skills/agents, or install Earshot's `real-sound` workflow.
4. Verify the installed files and referenced assets, rediscover the skill in the active harness and load it.
   Use supported hot reload if needed. If the harness requires restarting, report that activation is pending;
   do not equate successful file copying with a loaded skill.
5. Install a missing runtime only when its operation is needed (Earshot CLI separately below; HyperFrames via
   its official setup). Check readiness before editing. On network/permission/setup failure, report the failed
   command and blocker; do not silently downgrade the result or repeatedly retry an unchanged failure.

These are inspected upstream revisions for new installations, not a runtime-tested compatibility matrix or
a lock of their transitive dependencies. Existing installations are not automatically moved to these pins:

| Repository | Reviewed revision | Skill entrypoint |
| --- | --- | --- |
| `bangtutorial/bang-motion` | `c1aa65e921c970d858705fcb4a53a8294d1a4131` | `SKILL.md` |
| `Vincentwei1021/video-shotcraft` | `6700db2ba80572ebc777b99d72049679fed9840c` | `SKILL.md` |
| `Leonxlnx/earshot` | `4ac3d2ac2b151e1c23376f9ce7f3047a17050013` | `skills/earshot/SKILL.md` |

Run only the clone command for each missing companion. If a checkout already exists, inspect its revision
and local changes instead of overwriting it or silently pulling:

```bash
COMPANIONS="$HOME/.local/share/one-shot-editing-companions"
mkdir -p "$COMPANIONS"
git clone https://github.com/bangtutorial/bang-motion.git "$COMPANIONS/bang-motion" &&
  git -C "$COMPANIONS/bang-motion" checkout --detach c1aa65e921c970d858705fcb4a53a8294d1a4131
git clone https://github.com/Vincentwei1021/video-shotcraft.git "$COMPANIONS/video-shotcraft" &&
  git -C "$COMPANIONS/video-shotcraft" checkout --detach 6700db2ba80572ebc777b99d72049679fed9840c
# Optional:
git clone https://github.com/Leonxlnx/earshot.git "$COMPANIONS/earshot" &&
  git -C "$COMPANIONS/earshot" checkout --detach 4ac3d2ac2b151e1c23376f9ce7f3047a17050013
```

Verify each new checkout with `git -C <path> rev-parse HEAD` before registration. Use the host's supported skill
installer, or the noninteractive skills CLI from the same shell. Set `HARNESS` to the detected agent's ID
supported by the installed CLI (consult its help/agent list; do not guess). Run only missing entries:

```bash
npx --yes skills add "$COMPANIONS/bang-motion" -g --agent "${HARNESS:?Identify the current harness}" --skill bang-motion --yes
npx --yes skills add "$COMPANIONS/video-shotcraft" -g --agent "${HARNESS:?Identify the current harness}" --skill video-shotcraft --yes
# Only when the Earshot stage is selected:
npx --yes skills add "$COMPANIONS/earshot/skills/earshot" -g --agent "${HARNESS:?Identify the current harness}" --skill earshot --yes
```

Preserve the skill's referenced files, not only `SKILL.md`. After installation,
confirm that Shotcraft's `gallery/api/library.json`, selected `references/shots/` cards and `demos/` are
accessible. If the installer omits these, keep the pinned checkout and record it as the recipe source.
Resolve the loaded skill location from the host, never from the example destination above.
Install HyperFrames using its own setup instructions, and record its actual version alongside companion
revisions. Verify its required CLI/registry/media skills are available before their stages.

For selected Earshot bank/kit operations, check the executable first. If missing, automatically install the
CLI separately (Python >=3.10 and FFmpeg), then verify readiness:

```bash
uv tool install "earshot @ git+https://github.com/Leonxlnx/earshot.git@4ac3d2ac2b151e1c23376f9ce7f3047a17050013"
earshot doctor
earshot sfx list
```

Do not add Earshot to ose's `pyproject.toml` or use ose's venv: setup synchronizes that environment exactly.
The bank is model-free, but package dependencies include Torch/Transformers; announce the dependency download
during bootstrap. No MCP or cloud extras are needed for the initial CLI route. Missing analysis-model caches
do not authorize downloads. Follow [earshot-sfx.md](earshot-sfx.md) for selected-take checks and audio review.
Installing a Python package is not installing an agent skill, and loading a skill is not executing its tools.

Keep source licenses/notices when adapting code; generated assets and references still need their own rights.
Updates are deliberate: record the new revision, recheck recipe/CLI differences and rerun a representative
pilot before adoption. Do not copy the whole upstream pipeline or auto-update at render time.

## Worth knowing / possible upgrades
- [auto-editor](https://github.com/WyattBlue/auto-editor): silence and motion-based cutting (a quick alternative
  rough cut).
- [MediaPipe](https://github.com/google-ai-edge/mediapipe): more robust face/pose tracking for reframing
  (profiles, motion).
- [silero-vad](https://github.com/snakers4/silero-vad): voice activity detection for breath and silence trimming.
- [pyannote.audio](https://github.com/pyannote/pyannote-audio): speaker diarization (podcasts, interviews →
  speaker-aware crops).
- [LAION CLAP](https://github.com/LAION-AI/CLAP) / [Essentia](https://essentia.upf.edu): music tagging by text
  prompt and genre/mood models.
- [open_clip](https://github.com/mlfoundations/open_clip): semantic B-roll search with text→image embeddings.
- [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet): real-time speech enhancement.
- [Remotion](https://www.remotion.dev): implementation source for some Shotcraft demos, not the selected
  renderer or an automatic upgrade. Adapt the motion grammar to HyperFrames under
  [motion-direction.md](motion-direction.md).
- Inspiration: [Hormozi-style captions](https://github.com/topics/auto-subtitles), OpusClip-style repurposing,
  and [clipsai](https://github.com/ClipsAI/clipsai) for long→short clipping.

## Engineering comparison (2026-10-27)

Primary-source documentation informed this local-first improvement pass. These are transferable design ideas,
not benchmarks showing that this toolkit outperforms those projects. No additional runtime dependency or
third-party implementation was imported.

| Project and evidence | Useful principle | Applied here |
|---|---|---|
| [Auto-Editor options](https://auto-editor.com/ref/options) and [timeline format](https://auto-editor.com/docs/v3) | Explicit cut margins, keep overrides and saved timelines make editing inspectable | Validate time ranges, preserve reviewed EDLs on reruns, review deletions in context, fingerprint transcripts |
| [stable-ts regrouping](https://github.com/jianfch/stable-ts#regrouping-words) | Keep word timing separate from punctuation/gap/length-based caption grouping | Preserve existing phrase grouping, fix overlapping chunks, order cold-open captions by output time, clamp final linger |
| [WhisperX limitations](https://github.com/m-bain/whisperX#limitations--) | Numbers, unsupported tokens and overlapping speech can defeat alignment | Fail explicitly on unaligned words; do not silently drop them; expose a faster-whisper retry |
| [ClipsAI clip finder](https://www.clipsai.com/references/clip) | Sentence/topic boundaries matter more than arbitrary runtime | Prefer a coherent complete idea; preserve meaning-changing take alternatives rather than chasing shorter cuts |

### What changed and how it was checked

- Source-to-output timeline: reordered cold-open words now follow output time; rapid captions do not overlap
  and caption linger stops at video end. Regression tests cover all three cases.
- Rough cuts: changed quantities/negation are retained for review, meaningful between-take speech survives,
  distant repetition is not a stutter, and Portuguese `um` is preserved. Timestamp/range errors fail early.
- Reruns: approved EDLs and caption choices survive `auto`; transcript changes are rejected; final encoding
  promotes draft intermediates. Tests exercise orchestration and a synthetic FFmpeg render.
- QA: decoding/measurement failures and missing editorial evidence are errors, not passes. Review candidates
  and CC-BY credit requirements are warnings. CLI errors propagate to automation.
- Asset imports: content-based deduplication and isolated import directories avoid filename collisions.
  B-roll sources remain until each asset is indexed; failed imports retain their source and earlier successes.
  Existing IDs and paths remain usable. Failure-injection tests cover processing and index-write errors.

### Original deferred items (2026-10-27; superseded where noted below)

- [Auto-Editor two-pass normalization](https://auto-editor.com/docs/anorm): evaluate measured two-pass
  normalization of the complete voice/music/SFX mix. Current rendering retains FFmpeg dynamic loudnorm and
  final-output measurement; two-pass audio is not implemented in this pass.
- VAD boundary refinement, alignment provenance/coverage and active-speaker tracking need representative
  recordings, including quiet speech, profile views and multiple speakers. Do not add models solely to claim
  better quality. stable-ts is archived according to its repository; it is a reference, not a new dependency.
- ClipsAI topic selection and diarization are useful for long recordings but expand the current single-speaker
  workflow. Test factual completeness, hardware costs and model-access requirements before adoption.
- A deletion-review reel and a real EN/PT-BR benchmark corpus would improve evaluation. Automated tests cannot
  measure viewer retention or certify preserved meaning, crop quality, transcription accuracy or music rights.
- Source-video fingerprinting and plan-timestamp rebasing are not implemented. Legacy EDLs lack transcript
  fingerprints. Asset indexes still assume one writer; hard termination may leave orphan import directories,
  and content hashing adds disk reads. Installer symlink ownership and mobile scripted-text parsing remain
  audit follow-ups, outside this editing-pipeline pass.

### Licensing

The researched repositories identify Auto-Editor as Unlicense, stable-ts and ClipsAI as MIT, and WhisperX as
BSD-2-Clause. Recheck the exact revision before reusing implementation code. Model weights, dependencies and
distributed binaries can have separate terms; these repository licenses do not grant music or footage rights.

## Implementation follow-through (2026-10-30)

- Locked dependencies and one OpenCV variant; Linux/macOS, Python 3.10/3.12 CI matrix.
- Versioned JSON plan schema plus timing/asset validation; source, cut, plan and render provenance.
- Source-quality default: native-detail SDR/CFR, lossless FFV1 intermediates and QP-0 final H.264. Social delivery
  is explicit. HDR/unsupported sources are blocked, not silently downgraded.
- Revision-bound approvals and deletion-review reels; consent-aware real-media evaluation harness.
- Smoothed Haar-based crop trajectories and manual/static overrides. MediaPipe remains a possible benchmarked
  replacement, not a bundled model or a claimed improvement without evidence.
- Rendered-glyph safe-zone/collision sampling, face-overlap warnings and dated platform assumptions.
- Serialized JSON library transactions, unique atomic writes, and rollback-safe relabeling.
- Measured two-pass final audio; optional OTIO export, local OpenCLIP retrieval and cohort-aware analytics.

Remaining limits: no bundled consented real-person corpus, no empirical retention claims, no automatic
plan-timestamp rebasing, no active-speaker model, and no exhaustive visual correctness certification.
Process interruption can leave orphan import/relabel files. Locks and commit ordering are not a transactional
filesystem or a substitute for backups against power loss, filesystem corruption or hardware failure.
See [evaluation.md](evaluation.md) for experiments and [plan-schema.md](plan-schema.md) for migration/quality.
