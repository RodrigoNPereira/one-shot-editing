#!/usr/bin/env bash
# One-shot-editing environment setup.
#   setup.sh            core deps (transcription, rough cut, music analysis, b-roll, reframe)
#   setup.sh --full     + WhisperX (better word alignment) and Demucs (voice isolation); large torch download
set -euo pipefail

OSE_HOME="${OSE_HOME:-$HOME/.one-shot-editing}"
VENV="${OSE_VENV:-$OSE_HOME/venv}"
FULL=0
[[ "${1:-}" == "--full" ]] && FULL=1

say() { printf '\033[1;36m[ose]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[ose]\033[0m %s\n' "$*" >&2; exit 1; }

command -v ffmpeg >/dev/null || die "ffmpeg not found. Install it (apt install ffmpeg / brew install ffmpeg) and re-run."
command -v ffprobe >/dev/null || die "ffprobe not found (ships with ffmpeg)."
FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
grep -q " ass " <<<"$FILTERS" || die "ffmpeg was built without libass (needed to burn captions)."

mkdir -p "$OSE_HOME"/{library/music,library/broll/_inbox,cache}
[[ -f "$OSE_HOME/performance.csv" ]] || \
  echo "date,platform,url,topic,hook,hook_pattern,language,duration_s,views,avg_view_duration_s,retention_3s_pct,completion_pct,likes,comments,shares,saves,follows" > "$OSE_HOME/performance.csv"

if command -v uv >/dev/null; then
  [[ -x "$VENV/bin/python" ]] || { say "creating venv (python 3.12) at $VENV"; uv venv -q --python 3.12 "$VENV"; }
  PIP=(uv pip install -q --python "$VENV/bin/python")
else
  PY=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || true)
  [[ -n "$PY" ]] || die "Need uv or python 3.10-3.12."
  [[ -x "$VENV/bin/python" ]] || { say "creating venv with $PY"; "$PY" -m venv "$VENV"; }
  PIP=("$VENV/bin/python" -m pip install -q)
fi

say "installing core packages"
"${PIP[@]}" faster-whisper rapidfuzz yt-dlp scenedetect "opencv-python<5" "opencv-python-headless<5" numpy librosa soundfile

if [[ $FULL == 1 ]]; then
  say "installing WhisperX + Demucs (this downloads torch, a few GB)"
  "${PIP[@]}" whisperx demucs
fi

say "done. Run: $(cd "$(dirname "$0")/.." && pwd)/bin/ose doctor"
