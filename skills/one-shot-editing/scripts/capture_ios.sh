#!/usr/bin/env bash
# Record app footage from the iOS Simulator (macOS + Xcode only). Taps need idb (https://fbidb.io).
# Output lands in the b-roll inbox so `ose broll ingest` picks it up.
#
#   capture_ios.sh boot   [device name]                 e.g. "iPhone 16 Pro" (default: first available iPhone)
#   capture_ios.sh launch <bundle id>
#   capture_ios.sh shot   [name]
#   capture_ios.sh record [name] [seconds]
#   capture_ios.sh start  [name] / stop
#   capture_ios.sh tap <x> <y> | swipe <x1> <y1> <x2> <y2> | text "<str>"   (idb, points not pixels)
#   capture_ios.sh demo <bundle id> <script.txt>        record while replaying a script of tap/swipe/text/sleep lines
set -euo pipefail

[[ "$(uname)" == Darwin ]] || { echo "iOS capture needs macOS + Xcode. On Linux, ask the user for screen recordings or use capture_web.sh / capture_android.sh." >&2; exit 1; }
command -v xcrun >/dev/null 2>&1 || { echo "xcrun not found: install Xcode" >&2; exit 1; }

OSE_HOME="${OSE_HOME:-$HOME/.one-shot-editing}"
INBOX="$OSE_HOME/library/broll/_inbox"
STATE="$OSE_HOME/cache/ios_recording"
mkdir -p "$INBOX" "$(dirname "$STATE")"
name_for() { local n="${1:-}"; [[ -n "$n" ]] || n="ios-$(date +%Y%m%d-%H%M%S)"; echo "${n// /-}"; }

start_rec() {
  local out="$INBOX/$(name_for "${1:-}").mp4"
  xcrun simctl io booted recordVideo --codec=h264 --force "$out" >/dev/null 2>&1 &
  echo "$! $out" >"$STATE"; sleep 1
}
stop_rec() {
  read -r pid out <"$STATE"; kill -INT "$pid"; wait "$pid" 2>/dev/null || true; rm -f "$STATE"; echo "$out"
}
idb_do() {
  command -v idb >/dev/null 2>&1 || { echo "idb not found: brew install facebook/fb/idb-companion && pip install fb-idb" >&2; exit 1; }
  case "$1" in
    tap) idb ui tap "$2" "$3" ;;
    swipe) idb ui swipe "$2" "$3" "$4" "$5" ;;
    text) idb ui text "$2" ;;
    sleep|wait) sleep "$2" ;;
    *) echo "unknown action: $1" >&2; return 1 ;;
  esac
}

cmd="${1:-}"; shift || true
case "$cmd" in
  boot)
    dev="${1:-$(xcrun simctl list devices available | grep -m1 -o 'iPhone[^(]*' | sed 's/ *$//')}"
    xcrun simctl boot "$dev" 2>/dev/null || true; open -a Simulator; echo "booted: $dev" ;;
  launch) xcrun simctl launch booted "$1" ;;
  shot) out="$INBOX/$(name_for "${1:-}").png"; xcrun simctl io booted screenshot "$out" >/dev/null; echo "$out" ;;
  record) start_rec "${1:-}"; sleep "${2:-10}"; stop_rec ;;
  start) start_rec "${1:-}"; echo "recording… stop with: $0 stop" ;;
  stop) stop_rec ;;
  tap|swipe|text) idb_do "$cmd" "$@" ;;
  demo)
    xcrun simctl launch booted "$1" >/dev/null; sleep 2; start_rec "demo"
    while read -r -a line; do
      [[ ${#line[@]} -eq 0 || "${line[0]}" == \#* ]] && continue
      idb_do "${line[@]}"; sleep 0.6
    done <"$2"
    sleep 1; stop_rec ;;
  *) sed -n '2,11p' "$0"; exit 2 ;;
esac
