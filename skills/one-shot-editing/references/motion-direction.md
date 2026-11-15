# Motion direction and companion skills

Read only for designed overlays, fullscreen explainers or designed inserts. The normal FFmpeg route does not
require these companions. This is an orchestration contract, not a second editor or a new `plan.json` schema.

## Ownership and loading

| Stage | Load / read | Bounded responsibility |
| --- | --- | --- |
| Intake | `hyperframes`; this guide | Verify the compositor contract and companion availability; preserve delivery dimensions, FPS, cut and audio decisions. |
| After the cut is locked | `bang-motion`; its `references/anti-ppt.md`, `references/explainer.md` for explainers, and relevant `references/techniques.md` sections | Direct the visual argument: subject, action, hierarchy, continuity and framing. No rendering or source edits. |
| Before storyboard approval | `video-shotcraft`; its gallery index and selected shot cards/demos | Select and inspect motion recipes, variants, timings and known pitfalls. Do not launch its whole product-promo workflow. |
| Before implementation | `hyperframes-registry` | Find a suitable existing component before hand-building a named effect. |
| After visual events are timed | Optional `earshot`; [earshot-sfx.md](earshot-sfx.md) | Make or compare SFX candidates, not a second soundtrack. |
| Composition and delivery | `hyperframes`, `hyperframes-cli`, `media-use` as needed | Implement, check, preview, mix and render the single approved timeline. |

Use the host's skill loader and advertised skill locations. If the host has no loader, explicitly read the
installed companion's `SKILL.md` and selected references relative to that location. A link or remembered summary
is not a loaded skill. Record the resolved locations and revisions in the project's `STYLE.md`.
Do not assume `~/.agents/skills`, a sibling checkout or the ignored root `references/` exists.

Bang Motion and Video Shotcraft are required for this designed route. If absent from the current harness,
announce and automatically install them using [companion setup](oss-resources.md#design-companion-setup), then
load and verify them before composition. Earshot remains optional, but selecting its stage triggers the same
missing-skill bootstrap; do not drop a requested Earshot cue merely because its skill was initially absent.
Reuse existing installations without overwriting or upgrading them. Install only into the active harness,
not every detected agent. The simple FFmpeg route does not trigger design-companion installation.
If installation fails, host permissions deny it or activation requires a restart, report the exact blocker
and finish independent editorial work if useful. Never silently substitute auto zooms or claim an unloaded
skill was used. Use a supported reload when available; do not bypass host restrictions.

Loading a skill does not require a subagent. Keep the work in one context unless delegation is explicitly needed
and allowed. Do not inherit upstream multi-agent orchestration or repeated approval dialogs.

## Direction brief: action before decoration

Pass Bang Motion the locked cut words, delivery format, actual footage frames, primary reference, permissions,
caption/audio decisions and free space around the subject. Ask for visual direction only:

> Explain each important spoken action with an initial state, a visible change and a result. Preserve the
> presenter's role, exact speech and cut. Choose overlay, fullscreen or no graphic per beat and justify it.
> Keep related objects recognizable between beats. Return style direction and storyboard candidates, not code.

Derive the visual system from the footage, topic and creator, not a starter's palette. Choose a direction in
one-shot mode and record why; otherwise use the existing style checkpoint. Render representative styleframes
before animating: one overlay over actual footage and one fullscreen scene if the brief needs both.
Inspect at phone width. Fix weak hierarchy, miniature diagrams or unreadable labels before writing tweens.
Store the selected style, rejected defaults and frame paths in `STYLE.md`; if HyperFrames requires `SPEC.md`,
derive its implementation constraints from these decisions, not an independent creative brief.

- **Overlay:** one idea fits clearly beside the face/gestures and captions. Placement follows available space,
  not a permanent top-card slot. Use a container only when it helps grouping or contrast.
- **Fullscreen:** a mechanism or detail needs the frame. Recompose for portrait, with a meaningful close-up
  and an explicit return to the presenter; do not enlarge a tiny landscape demo onto an empty canvas.
- **No graphic:** the speaker, evidence already shown or a quiet beat carries the point better.

Plan verbs such as collect, merge, validate and update, not an icon for every noun. Preserve object identity when
it explains causality: source -> record -> normalized row -> result. Keep distinct states visibly distinguishable.
Paths and perspective must agree: a side-view vehicle does not rotate upright on a top-view road; data travelling
along a drawn curve must follow that curve rather than a straight interpolation between endpoints.

## Recipe selection and adaptation

Ask Shotcraft for a small shortlist serving the chosen actions, not a new style or Ink Press template.
Check `gallery/api/library.json` for the card and variant, read the card under `references/shots/`, locate the
exact demo it names, and inspect its preview and implementation. A name alone is not enough to recreate a recipe.
If preview/source is unavailable or disagrees with the card, report the gap and do not claim verified fidelity.

Starting candidates, not mandatory presets:

| Action | Shotcraft card | Adaptation question |
| --- | --- | --- |
| Merge sources | `ui-entrance/bezier-source-converge-merge.md` | Do the same records follow the real paths and visibly arrive? |
| Event becomes a row | `ui-entrance/row-embed.md` | Does the record land in its actual slot without duplicates? |
| Compare states | `data/before-after-slider-scrub.md` | Is the comparison truthful and readable without the transition? |
| Metric changes | `data/chart-live-moves.md` | Are values sourced and axes/scales consistent? |
| Focus a detail | `effects/scanline-annotate-focus.md` | Does the highlight clarify rather than decorate? |

Then search the HyperFrames registry. Use a suitable existing component when it implements the intended action.
Otherwise adapt the recipe into HTML/SVG/GSAP within HyperFrames. Record the source URL/revision, variant, demo,
registry search/choice, adapted properties and retained critical timings in `STORYBOARD.md`.
Preserve motion relationships, not arbitrary 30 fps frame counts: convert to seconds and the delivery frame grid.
Timing must fit the spoken beat and reading hold. Choose a simpler recipe if it cannot fit without rushing speech.
Preserve attribution/license notices for copied or adapted code; media and fonts have separate rights.

## Boundaries: do not import conflicting defaults

- one-shot-editing owns the source, EDL, hook, CTA, language and approval mode. Companions cannot rewrite
  narration, add TTS/music, change aspect ratio/FPS or reopen the approved cut.
- HyperFrames owns the runtime: paused registered timelines, one editable subcomposition per scene, stable
  timed elements, local assets/fonts, no autoplay/player loops, independent clocks or render-time network access.
  Do not import a Bang Motion player or migrate to React/Remotion for a Shotcraft recipe.
- Anti-slide rules judge the visible result, not the number of files/sections. Keep good hard cuts and quiet
  beats; do not require camera drift, breathing, particles, Ken Burns, glow or grain on every shot.
- Use easing by physical/narrative role; constant-speed motion may be linear. No universal spring, forced
  three-property entrance, identical top panels or quota of visual changes.
- Voice timing controls this talking-head edit. Beat-sync is subordinate unless the brief explicitly calls for
  music-led editing. Upstream sound libraries/presets are candidates, not mandatory sources or gains.
- Use [earshot-sfx.md](earshot-sfx.md) for procedural sounds and the existing media route for recordings.
  Do not run Shotcraft's mixer, Earshot's `real-sound` pipeline and HyperFrames mixing on top of each other.

## Pilot acceptance

Follow [footage-overlays.md](footage-overlays.md) for the storyboard and 10-15 s pilot.
Review against the chosen styleframes, actual recipe preview and reference, not a remembered impression.
In `REVIEW.md`, separate technical, artistic and listening status. For every defect give a timestamp/frame,
evidence, intended correction and recheck result. Missing checks stay pending, even in no-stops mode.
Use [evaluation.md](evaluation.md#designed-motion-and-sfx-pilot) for controlled comparisons.
Passing tool checks does not establish premium quality, higher retention or human approval.
