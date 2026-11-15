# Footage with animated overlays

Use for reference-led shorts where the presenter stays as the visual base and motion graphics illustrate
the speech. This is a designed HyperFrames route, not an auto-zoom preset. Preserve good hard cuts;
smoothness means motivated continuity, not dissolving between every pair of faces.
Use [motion-direction.md](motion-direction.md) to load Bang Motion for direction and Shotcraft for recipes.
Fullscreen explanation is allowed when the mechanism needs space; plan why and when the presenter returns.

## Reference intake and style sheet

Choose one primary reference; use the others for specific lessons rather than averaging their styles.
Inspect the opening, each visual beat and the ending. Sample fast movements more densely; static contact
sheets alone cannot establish timing, easing or sound quality. Listen to the references and the source.
Separate observed behavior, transcript claims, measured values and guesses about the author's tools.
Keep references for local analysis; do not reuse their footage, music or graphics in delivery without rights.

Save the following in the project's `STYLE.md` before composition:

- Primary reference and relevant timestamps; what to borrow and what not to copy.
- Native source dimensions/FPS/color and the explicitly approved delivery conversion.
- Base framing, free space around face/gestures, platform safe zones and overlay hierarchy.
- Local licensed fonts: a strong sans for information, optional italic serif for selective contrast.
- Colors chosen for the actual footage, legible at phone size; one accent with a semantic purpose.
- Movement roles and durations, reading holds, allowed cut treatments and sound roles.

Starting values to adapt to the selected direction, not a fixed reference-derived template:

| Element | Starting treatment |
| --- | --- |
| Base footage | Full-frame presenter; retain recognizable face, gestures and intentional breathing room. |
| Explanatory overlay | One dominant idea at a time; real capture for product demonstrations, labeled illustration for diagrams. |
| Type | Information hierarchy above decorative effects; selective emphasis, not an animated title on every word. |
| Entrance | 0.25-0.45 s, ease-out to a stable landing, e.g. `power4.out`; no perpetual drift after arrival. |
| Exit | 0.15-0.25 s, accelerating departure, e.g. `power3.in`; no accidental scale snap. |
| Hold | Long enough to read at phone size; start around 0.5 s + 0.3 s per word and adjust to the spoken beat. |
| Camera move | Ease both ways; do not reuse the text entrance curve for every motion. |
| Blur | Only on fast movers, through the supported compositor mechanism; inspect the fastest frames. |
| Caption | Usually 1-3 words, selective highlight, clear of face and platform controls. |
| Quiet beat | Remove explanatory overlays when the presenter delivers the conclusion. No decorative pulses or sound spam. |

Before animation, inspect representative styleframes over the real footage and at phone size. Reject tiny
labels, repeated top-panel layouts and ineffective hierarchy before polishing their entrance effects.
Record the selected direction and companion revisions in `STYLE.md`.

## Storyboard on the locked cut

Save `STORYBOARD.md` in the project. Replace placeholders with actual words and times from `cut_words.json`;
never invent timestamps from an unaligned transcript. The table is a human planning artifact, not new
`plan.json` fields: the plan schema rejects unknown keys.

Each beat records the following (use a table or a short block per beat):

| Field | Required decision |
| --- | --- |
| Cut time / phrase | Exact words and time from cut words; stable beat ID. |
| Purpose / action | What the viewer learns; initial state -> visible action -> result, not just a noun/icon. |
| Continuity | Which object persists, transforms or hands off to the next beat. |
| Composition / assets | Overlay, fullscreen or no graphic, with reason; source/license or labeled conceptual illustration. |
| Recipe / component | Shotcraft card, variant, exact demo and revision; registry choice; necessary GSAP adaptations. |
| Timing / cut | Entrance, action, landing, stable reading hold, exit; camera framing and seam treatment. |
| Sound | Cue ID, purpose or none, selected take, visual event, measured anchor, offset, gain and review status. |

Make a 10-15 s pilot containing at least two existing cuts, emphasis and a demonstration where the material
allows it. Include an overlay/fullscreen handoff when the brief uses both. Compare the same excerpt with and
without treatment and against the chosen styleframes/recipe previews. Get style approval before scaling up;
in no-stops mode inspect it and record the decision. If the source is missing, stop the media work and
request it; a reference Reel is not substitute footage for the user's project.

## Cut continuity

Inspect about 0.5 s before and after every seam, with picture and sound. Log timestamp, defect and treatment:
pose/framing jump, clipped phoneme, changing ambience, zoom reset or overlay entrance/exit.

1. Fix cut points first, preserving meaning, phonemes, useful breaths and gestures. Revalidate timed items
   and accept the new timeline explicitly if the EDL changes.
2. Keep clean hard cuts. Cover a distracting jump with a relevant capture/overlay or intentional reframing,
   not an unrelated effect applied to all cuts. Do not dissolve the presenter into a double face.
3. Give motion an explicit initial state, landing, hold and exit. Preview each boundary before and after
   it; text should stop moving once it lands.
4. Short fades on the existing cut audio are click prevention, not overlap. If ambience needs a crossfade
   or J/L cut, use valid handles from the original source and independent audio timing. Do not recover
   discarded speech from the concatenated cut or move visible lip-sync to hide an edit.

## Sound cues, assets and mix

Use a small coherent sound kit: approved recorded assets or optional Earshot bank/kit candidates for stylized
movement and contacts. Follow [earshot-sfx.md](earshot-sfx.md) after visual events are timed.
Existing ose SFX accept file paths; built-in synthesis is for the simple route, not a premium sound kit.
Inspect candidate assets before using them; record source, license and any required attribution.
Do not install a tool merely because a reference names it, or download assets without checking rights.

- Assign a sound only to a meaningful visible action. Quiet beats and most caption changes need no effect.
- Align the audible transient, not the file's first sample, to the impact/reveal. Start with one-frame
  accuracy for impact cues; a whoosh/riser can lead in if its payoff lands on the event.
- Derive placement from `visual hit - transient offset`; trim unwanted lead-in or choose another asset
  if placement would go negative. Handle fades, tails and volume automation in the compositor or a
  prepared local copy, without extending or shifting the approved picture timeline silently.
- Audition gain per asset. A fixed -8 or -10 dB gain does not define perceived level. Music sidechain in
  ose does not duck effects; reduce or automate an effect that masks important speech.
- Keep the voice once, in either the base footage or a replacement mix. Never sum both copies.
- Start with the toolkit's -14 LUFS integrated / <= -1.5 dBTP target for the final mix. Measure it again
  after composition; do not copy a reference's clipped peak or confuse loudness with sound quality.
- Compare voice-only, voice+music (when present) and full mix on headphones and a phone speaker at low and normal
  volume. Missing listening checks must remain pending, even if technical QA passes.

## Composition and acceptance

Follow [hyperframes-route.md](hyperframes-route.md). Use the locked browser handoff and cut words,
preserving the source master. Load `hyperframes` first; search `hyperframes-registry` for suitable
components before implementing named effects; use `media-use` for assets/mixing and `hyperframes-cli`
for checks, snapshots, preview and rendering. No dependency on ignored local reference files in delivery.

Keep assets/fonts local and timelines deterministic. Do not burn ose captions beneath compositor captions.
Check composition duration and media offsets against the cut; choose resolution/FPS explicitly.

Before calling the pilot approved:

- Run HyperFrames check and fix errors; inspect scene midpoints, motion peaks and boundaries, not just a cover.
- Compare to the primary reference: presenter visible, purposeful scale/hierarchy, readable stable holds,
  clean entrances/exits, real demonstration assets and intentional quiet beats.
- During fullscreen beats, require justified framing and an intentional return instead of presenter visibility.
- Check perspective, real motion paths, object continuity and phrase-to-action timing. A diagram must explain
  a mechanism, not merely reveal labels; inspect peaks and seams densely and play the pilot at normal speed.
- Verify cut continuity and the applicable audio mixes above. Record remaining manual checks honestly.
- Measure rendered duration, dimensions, FPS, loudness and true peak. Preserve the compositor's review
  evidence; external renders do not gain ose provenance by writing a fabricated passing sidecar.

Write `REVIEW.md` with separate technical, artistic and listening status. Every failed criterion needs a
timestamp/frame, evidence, correction and recheck result; missing evidence means pending, not pass.
If artistic review fails, revise the direction/recipe and pilot instead of adding more effects.

After approval, extend the same visual grammar to the whole film and review the actual final output.
Do not claim viewer retention, licensing, framing or artistic quality from automated metrics alone.