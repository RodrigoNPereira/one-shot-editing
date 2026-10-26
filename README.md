# one-shot-editing

An open-source **agent skill** (Claude Code, GitHub Copilot CLI, Codex, and any agent that reads `SKILL.md`) that
turns raw talking-head footage into a finished, retention-optimised **vertical short** for TikTok, Reels or
Shorts. It works in one pass, and you approve the creative calls.

> "Edit this for TikTok: ~/Videos/raw.mp4" · "Edita esse vídeo pro Reels, tira as pausas e coloca legenda"

## What it does

| # | Step | How |
|---|---|---|
| 1 | **Hook** | Picks from a bilingual library of 90 proven templates (15 patterns), ranked by *your* past performance |
| 2 | **Rough cut** | Word-level timestamps (faster-whisper / WhisperX); cuts fillers (um, éé, hã…), stutters, false starts, dead air; detects **retakes** and keeps the best one; optional cold open |
| 3 | **Reframe** | 16:9 → 9:16 with face tracking (or blur-fill); frame-exact segments, no A/V drift |
| 4 | **Captions** | 2–3 words at a time, active-word highlight, 4 styles, platform safe zones |
| 5 | **Music** | Personal library: paste a link (yt-dlp) or a file, auto BPM/energy/mood, tag by vibe; suggestions by topic; ducked under the voice; licence tracking |
| 6 | **B-roll** | Drop files in an inbox; the agent looks at thumbnails, labels and files them; text search; full-screen or picture-in-picture; web captures (agent-browser) and **optional app footage** (Android emulator / iOS Simulator / your recordings) |
| 7 | **Pacing** | A visual change at least every ~3 s: hard cuts, punch/smooth zooms, on-screen text, SFX |
| 8 | **CTA** | Goal-matched call-to-action templates (EN/PT-BR) and an end card |
| + | **Finish** | Voice cleanup, −14 LUFS loudness, QA report (loudness, black frames, dead air, hook speed, pacing, captions, safe zones, music licence), contact sheet, cover image, performance log that feeds hook selection |

Rendering is **ffmpeg** by default (fast, native-looking). For designed output (kinetic type, embedded captions,
motion graphics) the skill hands the cut to **[HyperFrames](https://github.com/heygen-com/hyperframes)**.

Inspired by a creator's "my videos are edited by Claude Code" workflow (hook doc → WhisperX rough cut → 2–3-word
subtitles → yt-dlp music library → auto-sorted B-roll + simulator recordings → cuts every 3 s → CTA). This
project turns that workflow into a reusable, open toolkit.

## Install

Requirements: **ffmpeg with libass**, and either [uv](https://docs.astral.sh/uv/) or Python 3.10–3.12. Node is
optional (web capture). adb and Xcode are optional (app capture).

```bash
git clone https://github.com/<you>/one-shot-editing && cd one-shot-editing
./install.sh            # links the skill into ~/.agents/skills (+ ~/.claude/.copilot/.codex skill dirs), puts `ose` on PATH
./install.sh --full     # + WhisperX (tighter word timing) and Demucs (voice isolation); large torch download
```
Or with the [skills CLI](https://skills.sh): `npx skills add <you>/one-shot-editing -g`. The Python toolkit then
installs itself on the first `ose` run.

The first transcription downloads a Whisper model (~0.5 GB). Libraries live in `~/.one-shot-editing/`
(`OSE_HOME`).

## Use it

Just ask your agent. It follows [`SKILL.md`](skills/one-shot-editing/SKILL.md) and stops for approval at the
hook, after the rough cut, and before the final render. To skip the stops, say "one shot" / "faz tudo".

Or drive the CLI yourself:
```bash
ose init proj --video raw.mp4
ose transcribe proj && ose text proj
ose roughcut proj --report            # then --keep r3 / --cut 12.4-15 / --hook-range 41-45
ose cut proj                          # 1080x1920 rough cut
ose music add "https://…" --tags "lofi,focus" --vibe "calm night coding" --license royalty-free
ose plan proj --set hook.text="Nobody tells you this" --set cta.text="Follow for part 2" --set music.track=<id>
ose broll ingest && ose broll pending # label with: ose broll label <id> --category ui --labels "…"
ose plan proj --add-broll '{"asset":"<id>","start":4.2,"duration":2}'
ose pacing proj --apply
ose render proj && ose qa proj && ose cover proj --at 3 --text "TITLE"
ose auto proj                         # everything above with defaults
```
Full command list: `ose -h` and `ose <command> -h`.

## Layout
```
skills/one-shot-editing/
  SKILL.md                 orchestrator the agent follows
  bin/ose                  CLI wrapper (own Python 3.12 venv)
  scripts/ose/             toolkit: transcribe, roughcut, cut, captions, music, broll, pacing, render, qa, hooks
  scripts/capture_*.sh     web (agent-browser), Android (adb), iOS Simulator (simctl + idb) capture
  scripts/setup.sh         environment setup
  references/              hooks, CTA, retention rules, caption styles, platforms, music, B-roll, app footage, …
  assets/hooks.json        starter hook library (EN + PT-BR)
  assets/fonts/            Montserrat + Anton (SIL OFL)
tests/                     pytest suite (synthetic media, no model download)
```

## Development
```bash
~/.one-shot-editing/venv/bin/python -m pip install pytest   # or: uv pip install --python ~/.one-shot-editing/venv/bin/python pytest
~/.one-shot-editing/venv/bin/python -m pytest -q tests
```

## Credits and licences
MIT (see [LICENSE](LICENSE)). Built on FFmpeg, faster-whisper, WhisperX, rapidfuzz, yt-dlp, librosa,
PySceneDetect, OpenCV, Demucs and agent-browser. See
[references/oss-resources.md](skills/one-shot-editing/references/oss-resources.md). The fonts are under the SIL
Open Font License. **Music you download is your responsibility**: the skill tracks licences and warns, but
trending songs should be added in-app, not baked in.
