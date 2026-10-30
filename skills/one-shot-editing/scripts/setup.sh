#!/usr/bin/env bash
# One-shot-editing environment setup.
#   setup.sh            core deps (transcription, rough cut, music analysis, b-roll, reframe)
#   setup.sh --full     + WhisperX (better word alignment) and Demucs (voice isolation); large torch download
set -euo pipefail

OSE_HOME="${OSE_HOME:-$HOME/.one-shot-editing}"
VENV="${OSE_VENV:-$OSE_HOME/venv}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

say() { printf '\033[1;36m[ose]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[ose]\033[0m %s\n' "$*" >&2; exit 1; }
EXTRAS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) EXTRAS+=(--extra alignment --extra isolation); shift ;;
    --extra)
      [[ $# -ge 2 ]] || die "--extra requires alignment, isolation, semantic or interchange"
      case "$2" in alignment|isolation|semantic|interchange) EXTRAS+=(--extra "$2"); shift 2 ;;
        *) die "unknown extra: $2" ;; esac ;;
    *) die "unknown option: $1" ;;
  esac
done

command -v ffmpeg >/dev/null || die "ffmpeg not found. Install it (apt install ffmpeg / brew install ffmpeg) and re-run."
command -v ffprobe >/dev/null || die "ffprobe not found (ships with ffmpeg)."
FILTERS="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
grep -q " ass " <<<"$FILTERS" || die "ffmpeg was built without libass (needed to burn captions)."

mkdir -p "$OSE_HOME"/{library/music,library/broll/_inbox,cache}
[[ -f "$OSE_HOME/performance.csv" ]] || \
  echo "date,platform,url,topic,hook,hook_pattern,language,duration_s,views,avg_view_duration_s,retention_3s_pct,completion_pct,likes,comments,shares,saves,follows" > "$OSE_HOME/performance.csv"

if command -v uv >/dev/null; then
  [[ -x "$VENV/bin/python" ]] || { say "creating venv (python 3.12) at $VENV"; uv venv -q --python 3.12 "$VENV"; }
  UV=(uv)
else
  PY=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || true)
  [[ -n "$PY" ]] || die "Need uv or python 3.10-3.12."
  [[ -x "$VENV/bin/python" ]] || { say "creating venv with $PY"; "$PY" -m venv "$VENV"; }
  [[ -x "$VENV/bin/uv" ]] || "$VENV/bin/python" -m pip install -q "uv==0.12.5"
  UV=("$VENV/bin/uv")
fi

say "syncing locked packages (optional models can require several GB)"
if "${UV[@]}" pip show --python "$VENV/bin/python" opencv-python-headless >/dev/null 2>&1; then
  # Both distributions own cv2; remove both before reinstalling the one locked variant.
  "${UV[@]}" pip uninstall --python "$VENV/bin/python" opencv-python-headless opencv-python
fi
UV_PROJECT_ENVIRONMENT="$VENV" "${UV[@]}" sync --project "$SKILL_DIR" --locked --no-dev "${EXTRAS[@]}"
cksum < "$SKILL_DIR/uv.lock" > "$VENV/.ose-lock"
printf '%s\n' "${EXTRAS[*]}" > "$VENV/.ose-extras"

say "done. Run: $(cd "$(dirname "$0")/.." && pwd)/bin/ose doctor"
