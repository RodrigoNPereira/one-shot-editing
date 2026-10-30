# Troubleshooting

| Symptom | Fix |
|---|---|
| `ose doctor` fails, or `venv missing` | `bash scripts/setup.sh` (needs `uv` or Python 3.10–3.12 available; uv downloads 3.12 automatically) |
| `ffmpeg … No such filter: 'ass'` | ffmpeg was built without libass. Install a full build (`apt install ffmpeg`, `brew install ffmpeg`, or the static build from johnvansickle.com) |
| First transcription is very slow | The Whisper model downloads once (~0.5 GB for `small`). Use `--model base` for speed, or `medium`/`large-v3` for accuracy (GPU recommended) |
| Fillers not removed | Whisper sometimes drops "um/éé". Use `--engine whisperx` (setup `--full`), or cut manually with `--cut a-b` after reading `ose text` |
| Wrong words in captions | Edit `work/transcript.json`, rebuild/review with `ose roughcut`, review timed placements with `ose plan --accept-timeline`, then `ose cut` and `ose render` |
| Good line removed as a "retake" | `ose roughcut proj --report`, then `--keep r2` (decision id) |
| Face crop is off | Set `framing.center` to a manual 0..1 center, or use `--reframe center`/`blur`. Dynamic Haar tracking is not active-speaker detection |
| Audio/video drift | Should not happen: segments are frame-exact. Report with `work/edl.json` |
| Music too loud | `ose plan proj --set music.volume_db=-22`; ducking is already on (`music.duck`) |
| yt-dlp download fails | Deliberately update the locked version with `uv lock --project skills/one-shot-editing --upgrade-package yt-dlp`, then rerun setup and commit the lock update |
| `faster-whisper` / PyAV error `metadata_errors` | Already worked around (audio passed as an array). Re-run setup if it persists |
| OpenCV `CascadeClassifier` missing | OpenCV 5 removed it; setup pins `opencv-python<5` |
| agent-browser missing Chrome libs | `agent-browser install --with-deps` |
| Legacy transcript/EDL has no provenance | Re-transcribe or explicitly `ose provenance proj --adopt` only after confirming the source/transcript relationship; rebuild `ose cut` |
| Timed plan belongs to another EDL | Review every placement against the new cut, then `ose plan proj --accept-timeline` |
| Final is huge or unsupported by a player | Source masters use lossless H.264/ALAC. Explicitly select `output.profile=social` and rebuild, or export a browser cut without replacing the master |
| HDR/VFR/unsupported source rejected | Use a color-managed workflow for HDR. For VFR or source pixel-format conversion, explicitly choose `output.profile=social`; never pretend it preserves every source property |
| Loudness analysis is non-finite | Inspect silent/invalid source audio; explicitly choose `audio.normalization=off` only if silence is intentional |
| Semantic index missing/stale | Install `--extra semantic`, then rebuild `ose broll index-semantic`; models run locally but the first use downloads weights |
| Batching requested without VAD | Batched faster-whisper requires explicit `--vad`; compare quiet speech/fillers with the non-batched baseline |

Environment variables: `OSE_HOME` (libraries, default `~/.one-shot-editing`) and `OSE_VENV` (Python env, default
`$OSE_HOME/venv`).
