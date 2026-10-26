#!/usr/bin/env bash
# Capture web/app footage for B-roll with agent-browser (https://github.com/vercel-labs/agent-browser).
# Output lands in the b-roll inbox so `ose broll ingest` picks it up.
#
#   capture_web.sh shot   <url> [name]            phone-sized screenshot
#   capture_web.sh full   <url> [name]            full-page screenshot (good for scroll-through b-roll)
#   capture_web.sh record <url> [name] [seconds]  record; drive the page meanwhile with `agent-browser click/fill/scroll`
#   capture_web.sh start  <url> [name]            start recording and return (stop with: capture_web.sh stop)
#   capture_web.sh stop
#
# Env: VIEWPORT="430 932 3" (w h scale; default iPhone-ish), OSE_HOME, AB (agent-browser command override)
set -euo pipefail

OSE_HOME="${OSE_HOME:-$HOME/.one-shot-editing}"
INBOX="$OSE_HOME/library/broll/_inbox"
mkdir -p "$INBOX"
read -r VW VH VS <<<"${VIEWPORT:-430 932 3}"

if [[ -n "${AB:-}" ]]; then read -r -a ab <<<"$AB"
elif command -v agent-browser >/dev/null 2>&1; then ab=(agent-browser)
else ab=(npx -y agent-browser)
fi

need_url() { [[ -n "${1:-}" ]] || { echo "usage: $0 $cmd <url> [name]" >&2; exit 2; }; }
name_for() { local n="${1:-}"; [[ -n "$n" ]] || n="web-$(date +%Y%m%d-%H%M%S)"; echo "${n// /-}"; }

open_page() {
  "${ab[@]}" set viewport "$VW" "$VH" "$VS" >/dev/null 2>&1 || true
  "${ab[@]}" open "$1"
  "${ab[@]}" wait --load networkidle >/dev/null 2>&1 || sleep 2
}

cmd="${1:-}"; shift || true
case "$cmd" in
  shot|full)
    need_url "${1:-}"; out="$INBOX/$(name_for "${2:-}").png"
    open_page "$1"
    if [[ "$cmd" == full ]]; then "${ab[@]}" screenshot --full "$out"; else "${ab[@]}" screenshot "$out"; fi
    echo "$out" ;;
  record)
    need_url "${1:-}"; out="$INBOX/$(name_for "${2:-}").webm"; secs="${3:-8}"
    open_page "$1"
    "${ab[@]}" record start "$out"
    # default choreography: slow scroll so the clip has motion; agents can instead drive the page between start/stop
    for _ in $(seq 1 "$secs"); do "${ab[@]}" scroll down 250 >/dev/null 2>&1 || true; sleep 1; done
    "${ab[@]}" record stop
    echo "$out" ;;
  start)
    need_url "${1:-}"; out="$INBOX/$(name_for "${2:-}").webm"
    open_page "$1"; "${ab[@]}" record start "$out"; echo "$out" ;;
  stop)
    "${ab[@]}" record stop ;;
  *)
    sed -n '2,12p' "$0"; exit 2 ;;
esac
