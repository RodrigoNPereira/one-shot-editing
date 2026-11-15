# Retention rules

These are starting heuristics, not proven performance guarantees. Tune them with the creator's results and
the clip's purpose. Preserving meaning and intelligibility takes priority over runtime or effects frequency.

## Structure (≈ 20–45 s talking head)
| Time | Beat | Edit moves |
|---|---|---|
| 0–1 s | Hook line plus hook card | Start on a clear claim or payoff without dropping essential context |
| 1–3 s | Re-hook / stakes ("…and it took me 10 minutes") | Show the result if it clarifies the stakes; preserve useful context |
| 3 s – end-5 s | Payoff in 2–4 beats | Visualize meaningful actions and evidence; preserve continuity rather than illustrate every noun |
| last 3–5 s | CTA / loop line | CTA card; music swell or fade |

## Pacing
- **Review static stretches around ~3 s.** Changes include a jump cut, zoom in/out, B-roll in/out, an on-screen text
  or number, or a card. `ose pacing` measures this (`max_static`, `changes_per_10s`) and `--apply` fills the gaps
  with alternating zooms. Use a larger `--max` for demonstrations or emotional pauses; do not run `--apply`
  just to force an otherwise clear sequence to pass a pacing heuristic.
- Do not optimize a quota of changes per 10 s. A readable mechanism and a deliberate hold can outperform a
  succession of entrances; event counts are diagnostic, not artistic acceptance.
- **Jump cuts**: preserve good seams. Optional `ose pacing --apply --jumpcut` alternates zoom levels in the
  simple route; it is not a requirement for every cut or a substitute for reviewing pose and framing.
- **Pauses**: `tight` (TikTok default) keeps about 0.1 s of air around words, `natural` about 0.18 s, `loose` about
  0.3 s. Educational or emotional content can breathe more.
- **Emphasis zooms** (choose them yourself): punchlines, numbers, "the key is…", reveals. Use `punch` (instant
  1.2–1.3) for comedy or impact, `smooth` (eased 1.1–1.15) for explanations, and `slow` (gradual push) for stories.
  `smooth` eases back to the base scale before its end; `slow` still ends with an intentional scale reset.
  Counting a cut or zoom as a pacing event does not certify its continuity.
- **Transitions**: hard cuts by default. Use whooshes or zoom-through only at section changes, at most 1–2 per video.
  Fancy transitions between every cut look amateur.
- **B-roll**: 1–3 s each, cut on the word it illustrates (start about 0.1 s before the word). Use `pip` when the
  face matters (reactions, emotion) and `full` for demos and screens.
- **Sound design**: subtle licensed SFX on meaningful visual events, with the transient aligned to the event
  and gain auditioned per asset. A fixed gain or effect frequency is not a quality target; leave quiet beats.
  Music ducking does not duck the SFX. Follow [footage-overlays.md](footage-overlays.md) for designed output.
  Procedural candidates are optional via [earshot-sfx.md](earshot-sfx.md), not a mandatory sound on every event.

## Continuity and designed output

Review every seam with picture and audio context. Preserve useful breaths and clean hard cuts; repair
clipped phonemes and unintended framing/scale jumps. Do not use global face dissolves or effects to hide
bad cut points. Footage with explanatory overlays needs the HyperFrames storyboard/pilot route, not more
automatic zooms. Use [motion-direction.md](motion-direction.md) for Bang Motion / Shotcraft routing and
[footage-overlays.md](footage-overlays.md) for movement and sound acceptance checks.

## Content
- One idea per video. If the transcript has two ideas, propose two videos.
- Cut unnecessary setup only after listening in context. Preserve negation, quantities, qualifications,
  dependencies and the setup needed for the payoff. Fuzzy similarity alone cannot prove two takes mean the same thing.
- Open loops: tease the best item ("…and number 3 is the one nobody uses") to hold viewers until the end.
- End with a payoff, not with a fade-out of energy. The final words should be strong.

## Length targets
Start with a 20–60 s brief when appropriate, then let a complete idea determine the duration. QA's 12–75 s
warning is a local editorial heuristic, not a platform restriction or a prediction of performance.
Check current platform upload limits separately; neither this guide nor a passing QA score proves retention.
