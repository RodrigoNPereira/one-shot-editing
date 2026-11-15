# HyperFrames route

Use it when the user wants **designed** output that ffmpeg/ASS can't do well: kinetic typography, captions embedded
behind the subject, branded animated title cards, animated charts or stats, motion-graphic explainers, or
transitions with real motion design. Footage with animated overlays belongs here: compose the whole video,
keeping the presenter as the base with purposeful fullscreen explanations and an explicit return. Follow
[footage-overlays.md](footage-overlays.md) for the reference-led style sheet, storyboard and pilot.
HyperFrames composes HTML/GSAP into video deterministically. Load `hyperframes` first and follow
[motion-direction.md](motion-direction.md): Bang Motion directs after cut approval; Video Shotcraft selects
recipes before storyboard approval; the registry supplies reusable components; optional Earshot supplies SFX.
Load `hyperframes-cli` and `media-use` for their scoped operations. These are not competing whole-film pipelines.
If a required companion or HyperFrames is missing, automatically bootstrap it in the current harness under
[companion setup](oss-resources.md#design-companion-setup), then verify availability. Report a blocker only
if setup/activation fails; never deliver basic ASS captions and auto zooms as equivalent motion design.

## Hand-off (one-shot-editing directs the workflow, HyperFrames composes)
1. Run steps 0–2 here: `init → transcribe → roughcut → cut`, then `ose export proj --format browser`.
   Keep the lossless `work/cut.mkv` master. Handoff: `out/browser-cut.mp4` (explicit 8-bit H.264/AAC conversion)
   and `work/cut_words.json` (word timestamps on the cut timeline).
2. Decide hook, music, B-roll and CTA here as usual (they're editorial decisions), and record them in `plan.json`.
    Use Bang Motion to produce style direction and representative styleframes. Use Shotcraft to select
    action-matched recipes, inspect the exact variants/demos and record adaptations in the storyboard.
    Keep motion choreography in the project's storyboard and composition, not in invented plan keys.
    Select sound cues after visual timing; use [earshot-sfx.md](earshot-sfx.md) for procedural candidates.
    Approve the styleframes and a 10–15 s pilot, with separate artistic/audio review, before the whole film.
3. In HyperFrames, use `browser-cut.mp4` as the base footage and build from `cut_words.json` plus `plan.json`:
    - Captions and overlays: use HyperFrames caption/overlay guidance and registry components instead of
       burning ASS first. Add a subject matte only when the layout needs text behind the presenter.
    - Punch-ins and reframes: use a deterministic timeline on an inner media wrapper, with explicit start,
       landing and exit states. Consult the motion guidance before adding easing or blur.
    - Source edits remain in ose's EDL. A concatenated browser-cut cannot recover discarded audio handles;
       J/L cuts need the original source and explicit independent audio timing. Do not silently change the cut.
    - Music, SFX and ducking: follow `media-use` mixing guidance and [earshot-sfx.md](earshot-sfx.md) for
       source selection and measured cue anchors. Generation is external to media-use's SFX retrieval;
       ingest the chosen local WAVs and their provenance. Keep one voice track. Either use the base
       voice once and mix in the compositor, or replace its audio with an explicitly prepared ose mix, never both.
    - Keep the source master intact. Browser export is an explicit 8-bit conversion; choose composition
       resolution/FPS from the approved delivery requirements, not HyperFrames' new-project defaults.
4. An external HyperFrames render has no ose render-provenance record. `ose qa proj --file <rendered.mp4>`
   can report technical measurements but will flag unverified provenance; do not manufacture a passing
   sidecar. Inspect external captions/framing in HyperFrames and retain its own render evidence.

## Mixed (isolated inserts only)
Keep the ffmpeg pipeline for the short and build only the **inserts** in HyperFrames, for example an animated
"3 steps" title card, a stat counter, or a conceptual diagram (real capture for a real app demonstration).
Scope [motion-direction.md](motion-direction.md) to those inserts. Render at the approved placement dimensions
and FPS, not automatic 1080p/30 defaults; ingest, label and place them as B-roll.
The native B-roll renderer uses the insert's video only. Export silent inserts and place any chosen SFX
separately through `plan.sfx`, converting insert-local cue times to the final cut timeline.
This is not the preferred route for a continuous footage-with-overlays brief.

## When not to
Plain talking heads, speed and batch work, or no design brief: the ffmpeg route is faster and looks native to the
platforms.
