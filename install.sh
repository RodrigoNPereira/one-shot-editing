#!/usr/bin/env bash
# Install one-shot-editing globally.
#   ./install.sh              symlink the skill into ~/.agents/skills (+ ~/.claude, ~/.copilot, ~/.codex skill dirs
#                             that exist), put `ose` on PATH (~/.local/bin) and set up the Python toolkit
#   ./install.sh --copy       copy instead of symlink (no live link to this checkout)
#   ./install.sh --full       also install WhisperX + Demucs (large torch download)
#   ./install.sh --no-setup   skip the Python environment (it is created on first `ose` run anyway)
#   ./install.sh --uninstall  remove the links/copies (keeps ~/.one-shot-editing libraries)
set -euo pipefail

NAME=one-shot-editing
SRC="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)/skills/$NAME"
CANON="$HOME/.agents/skills/$NAME"
AGENT_DIRS=("$HOME/.claude/skills" "$HOME/.copilot/skills" "$HOME/.codex/skills")
BIN="$HOME/.local/bin/ose"
COPY=0 SETUP=1 FULL="" UNINSTALL=0
for a in "$@"; do
  case "$a" in
    --copy) COPY=1 ;; --no-setup) SETUP=0 ;; --full) FULL=--full ;; --uninstall) UNINSTALL=1 ;;
    *) sed -n '2,8p' "$0"; exit 2 ;;
  esac
done
say() { printf '\033[1;36m[install]\033[0m %s\n' "$*"; }

remove_entry() {  # only remove what we own: links to our skill, or a copy carrying our SKILL.md name
  local p="$1"
  if [[ -L "$p" ]]; then rm "$p"
  elif [[ -d "$p" ]] && grep -q "^name: $NAME$" "$p/SKILL.md" 2>/dev/null; then rm -rf "$p"
  elif [[ -e "$p" ]]; then echo "refusing to touch $p (not ours)" >&2; return 1
  fi
}

if [[ $UNINSTALL == 1 ]]; then
  for d in "${AGENT_DIRS[@]}"; do remove_entry "$d/$NAME" || true; done
  remove_entry "$CANON" || true
  [[ -L "$BIN" ]] && rm "$BIN"
  say "uninstalled (libraries in ~/.one-shot-editing kept)"; exit 0
fi

[[ -f "$SRC/SKILL.md" ]] || { echo "skill not found at $SRC" >&2; exit 1; }
mkdir -p "$(dirname "$CANON")"
remove_entry "$CANON"
if [[ $COPY == 1 ]]; then cp -R "$SRC" "$CANON"; say "copied skill -> $CANON"
else ln -s "$SRC" "$CANON"; say "linked $CANON -> $SRC"; fi

for d in "${AGENT_DIRS[@]}"; do
  [[ -d "$d" ]] || continue
  remove_entry "$d/$NAME" && ln -s "$CANON" "$d/$NAME" && say "linked $d/$NAME"
done

mkdir -p "$(dirname "$BIN")"
ln -sf "$CANON/bin/ose" "$BIN"
say "ose -> $BIN$([[ ":$PATH:" == *":$HOME/.local/bin:"* ]] || echo '  (add ~/.local/bin to PATH)')"

if [[ $SETUP == 1 ]]; then bash "$CANON/scripts/setup.sh" $FULL; "$BIN" doctor; fi
say "done. Ask your agent: \"edit this video for TikTok: ~/Videos/raw.mp4\""
