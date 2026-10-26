# Hooks

The hook is the first 1–3 seconds: the **spoken opening** plus the **on-screen hook card** (`plan.hook.text`, shown
for `hook.duration` = 2.6 s by default). Most viewers decide to stay or leave here, so this is the most important
choice in the edit.

## Choosing a hook (do this every time)
1. **Know the payoff.** One sentence: what does the viewer get by the end? The hook promises exactly that, and
   nothing the video doesn't deliver (over-promising kills completion rate and comments call it out).
2. **Check this creator's data.** `ose perf summary` ranks hook patterns by average 3-second retention, then views.
   With ≥ 3 videos per pattern, prefer the top 2 patterns. With little data, rank by topic fit (`best_for`).
3. **Pull candidates.** `ose hooks list --lang pt|en [--pattern X] [--search word]`. Fill `{placeholders}` with
   specifics: numbers, names, timeframes. "I saved 11 hours a week" beats "I saved a lot of time".
4. **Check the footage.** Does the creator already say something hook-worthy? The best hook is often a line from the
   middle. Use `ose roughcut --hook-range START-END` to make it a cold open, and keep the on-screen card consistent
   with it.
5. **Present 3 options**, one per pattern, each with a one-line rationale, and recommend one.

## Rules
- On-screen text ≤ 9 words, readable in about 1.5 s, without repeating the spoken words verbatim (it complements them).
- The first spoken word starts ≤ 0.4 s in. No greetings, no "so…", no logo intro, no "in this video I'm going to…".
- Use specifics over adjectives, tension over information, and "you" over "I" (unless it's a story hook).
- Visual hook: begin on motion or a zoom-in (`zooms` at 0.0 s, `punch`, scale 1.15–1.25) or on the result itself.
- Language: write the hook in the video's spoken language. PT-BR should sound natural and casual ("tá", "pra",
  "você"), not like a literal translation.

## Patterns (in `assets/hooks.json`)
| Pattern | Why it works | Best for |
|---|---|---|
| curiosity-gap | Opens a loop the viewer must close | tips, stories, tech |
| contrarian | Challenges a belief → "wait, what?" | opinion, education, business |
| result-first | Payoff up front, then the how | tutorial, build, fitness, money |
| mistake-warning | Loss aversion | tips, career, tech, money |
| list-number | Bounded, scannable payoff | tips, tools, education |
| shortcut | Same result, less effort | tutorial, productivity |
| story | Narrative tension, personal stakes | vlog, career, founder |
| challenge-experiment | Uncertain outcome | vlog, tech, fitness |
| secret-insider | Exclusive knowledge, status | business, tech, career |
| comparison | Picks a side in a known debate | tools, tech, products |
| pov-relatable | Instant identification → shares | humor, student, work |
| direct-question | Addresses and qualifies the viewer | any |
| authority-proof | Credibility via numbers or experience | business, education |
| urgency-fomo | Time pressure, missing out | news, trends |
| transformation | Before/after contrast | build, fitness, design |

## Growing the library
- `ose hooks add --pattern contrarian --en "…" --pt "…"` saves to `~/.one-shot-editing/hooks.user.json`
  (it survives skill updates).
- When the user shares a viral video they like, extract its hook, generalise it into a template with
  placeholders, and add it.
- The video's 7-step system used a "255 proven hooks" document. Build the equivalent over time from real data rather
  than copying lists: log every posted video with `ose perf add` (hook text, pattern, views, 3 s retention,
  completion), and the ranking improves on its own.

## Performance loop
```bash
ose perf add --hook-pattern result-first --hook "I built this in 2 hours" --topic "side project" \
  --views 48000 --retention-3s-pct 71 --completion-pct 38 --shares 210 --platform tiktok
ose perf summary
```
The CSV lives at `~/.one-shot-editing/performance.csv`; the user can also edit it in a spreadsheet. Ask the user
for numbers 48–72 h after posting. TikTok Studio, Instagram Insights and YouTube Studio all show 3-second
retention (or "viewed vs swiped").
