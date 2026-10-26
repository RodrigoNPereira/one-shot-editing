# Troubleshooting

| Symptom | Fix |
|---|---|
| `ose doctor` fails, or `venv missing` | `bash scripts/setup.sh` (needs `uv` or Python 3.10–3.12 available; uv downloads 3.12 automatically) |
| `ffmpeg … No such filter: 'ass'` | ffmpeg was built without libass. Install a full build (`apt install ffmpeg`, `brew install ffmpeg`, or the static build from johnvansickle.com) |
| First transcription is very slow | The Whisper model downloads once (~0.5 GB for `small`). Use `--model base` for speed, or `medium`/`large-v3` for accuracy (GPU recommended) |
| Fillers not removed | Whisper sometimes drops "um/éé". Use `--engine whisperx` (setup `--full`), or cut manually with `--cut a-b` after reading `ose text` |
| Wrong words in captions | Edit `word` in `work/transcript.json`, then `ose cut` (rebuilds cut_words) and `ose render` |
| Good line removed as a "retake" | `ose roughcut proj --report`, then `--keep r2` (decision id) |
| Face crop is off | `ose cut proj --reframe center` or `blur`. Face tracking uses OpenCV Haar (frontal faces) |
| Audio/video drift | Should not happen: segments are frame-exact. Report with `work/edl.json` |
| Music too loud | `ose plan proj --set music.volume_db=-22`; ducking is already on (`music.duck`) |
| yt-dlp download fails | `~/.one-shot-editing/venv/bin/python -m pip install -U yt-dlp` (sites change often) |
| `faster-whisper` / PyAV error `metadata_errors` | Already worked around (audio passed as an array). Re-run setup if it persists |
| OpenCV `CascadeClassifier` missing | OpenCV 5 removed it; setup pins `opencv-python<5` |
| agent-browser missing Chrome libs | `agent-browser install --with-deps` |

Environment variables: `OSE_HOME` (libraries, default `~/.one-shot-editing`) and `OSE_VENV` (Python env, default
`$OSE_HOME/venv`).
