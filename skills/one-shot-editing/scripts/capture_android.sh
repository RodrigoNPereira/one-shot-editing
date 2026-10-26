#!/usr/bin/env bash
# Record app footage from an Android emulator/device with adb (Android SDK platform-tools).
# Output lands in the b-roll inbox so `ose broll ingest` picks it up.
#
#   capture_android.sh devices
#   capture_android.sh launch <package>                     start an app (e.g. com.example.app)
#   capture_android.sh shot   [name]                        screenshot
#   capture_android.sh record [name] [seconds]              record (max 180s); drive the app meanwhile
#   capture_android.sh start  [name]                        start background recording
#   capture_android.sh stop                                 stop it and pull the file
#   capture_android.sh tap <x> <y> | swipe <x1> <y1> <x2> <y2> [ms] | text "<str>" | key <KEYCODE> | back | home
#   capture_android.sh demo <package> <script.txt>          record while replaying a script of the commands above
#
# Env: ANDROID_SERIAL (pick device), OSE_HOME
set -euo pipefail

OSE_HOME="${OSE_HOME:-$HOME/.one-shot-editing}"
INBOX="$OSE_HOME/library/broll/_inbox"
STATE="$OSE_HOME/cache/android_recording"
REMOTE=/sdcard/ose_capture.mp4
mkdir -p "$INBOX" "$(dirname "$STATE")"
command -v adb >/dev/null 2>&1 || { echo "adb not found: install Android platform-tools and start an emulator (see references/app-footage.md)" >&2; exit 1; }

name_for() { local n="${1:-}"; [[ -n "$n" ]] || n="android-$(date +%Y%m%d-%H%M%S)"; echo "${n// /-}"; }

start_rec() {
  local out="$INBOX/$(name_for "${1:-}").mp4" limit="${2:-180}"
  adb shell rm -f "$REMOTE" >/dev/null 2>&1 || true
  adb shell screenrecord --bit-rate 12000000 --time-limit "$limit" "$REMOTE" &
  echo "$! $out" >"$STATE"
  sleep 1
}

stop_rec() {
  [[ -f "$STATE" ]] || { echo "no recording in progress" >&2; exit 1; }
  read -r pid out <"$STATE"
  adb shell pkill -INT screenrecord >/dev/null 2>&1 || true
  wait "$pid" 2>/dev/null || true
  sleep 1
  adb pull "$REMOTE" "$out" >/dev/null
  rm -f "$STATE"
  echo "$out"
}

do_action() {
  case "$1" in
    tap) adb shell input tap "$2" "$3" ;;
    swipe) adb shell input swipe "$2" "$3" "$4" "$5" "${6:-300}" ;;
    text) adb shell input text "$(printf '%s' "$2" | sed 's/ /%s/g')" ;;
    key) adb shell input keyevent "$2" ;;
    back) adb shell input keyevent KEYCODE_BACK ;;
    home) adb shell input keyevent KEYCODE_HOME ;;
    sleep|wait) sleep "$2" ;;
    *) echo "unknown action: $1" >&2; return 1 ;;
  esac
}

cmd="${1:-}"; shift || true
case "$cmd" in
  devices) adb devices -l ;;
  launch) adb shell monkey -p "$1" -c android.intent.category.LAUNCHER 1 >/dev/null ;;
  shot) out="$INBOX/$(name_for "${1:-}").png"; adb exec-out screencap -p >"$out"; echo "$out" ;;
  record) start_rec "${1:-}" "${2:-10}"; sleep "${2:-10}"; stop_rec ;;
  start) start_rec "${1:-}" 180; echo "recording… stop with: $0 stop" ;;
  stop) stop_rec ;;
  tap|swipe|text|key|back|home) do_action "$cmd" "$@" ;;
  demo)
    pkg="$1"; script="$2"
    adb shell monkey -p "$pkg" -c android.intent.category.LAUNCHER 1 >/dev/null; sleep 2
    start_rec "${pkg##*.}-demo" 180
    while read -r -a line; do
      [[ ${#line[@]} -eq 0 || "${line[0]}" == \#* ]] && continue
      do_action "${line[@]}"; sleep 0.6
    done <"$script"
    sleep 1; stop_rec ;;
  *) sed -n '2,14p' "$0"; exit 2 ;;
esac
