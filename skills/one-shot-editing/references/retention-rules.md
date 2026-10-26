# Retention rules

## Structure (≈ 20–45 s talking head)
| Time | Beat | Edit moves |
|---|---|---|
| 0–1 s | Hook line plus hook card | Start mid-sentence or on the punchline; optional punch-in zoom at 0.0 s |
| 1–3 s | Re-hook / stakes ("…and it took me 10 minutes") | Cut immediately; a B-roll flash of the result |
| 3 s – end-5 s | Payoff in 2–4 beats | A jump cut between beats; B-roll on every concrete noun you can show; text on numbers |
| last 3–5 s | CTA / loop line | CTA card; music swell or fade |

## Pacing
- **Visual change at least every ~3 s.** Changes include a jump cut, zoom in/out, B-roll in/out, an on-screen text
  or number, or a card. `ose pacing` measures this (`max_static`, `changes_per_10s`) and `--apply` fills the gaps
  with alternating zooms.
- Target 4–8 changes per 10 s for talking heads. Above about 12 it feels frantic, unless that's the creator's style.
- **Jump cuts**: when the same framing is cut, alternate the zoom level (1.0 ↔ 1.12) so the cut reads as intentional.
  `ose pacing --apply --jumpcut` does this.
- **Pauses**: `tight` (TikTok default) keeps about 0.1 s of air around words, `natural` about 0.18 s, `loose` about
  0.3 s. Educational or emotional content can breathe more.
- **Emphasis zooms** (choose them yourself): punchlines, numbers, "the key is…", reveals. Use `punch` (instant
  1.2–1.3) for comedy or impact, `smooth` (eased 1.1–1.15) for explanations, and `slow` (gradual push) for stories.
- **Transitions**: hard cuts by default. Use whooshes or zoom-through only at section changes, at most 1–2 per video.
  Fancy transitions between every cut look amateur.
- **B-roll**: 1–3 s each, cut on the word it illustrates (start about 0.1 s before the word). Use `pip` when the
  face matters (reactions, emotion) and `full` for demos and screens.
- **Sound design**: subtle SFX on visual events (pop on text, whoosh on B-roll entry) at about -10 dB. Never more
  than one SFX per 2–3 s.

## Content
- One idea per video. If the transcript has two ideas, propose two videos.
- Cut setup ("so basically", "what I wanted to say is") and any "context" the viewer doesn't need.
- Open loops: tease the best item ("…and number 3 is the one nobody uses") to hold viewers until the end.
- End with a payoff, not with a fade-out of energy. The final words should be strong.

## Length targets
TikTok: 21–34 s is the sweet spot for most talking heads; up to 60 s if the story holds. Reels: 15–30 s.
Shorts: under 60 s performs best (up to 3 min is allowed). QA warns outside 12–75 s.
