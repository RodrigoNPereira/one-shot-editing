# Caption styles

All styles show **≤ 3 words** (max 18 characters) per chunk, break on pauses > 0.35 s and sentence ends, and
linger ≤ 0.5 s. They sit at about 70 % of the screen height, clear of the TikTok/Reels bottom UI and below the face.

| Style | Look | Use for |
|---|---|---|
| `bold-pop` (default) | Montserrat ExtraBold, UPPERCASE, white with black outline, **active word in yellow**, pop-in | Most talking heads; "Hormozi-style" |
| `impact` | Anton condensed, UPPERCASE, active word in green, pop-in | Hype, gaming, high-energy |
| `clean` | Montserrat Bold, sentence case, semi-transparent black box | Educational, corporate, calm |
| `minimal` | Montserrat Bold, sentence case, thin outline | Aesthetic, vlogs, storytelling |

```bash
ose captions proj --style impact --words 2
ose captions proj --none          # cards only (hook/CTA/text), no word captions
```
The style is saved in `plan.captions`, and `ose render` rebuilds the caption overlay from the plan every time.

## Other card styles (internal ASS styles)
- `Card`: hook and CTA. Dark text on white per-line boxes at the top, like TikTok's native text style.
- `Title`: big Anton word or number in the centre (`--add-text`). Use for stats, keywords, list numbers.

## Guidelines
- Captions should match speech exactly. Fix misheard words in `work/transcript.json` (edit `word`), then re-run
  `ose cut` (or just `ose captions`) and check names, brands and numbers.
- Write numbers as digits ("3x", "10k").
- Keep emoji out of word captions. They are OK in cards.
- For captions embedded behind the subject, kinetic typography or brand fonts, use the HyperFrames route
  (`embedded-captions` skill) with `work/cut_words.json`.

Fonts are bundled in `assets/fonts` under the SIL Open Font License (Montserrat, Anton). To add a brand font, drop
the TTF there and reference its family name in `captions.py` `STYLES`.
