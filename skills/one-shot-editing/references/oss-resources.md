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
