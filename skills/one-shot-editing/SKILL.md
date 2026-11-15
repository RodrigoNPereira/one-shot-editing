---
name: one-shot-editing
description: >-
  Edit raw talking-head footage into a finished, retention-optimised short vertical video (TikTok, Reels, Shorts)
  in one pass: hook selection, word-level rough cut (fillers, pauses, retakes), 9:16 reframe, 2-3-word animated
  captions, music from a personal tagged library (yt-dlp), B-roll library with auto-labelling and optional app/web
  footage capture, purposeful pacing, call to action, QA and a cover. Bilingual PT-BR / EN.
  Use when the user says "edit this video", "make a TikTok/Reel/Short from this", "cut my talking head", "remove
  the ums/pauses", "add captions and music", "edita esse vídeo", "faz um corte pro TikTok", "tira as pausas",
  "legenda esse vídeo", or drops a raw recording and wants a post-ready short. Also for managing the music/B-roll
  libraries, picking a hook or logging video performance. Also use for footage with animated overlays,
  motion-design reference matching, "video de fundo com animacoes sobrepostas" and sound-design review.
  Coordinates Bang Motion direction, Video Shotcraft recipes and optional Earshot SFX for HyperFrames output.
---

# one-shot-editing

Raw recording in, reviewed vertical short out. This follows a common creator workflow — **hook → rough cut →
captions → music → B-roll → transitions/pacing → CTA** — and adds the steps that workflow leaves implicit: audio
cleanup, reframing, QA, a cover and a performance feedback loop.

The `ose` CLI (Python toolkit + ffmpeg) owns the editorial pipeline and the simple render route.
You (the agent) make the creative decisions. Designed output uses the companion skills below, with one
approved cut and one HyperFrames composition/mix, not multiple competing editing pipelines.

Resolve `OSE` to `bin/ose` beside this loaded skill, including when installed in a plugin cache. Do not assume
`~/.agents/skills` exists. Run `bash "$OSE" doctor` first; use `bash "$OSE"` in place of `$OSE` below if the
package lacks executable permissions or its path contains spaces.

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
| **HyperFrames** | Footage with animated overlays; reference-led motion design, kinetic typography, embedded captions or fullscreen explanations | Cut with `ose`; Bang Motion directs, Video Shotcraft supplies recipes, optional Earshot supplies SFX; approve a pilot, then compose in HyperFrames. See [references/motion-direction.md](references/motion-direction.md) and [references/hyperframes-route.md](references/hyperframes-route.md). |

Mixing is fine: render the short with ffmpeg and build one or two designed inserts (title card, animated stat) in
HyperFrames, then drop the rendered inserts in as B-roll.
For footage-with-overlays briefs, inserts alone are not the requested style: keep the presenter as the base
and choose intentional fullscreen explanations only where needed, with a return to the presenter.
Use [references/footage-overlays.md](references/footage-overlays.md). Do not treat `ose auto` as that route.
Isolated designed inserts also use the companion contract, scoped to the insert rather than the entire film.

## Workflow

Work in a project folder next to the raw video (or wherever the user wants). **Stop for approval at the
checkpoints (◆)** unless the user said "just do it" / "one shot" / "faz tudo" — then run straight through and
show the result plus the QA report.

### 0. Intake
- Find the raw footage (ask only if nothing is obvious). Multiple clips → concatenate first, or edit each separately.
- Learn: topic, target platform (default `tiktok`), target length, tone, what the CTA should drive (follow, comment,
  link in bio, part 2…), and whether there's an app/site/repo to show.
- Inspect the source and listen to speech before deciding how tightly to cut. Preserve the original recording.
- Choose the rendering route now. For reference-led overlays, identify the primary reference, inspect its
  frames and audio, and separate content lessons from visual style. Preserve available reference downloads
  locally; never depend on the ignored repository-root `references/` being installed with this skill.
  If the user's source or previous output is missing, request it; do not substitute a reference creator's footage.
- Detect the current harness and check required skills in its active project/plugin/user scopes.
  Automatically install missing companions into that harness before their first use, following
  [companion setup](references/oss-resources.md#design-companion-setup). Announce the setup; no extra user
  confirmation is needed for this missing-skill bootstrap, subject to host permissions.
  For designed output, ensure `hyperframes`, Bang Motion and Video Shotcraft are available before composition;
  install Earshot when its optional SFX stage is selected. Load and verify each installed skill before use.
  Follow [references/motion-direction.md](references/motion-direction.md) for stage boundaries. Reuse existing
  installations; do not overwrite, auto-update, install into other harnesses or fetch optional analysis models.
- **Preserve source quality.** The default `source` profile keeps supported SDR/CFR native resolution (or
  native-resolution portrait crop), FPS, bit depth, chroma and color tags, with lossless intermediates and final
  video encoding. Do not silently downgrade 4K/60 fps/10-bit footage. Crop/zoom/compositing still change pixels.
  Lossless masters can be large and may not be upload/browser compatible. Use `--quality social` only for an
  explicit 1080x1920/30 fps/8-bit delivery conversion. HDR/Dolby Vision and unsupported source formats stop
  processing rather than losing color/detail silently; use an appropriate color-managed workflow.
- For an existing project, inspect its transcript, EDL and plan before rebuilding anything. Use `render --draft`
  for native previews, or the selected compositor's preview for designed output; existing timed placements
  depend on the approved cut.
```bash
$OSE init proj --video raw.mp4 [--lang pt|en] [--platform tiktok|reels|shorts] [--quality source|social]
```
If the recording needs optional Demucs isolation, run `$OSE isolate-voice proj` **before transcription**.
It changes the project's source. For an existing edit, changing the source requires new transcription and
cut review; do not reuse old timestamps merely because the filenames still exist.
```bash
$OSE transcribe proj                 # word timestamps; fillers are kept on purpose so they can be cut
$OSE text proj                       # readable transcript with timestamps — read it
```
Check names, numbers, negation and important qualifiers against the audio. WhisperX alignment is not always
available for every token; if it cannot align a word, retry with `transcribe --engine faster-whisper` and
inspect the result. Never invent timestamps or silently omit an unaligned word to get a render through.

### 1. Hook ◆
Make the opening clear quickly, without changing what the speaker meant. Read [references/hooks.md](references/hooks.md).
1. `$OSE perf summary` — which hook patterns worked best for this creator (if they log results).
2. `$OSE hooks list --lang <lang> [--pattern …] [--search <topic word>]` — library of proven templates.
3. Decide two things: the **on-screen hook text** (punchy, ≤ 9 words) and the **spoken opening**. If the strongest
   line is buried mid-video, propose a cold open: `--hook-range START-END` moves it to the front.
4. Present 3 options (pattern + text + why), recommend one, then proceed after approval. In one-shot mode,
   choose one and record why without waiting:
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
  Inspect `REVIEW` entries too: similar takes with changed numbers or negation are preserved, not automatically
  treated as duplicates. This safeguard is heuristic, not a semantic guarantee. Keep both when uncertain;
  in one-shot mode, report uncertainty rather than guessing which factual claim is correct.
- Listen across proposed deletions with surrounding context, not just to the kept transcript. Meaningful
  repetition, qualifications, numbers and safety context outrank a shorter runtime. Portuguese `um` is not
  an English filler. Invalid timestamps or cut ranges must be corrected before continuing.
- Lock the approved cut before timing music, B-roll, captions or SFX. If the EDL changes later, recheck every
  timed plan item, then use `plan --accept-timeline`; the toolkit does not automatically rebase placements.
  Watch `review --reel` for deletion context (red border = removed footage), then persist the cut approval:
  `$OSE review proj --approve cut --note "Reviewed deletions and preserved meaning"`.
```bash
$OSE cut proj [--reframe face|center|blur|fill]   # renders lossless work/cut.mkv at source-profile dimensions/FPS
```
- `face` (default) generates smoothed time-varying crop trajectories; `blur` = full frame over a blurred fill.
  `framing.tracking=static` retains the old median-per-segment crop; `framing.center=0.4` sets a manual center.
  Haar detection is a heuristic, not active-speaker tracking: inspect profile views, misses and multiple faces.
- Show the user the cut length and the transcript of the cut (`$OSE text proj --cut`).
- Review every cut with about 0.5 s of context on each side. Record the timestamp and whether the problem
  is pose/framing, a clipped phoneme, ambience or a zoom reset. The cut's short audio fades prevent clicks;
  they do not guarantee continuity. Keep good hard cuts; repair bad ones before decorating them.

### 2a. Designed motion: direction, recipes, sound and pilot ◆
Only for the HyperFrames route: follow [references/motion-direction.md](references/motion-direction.md) and
[references/footage-overlays.md](references/footage-overlays.md).
After the cut is locked, load `bang-motion` for direction and representative styleframes. Plan the visible
action and result for each spoken beat; choose overlay, fullscreen or no graphic and preserve related objects.
Load `video-shotcraft` before storyboard approval for selected recipe cards, exact variants, previews and source.
Search `hyperframes-registry` before implementation; reuse a suitable component or adapt the recipe to GSAP.
Once visual events are timed, choose sound or silence per cue. Load optional `earshot` only for the selected
generation/analysis scope, following [references/earshot-sfx.md](references/earshot-sfx.md).
Approve a 10–15 s pilot before extending to the whole video; in one-shot mode inspect and record the decision
without waiting, but keep unperformed artistic/listening checks pending. A technical pass is not style approval.
Do not render ASS captions first. Use steps 3–7 below for editorial decisions, then follow the HyperFrames
handoff instead of `ose render`/`auto`. External output requires the compositor's own review evidence.

### 3. Captions
The command below is for the FFmpeg route; designed captions use cut words in the compositor.
```bash
$OSE captions proj [--style bold-pop|impact|clean|minimal] [--words 3]
```
2–3 words at a time, active-word highlight, positioned clear of platform UI. Styles: see
[references/caption-styles.md](references/caption-styles.md). For "cinematic"/embedded-behind-subject captions use
the HyperFrames route and its caption/overlay guidance; do not assume a separate caption skill is installed.

### 4. Music
Personal library at `~/.one-shot-editing/library/music` — see [references/music-library.md](references/music-library.md).
```bash
$OSE music add "<url or file>" --tags "lofi,focus" --vibe "calm late-night coding" --license royalty-free
$OSE music suggest "<topic + intended feeling>" [--mood hype] [--energy 0.7]
$OSE plan proj --set music.track=<id> --set music.volume_db=-18
```
The FFmpeg route ducks music under the voice automatically; configure it explicitly in the HyperFrames mix.
Do not let a companion add music or replace the voice outside the approved brief.
**Licensing:** trending/copyrighted songs → render without music
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
Hard cuts by default, with emphasis tied to the spoken point. **Three seconds is a review threshold, not a
universal retention rule**: preserve intentional pauses and avoid effects that compete with comprehension. See
[references/retention-rules.md](references/retention-rules.md).
```bash
$OSE pacing proj                 # report: gaps without a visual change
$OSE pacing proj --apply [--jumpcut] [--max 3]   # auto zooms to fill gaps (+ alternate zoom on jump cuts)
$OSE plan proj --add-zoom '{"start":8.1,"end":9.4,"scale":1.2,"style":"punch"}'
$OSE plan proj --add-text '{"text":"3x faster","start":12,"end":13.5}'      # big on-screen word/number
$OSE plan proj --add-sfx '{"at":4.2,"asset":"whoosh"}'   # built-in: whoosh pop click ding boom riser (or a file)
```
Emphasis zooms belong on punchlines, numbers and key claims. `--apply` is an optional simple-route convenience,
not a requirement to fill every quiet stretch.
`smooth` eases in and out; `punch` intentionally cuts between scales. A passing pacing report only counts
events, not smoothness. For designed output, choreograph motion and sound in the compositor instead of
filling every gap with auto zooms. Use approved recorded assets or optional Earshot candidates for that route;
see [references/earshot-sfx.md](references/earshot-sfx.md). Built-ins remain available for simple edits, not as
a silent replacement for requested sound design. Align each sound's transient to the visual event and adjust
its gain by listening, not by applying one fixed dB value to every asset. Music ducking does not duck the SFX.

### 7. Call to action ◆
See [references/cta.md](references/cta.md). Match the CTA to the goal (follow for part 2, comment keyword, save,
link in bio). Spoken CTA lives in the cut; the on-screen card is set in the plan:
```bash
$OSE plan proj --set cta.text="Follow for part 2"   # shown for the last ~2.8 s (cta.start / cta.duration to override)
```
For the FFmpeg route, preview and render below. Designed output instead follows the HyperFrames handoff:
```bash
$OSE render proj --draft     # fast preview → out/draft.mp4
$OSE qa proj --file proj/out/draft.mp4   # explicitly check the preview, not an older final
$OSE render proj             # source-quality master → out/final.mp4; measured two-pass audio
```

### 8. QA, cover, post copy
The ose commands/reports below apply to native output. For designed output, use the compositor's checks,
snapshots and rendered cover frames; external files do not acquire ose provenance or approval automatically.
```bash
$OSE qa proj                 # loudness, black frames, dead air, hook speed, pacing, caption length/flash, safe zone, licence
$OSE cover proj [--n 6]                        # no --at: extracts candidate frames — view them and pick one
$OSE cover proj --at 3.2 --text "THE TITLE"    # out/cover.jpg (clean frame + big title)
```
**Look at `out/contact_sheet.jpg`** (and a few frames), and listen across edit boundaries before declaring done.
For designed output, also inspect frames around overlay entrances/exits and compare the pilot to the primary
reference, selected styleframes and recipe previews. Record artistic defects with timestamps/frames and
corrections in the project's `REVIEW.md`, separately from technical QA and listening status.
Listen to voice-only, voice+music (when present) and the full mix on headphones and a phone speaker; record
unperformed checks as pending, not approved. See [references/footage-overlays.md](references/footage-overlays.md).
QA errors return exit status 1, including failed measurements or missing required editorial evidence. Fix them
and rerun the affected steps, or report the output as blocked; never call an unverified file post-ready.
The editorial checks require readable `work/cut_words.json` and `work/edl.json` with nonempty words/segments.
QA defaults to `out/final.mp4`; use `--file` for a draft or custom output. Reports are written to `out/qa.json`.
Warnings still need review, especially preserved take alternatives, flashing captions and CC-BY attribution.
Technical QA does not certify preserved meaning, good framing, music rights or viewer retention. Then give the user:
the final file path, length, a post caption (hook restated + 3–5 hashtags, in the video's language), the music
credit if `cc-by`, and a reminder to log results later:
```bash
$OSE perf add --hook-pattern curiosity-gap --hook "..." --topic "..." --views 12000 --retention-3s-pct 62 --completion-pct 31
```
For native output, record final approval only after reviewing this exact output:
`$OSE review proj --approve final --note "Watched output and checked audio/captions/framing"`.
For designed output, bind `REVIEW.md` to the actual output path/hash and compositor evidence instead.
Rendered QA samples actual libass glyph bounds, card/caption collisions and detected-face overlaps; it is not
exhaustive and face-detection misses still need human review. Review source-quality master compatibility before
upload; the social profile is an explicit conversion, not the archival master.

### Fast path
`$OSE auto proj [--draft]` reuses an existing transcript and EDL, then runs cut → pacing → render (including
the plan's caption settings) → QA. Missing transcripts/EDLs are created. Reviewed cuts and captions-off settings
are preserved; generated pacing zooms are refreshed, while manual zooms stay. It is a first look, not automatic
editorial approval. Hook, music, B-roll and CTA still need judgement.
This fast path does not create HyperFrames overlays, a storyboard or a designed-output approval.

Use `auto proj --rebuild-edl` only to deliberately replace the existing cuts, then recheck timed plan items.
EDLs fingerprint source bytes and ordered transcript content. Cut/render records additionally bind quality,
framing, plan, asset and media bytes; stale artifacts are rejected. Legacy projects require retranscription or
explicit `provenance --adopt` after manual source/transcript review, followed by a new cut.
Draft mode uses faster rough-cut encoding; final rendering automatically rebuilds a recorded draft cut at
full quality. Both `auto` and `qa` exit unsuccessfully when QA reports errors.

## Plan file

Cut decisions live in `proj/work/edl.json`; supported native visual/audio treatments live in `proj/work/plan.json`
(`ose plan --set/--add-*` or edit it directly). Schema and
examples: [references/plan-schema.md](references/plan-schema.md). Times in the plan are on the **cut timeline**
(after rough cut), not the raw footage. `ose text proj --cut` shows cut-timeline timestamps.
Designed choreography, recipe provenance and richer sound cues belong in the project's storyboard/composition,
not additional schema keys.

## Rules of thumb
- Aim for an early hook and first word; avoid unnecessary intros, but keep the context needed to understand the claim.
- One idea per short. Cut anything that doesn't pay off the hook.
- Review long static stretches; add a cut, zoom, B-roll or text only when it helps the content.
- Captions: ≤ 3 words, high contrast, inside safe zones, never covering the face or the platform UI.
- Voice is king: music ducked to ~-18 dB under speech, loudness -14 LUFS.
- Ask before using copyrighted music in an exported file; prefer in-app sounds for trends.
- Always look at the output (contact sheet / frames) — never ship blind.
- Use cohort/sample-aware `perf summary`; do not present one successful post as evidence a hook is better.
- Optional `export` creates OTIO source cuts; effects stay metadata. Semantic B-roll retrieval requires explicit
  `broll index-semantic` and `broll search --semantic`, runs locally and downloads model weights only on opt-in.
- For quality experiments and consented real-media benchmarks, read [evaluation.md](references/evaluation.md).

## References
- [hooks.md](references/hooks.md) · [cta.md](references/cta.md) · [retention-rules.md](references/retention-rules.md)
- [caption-styles.md](references/caption-styles.md) · [platforms.md](references/platforms.md)
- [music-library.md](references/music-library.md) · [broll.md](references/broll.md) · [app-footage.md](references/app-footage.md)
- [plan-schema.md](references/plan-schema.md) · [hyperframes-route.md](references/hyperframes-route.md)
- [footage-overlays.md](references/footage-overlays.md) · [motion-direction.md](references/motion-direction.md)
- [earshot-sfx.md](references/earshot-sfx.md)
- [troubleshooting.md](references/troubleshooting.md) · [oss-resources.md](references/oss-resources.md)
