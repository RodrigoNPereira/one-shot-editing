# plan.json schema

`proj/work/plan.json` holds every creative decision. **All times are seconds on the cut timeline** (after the rough
cut). Edit it with `ose plan` or directly. Either `end` or `duration` is accepted for spans and normalised on save.

```jsonc
{
  "platform": "tiktok",                       // tiktok | reels | shorts (safe zones, QA limits)
  "hook": {
    "text": "Nobody tells you this about X",  // on-screen hook card (top). Empty = no card
    "pattern": "curiosity-gap",               // for perf logging
    "duration": 2.6,                          // seconds the card stays
    "on_screen": true
  },
  "captions": { "style": "bold-pop", "words_per_chunk": 3, "enabled": true },
  "music": {
    "track": "mc81f17b",                      // library id or file path; {} = no music
    "volume_db": -18, "start_offset": 0, "duck": true
  },
  "broll": [
    { "asset": "b2871217", "start": 2.5, "duration": 1.8, "mode": "full", "source_in": 0 }   // mode: full | pip
  ],
  "zooms": [
    { "start": 0.0, "end": 1.2, "scale": 1.25, "style": "punch" },      // punch | smooth | slow; "auto": true = added by pacing
  ],
  "texts": [
    { "text": "1963", "start": 4.5, "end": 5.7, "style": "Title" }       // Title (big centre) | Card (boxed top)
  ],
  "sfx": [
    { "at": 2.5, "asset": "whoosh", "volume_db": -8 }   // built-ins: whoosh pop click ding boom riser, or a file path
  ],
  "cta": { "text": "Follow for part 2", "duration": 2.8, "start": null, "on_screen": true },
  "audio": { "clean": true }                  // highpass + denoise + compressor on the voice
}
```

## CLI helpers
```bash
ose plan proj --set hook.text="..." --set music.volume_db=-20 --set captions.style=impact
ose plan proj --set music={}                              # values are parsed as JSON when possible
ose plan proj --add-broll '{...}' --add-zoom '{...}' --add-text '{...}' --add-sfx '{...}'
ose plan proj --clear zooms                               # reset a list
ose pacing proj --reset --apply                           # remove auto zooms and recompute
```

## Other project files
```
proj/
  raw/              source video (symlink, or a copy with --copy)
  work/
    meta.json       source info, detected language, platform
    audio16k.wav    transcription audio
    transcript.json words with start/end/probability (source timeline)
    edl.json        segments to keep + every cut decision (ids for --keep)
    cut.mp4         the rough cut, 1080x1920 (no captions/music)
    cut_words.json  words remapped to the cut timeline (feeds captions and HyperFrames)
    plan.json       this file
    captions.ass/.srt/.json
  out/ final.mp4 · draft.mp4 · cover.jpg · contact_sheet.jpg · qa.json
```
