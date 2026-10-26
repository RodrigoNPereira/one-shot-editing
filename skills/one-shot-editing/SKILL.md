---
name: one-shot-editing
description: >-
  Edit raw talking-head footage into a finished, retention-optimised short vertical video (TikTok, Reels, Shorts)
  in one pass: hook selection, word-level rough cut (fillers, pauses, retakes), 9:16 reframe, 2-3-word animated
  captions, music from a personal tagged library (yt-dlp), B-roll library with auto-labelling and optional app/web
  footage capture, pacing (a visual change every ~3 s, zooms), call to action, QA and a cover. Bilingual PT-BR / EN.
  Use when the user says "edit this video", "make a TikTok/Reel/Short from this", "cut my talking head", "remove
  the ums/pauses", "add captions and music", "edita esse vídeo", "faz um corte pro TikTok", "tira as pausas",
  "legenda esse vídeo", or drops a raw recording and wants a post-ready short. Also for managing the music/B-roll
  libraries, picking a hook or logging video performance.
---

# one-shot-editing

Raw recording in, post-ready vertical short out. This mirrors a proven creator workflow — **hook → rough cut →
captions → music → B-roll → transitions/pacing → CTA** — and adds the steps that workflow leaves implicit: audio
cleanup, reframing, QA, a cover and a performance feedback loop.

Everything is driven by the `ose` CLI (Python toolkit + ffmpeg). You (the agent) make the creative decisions —
hook, which retakes to keep, music, B-roll placement, CTA — and `ose` does the deterministic work.

```bash
OSE=~/.agents/skills/one-shot-editing/bin/ose     # or wherever this skill is installed; `$OSE doctor` checks the setup
```

The first run of any command auto-installs the toolkit into `~/.one-shot-editing/venv` (Python 3.12 via uv). The
first transcription downloads a Whisper model (~0.5 GB for `small`). If `doctor` fails, run
`bash <skill>/scripts/setup.sh` (add `--full` for WhisperX + Demucs).

## Language

Detect the language from the **user's request** and answer in it (PT-BR or EN). The **spoken** language is
detected from the audio by `ose transcribe` and stored in the project; it drives filler removal, hook and CTA
templates. If the request and the audio differ (e.g. a PT-speaking user editing an English video), talk to the user
in their language and write on-screen text (hook, CTA, captions) in the video's language unless told otherwise.

## Rendering route

| Route | When | How |
|---|---|---|
| **ffmpeg (default)** | Normal talking-head shorts; speed matters; batch editing | `ose render` (everything below) |
| **HyperFrames** | The user wants *designed* output: kinetic typography, branded animated cards, captions embedded behind the subject, motion graphics, explainer inserts | Do the cut with `ose` (steps 1–3), then hand `work/cut.mp4` + `work/cut_words.json` to HyperFrames — see [references/hyperframes-route.md](references/hyperframes-route.md) |

Mixing is fine: render the short with ffmpeg and build one or two designed inserts (title card, animated stat) in
HyperFrames, then drop the rendered inserts in as B-roll.

## Workflow

Work in a project folder next to the raw video (or wherever the user wants). **Stop for approval at the three
checkpoints (◆)** unless the user said "just do it" / "one shot" / "faz tudo" — then run straight through and
show the result plus the QA report.

### 0. Intake
- Find the raw footage (ask only if nothing is obvious). Multiple clips → concatenate first, or edit each separately.
- Learn: topic, target platform (default `tiktok`), target length, tone, what the CTA should drive (follow, comment,
  link in bio, part 2…), and whether there's an app/site/repo to show.
```bash
$OSE init proj --video raw.mp4 [--lang pt|en] [--platform tiktok|reels|shorts]
$OSE transcribe proj                 # word timestamps; fillers are kept on purpose so they can be cut
$OSE text proj                       # readable transcript with timestamps — read it
```

### 1. Hook ◆
The first 1–3 seconds decide everything. Read [references/hooks.md](references/hooks.md).
1. `$OSE perf summary` — which hook patterns worked best for this creator (if they log results).
2. `$OSE hooks list --lang <lang> [--pattern …] [--search <topic word>]` — library of proven templates.
3. Decide two things: the **on-screen hook text** (punchy, ≤ 9 words) and the **spoken opening**. If the strongest
   line is buried mid-video, propose a cold open: `--hook-range START-END` moves it to the front.
4. Present 3 options (pattern + text + why), recommend one, then:
```bash
$OSE plan proj --set hook.text="..." --set hook.pattern=curiosity-gap
```

### 2. Rough cut ◆
```bash
$OSE roughcut proj [--pace tight|natural|loose] [--aggressive] [--prefer last|best] [--hook-range 41.2-45.0]
```
- Removes hard fillers (um/uh/éé/hum/tipo-like with `--aggressive`), stutters, false starts, dead air; detects
  retakes (same line said twice → keeps the last/best take). `--report` lists every decision with an id.
- Read the report. Restore anything wrong with `--keep r3,r7`; remove extra ranges with `--cut 12.4-15.0`.
  Decision ids depend on the other flags, so re-run with the same `--pace/--aggressive/--prefer` when using `--keep`.
  Re-running is cheap — iterate on `edl.json` until the story flows. Remove tangents and anything that doesn't
  serve the hook's promise; a 60 s idea is usually a 25–40 s short.
```bash
$OSE cut proj [--reframe face|center|blur|fill]   # renders work/cut.mp4 (1080x1920, frame-exact segments)
```
- `face` (default) tracks the face for 16:9 → 9:16; `blur` = full frame over a blurred fill (screen recordings,
  two people); vertical sources pass through. Optionally `$OSE isolate-voice proj` (Demucs) for noisy rooms.
- Show the user the cut length and the transcript of the cut (`$OSE text proj --cut`).

### 3. Captions
```bash
$OSE captions proj [--style bold-pop|impact|clean|minimal] [--words 3]
```
2–3 words at a time, active-word highlight, positioned clear of platform UI. Styles: see
[references/caption-styles.md](references/caption-styles.md). For "cinematic"/embedded-behind-subject captions use
the HyperFrames route (`embedded-captions` skill).

### 4. Music
Personal library at `~/.one-shot-editing/library/music` — see [references/music-library.md](references/music-library.md).
```bash
$OSE music add "<url or file>" --tags "lofi,focus" --vibe "calm late-night coding" --license royalty-free
$OSE music suggest "<topic + intended feeling>" [--mood hype] [--energy 0.7]
$OSE plan proj --set music.track=<id> --set music.volume_db=-18
```
Music is ducked under the voice automatically. **Licensing:** trending/copyrighted songs → render without music
(or keep it only for preview) and tell the user to add the sound in-app; QA flags `unknown`/`platform-only` tracks.

### 5. B-roll
Library at `~/.one-shot-editing/library/broll` — see [references/broll.md](references/broll.md).
- **Ingest**: user drops files into `_inbox/` (or passes paths) → `$OSE broll ingest [files…]`.
- **Label**: `$OSE broll pending` gives thumbnails — **look at them** (view the images), then
  `$OSE broll label <id> --category <cat> --labels "a,b,c" --desc "…"` (files get sorted into category folders).
- **Find & place**: `$OSE broll search "<words from the transcript>"`; place where the voice references something
  visual, to cover jump cuts, or to break a long static shot:
```bash
$OSE plan proj --add-broll '{"asset":"<id>","start":4.2,"duration":2.0,"mode":"full"}'   # or "pip"
```
- **Web screenshots/recordings**: `scripts/capture_web.sh shot|full|record <url>` (agent-browser).
- **App footage (optional)**: use recordings the user provides, or — if given a repo — run the app and capture it:
  web via `capture_web.sh`, Android emulator via `capture_android.sh`, iOS Simulator (macOS only) via
  `capture_ios.sh`. Details: [references/app-footage.md](references/app-footage.md). Captures land in `_inbox/`.

### 6. Pacing & transitions
Hard cuts by default, a punch-in zoom every so often, and **no static shot longer than ~3 s**. See
[references/retention-rules.md](references/retention-rules.md).
```bash
$OSE pacing proj                 # report: gaps without a visual change
$OSE pacing proj --apply [--jumpcut] [--max 3]   # auto zooms to fill gaps (+ alternate zoom on jump cuts)
$OSE plan proj --add-zoom '{"start":8.1,"end":9.4,"scale":1.2,"style":"punch"}'
$OSE plan proj --add-text '{"text":"3x faster","start":12,"end":13.5}'      # big on-screen word/number
$OSE plan proj --add-sfx '{"at":4.2,"asset":"whoosh"}'   # built-in: whoosh pop click ding boom riser (or a file)
```
Emphasis zooms belong on punchlines, numbers and key claims — choose those yourself; let `--apply` fill the rest.

### 7. Call to action ◆
See [references/cta.md](references/cta.md). Match the CTA to the goal (follow for part 2, comment keyword, save,
link in bio). Spoken CTA lives in the cut; the on-screen card is set in the plan:
```bash
$OSE plan proj --set cta.text="Follow for part 2"   # shown for the last ~2.8 s (cta.start / cta.duration to override)
```
Then preview and render:
```bash
$OSE render proj --draft     # fast preview → out/draft.mp4
$OSE render proj             # final → out/final.mp4 (-14 LUFS, 1080x1920, 30 fps, H.264/AAC)
```

### 8. QA, cover, post copy
```bash
$OSE qa proj                 # loudness, black frames, dead air, hook speed, pacing, caption length/flash, safe zone, licence
$OSE cover proj [--n 6]                        # no --at: extracts candidate frames — view them and pick one
$OSE cover proj --at 3.2 --text "THE TITLE"    # out/cover.jpg (clean frame + big title)
```
**Look at `out/contact_sheet.jpg`** (and a few frames) before declaring done. Fix every QA error. Then give the user:
the final file path, length, a post caption (hook restated + 3–5 hashtags, in the video's language), the music
credit if `cc-by`, and a reminder to log results later:
```bash
$OSE perf add --hook-pattern curiosity-gap --hook "..." --topic "..." --views 12000 --retention-3s-pct 62 --completion-pct 31
```

### Fast path
`$OSE auto proj [--draft]` = transcribe → roughcut → cut → captions → pacing → render → QA with defaults. Good for a
first look; then refine with the steps above (hook, music, B-roll and CTA still need your judgement).

## Plan file

All creative decisions live in `proj/work/plan.json` (`ose plan --set/--add-*` or edit it directly). Schema and
examples: [references/plan-schema.md](references/plan-schema.md). Times in the plan are on the **cut timeline**
(after rough cut), not the raw footage. `ose text proj --cut` shows cut-timeline timestamps.

## Rules of thumb
- Hook in the first second; first word ≤ 0.4 s in. No logo intros, no "hey guys".
- One idea per short. Cut anything that doesn't pay off the hook.
- Something changes on screen every ~3 s (cut, zoom, B-roll, text).
- Captions: ≤ 3 words, high contrast, inside safe zones, never covering the face or the platform UI.
- Voice is king: music ducked to ~-18 dB under speech, loudness -14 LUFS.
- Ask before using copyrighted music in an exported file; prefer in-app sounds for trends.
- Always look at the output (contact sheet / frames) — never ship blind.

## References
- [hooks.md](references/hooks.md) · [cta.md](references/cta.md) · [retention-rules.md](references/retention-rules.md)
- [caption-styles.md](references/caption-styles.md) · [platforms.md](references/platforms.md)
- [music-library.md](references/music-library.md) · [broll.md](references/broll.md) · [app-footage.md](references/app-footage.md)
- [plan-schema.md](references/plan-schema.md) · [hyperframes-route.md](references/hyperframes-route.md)
- [troubleshooting.md](references/troubleshooting.md) · [oss-resources.md](references/oss-resources.md)
