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
- [HyperFrames](https://github.com/heygen-com/hyperframes) and [Remotion](https://www.remotion.dev): designed,
  programmatic video.
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

### Deferred until measured

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
