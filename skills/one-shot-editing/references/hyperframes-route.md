# HyperFrames route

Use it when the user wants **designed** output that ffmpeg/ASS can't do well: kinetic typography, captions embedded
behind the subject, branded animated title cards, animated charts or stats, motion-graphic explainers, or
transitions with real motion design. HyperFrames composes HTML/GSAP into video deterministically. Its skills
(`hyperframes`, `hyperframes-core`, `embedded-captions`, `talking-head-recut`, `hyperframes-keyframes`,
`motion-graphics`, `media-use`) may be installed globally; load `hyperframes` first, since it is the entry point.

## Hand-off (one-shot-editing does the editorial work, HyperFrames does the design)
1. Run steps 0–2 here: `init → transcribe → roughcut → cut`, then `ose export proj --format browser`.
   Keep the lossless `work/cut.mkv` master. Handoff: `out/browser-cut.mp4` (explicit 8-bit H.264/AAC conversion)
   and `work/cut_words.json` (word timestamps on the cut timeline).
2. Decide hook, music, B-roll and CTA here as usual (they're editorial decisions), and record them in `plan.json`.
3. In HyperFrames, use `browser-cut.mp4` as the base footage and build from `cut_words.json` plus `plan.json`:
   - Captions: `embedded-captions` (rail or embed styles, behind-the-subject matting) instead of `ose captions`.
   - Punch-ins and reframes: `hyperframes-keyframes`.
   - Re-editing a talking head inside HyperFrames: `talking-head-recut`.
   - Music, SFX and ducking: `hyperframes-audio` / `media-use`, or keep ose's audio by rendering
     a separate `output.profile=social` project and `ose render --no-captions` for a browser-compatible mix.
4. An external HyperFrames render has no ose render-provenance record. `ose qa proj --file <rendered.mp4>`
   can report technical measurements but will flag unverified provenance; do not manufacture a passing
   sidecar. Inspect external captions/framing in HyperFrames and retain its own render evidence.

## Mixed (most common)
Keep the ffmpeg pipeline for the short and build only the **inserts** in HyperFrames, for example an animated
"3 steps" title card, a stat counter, or a stylised app mock. Render them to MP4 (1080×1920 or 1080×1080 for
`pip`), drop them in `~/.one-shot-editing/library/broll/_inbox`, ingest and label them, and place them as B-roll.

## When not to
Plain talking heads, speed and batch work, or no design brief: the ffmpeg route is faster and looks native to the
platforms.
