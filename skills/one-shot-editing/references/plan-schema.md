# plan.json schema

`proj/work/plan.json` holds every creative decision. **All times are seconds on the cut timeline** (after the rough
cut). Edit it with `ose plan` or directly. Either `end` or `duration` is accepted for spans and normalised on save.
The machine-readable schema is `assets/plan.schema.json`. Unknown keys, invalid types, non-finite numbers,
negative/reversed spans and unsupported enum values fail explicitly. Rendering also checks timeline bounds
and asset availability.

```jsonc
{
  "schema_version": 1,
  "output": { "profile": "source" },          // source (default, lossless master) | social (explicit conversion)
  "framing": { "tracking": "dynamic", "max_speed": 0.15 }, // optional center: 0..1 overrides tracking
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
  "audio": { "clean": false, "normalization": "two-pass", "lufs": -14, "true_peak": -1.5, "lra": 11 }
                                            // normalization: two-pass | dynamic | off; clean opts into denoise/compression
}
```

## CLI helpers
```bash
ose plan proj --set hook.text="..." --set music.volume_db=-20 --set captions.style=impact
ose plan proj --set music={}                              # values are parsed as JSON when possible
ose plan proj --add-broll '{...}' --add-zoom '{...}' --add-text '{...}' --add-sfx '{...}'
ose plan proj --clear zooms                               # reset a list
ose pacing proj --reset --apply                           # remove auto zooms and recompute
ose plan proj --accept-timeline                           # only AFTER reviewing placements against changed cuts
```

## Other project files
```
proj/
  project.json      source info, language, platform, rough-cut quality and framing mode
  raw/              source video (symlink, or a copy with --copy)
  work/
    audio16k.wav    transcription audio
    transcript.json words with start/end/probability (source timeline)
    edl.json        segments, cut decisions (ids for --keep), review candidates, transcript fingerprint
    cut.mkv         lossless FFV1/float-PCM cut at source-profile dimensions/FPS (no captions/music)
    cut.provenance.json  input fingerprints, quality settings and hashes of cut/words
    approvals.json revision-bound cut/final approvals with review rationale
    cut_words.json  words remapped to the cut timeline (feeds captions and HyperFrames)
    plan.json       this file
    captions.ass/.srt/.json
  out/ final.mp4 · final.mp4.provenance.json · draft.mp4 · cover.jpg · contact_sheet.jpg · qa.json
```

## Quality is a requirement, not an optional optimization

`output.profile=source` is the default: preserve supported SDR/CFR source frame rate, bit depth, chroma and
color tags; retain native portrait/cropped resolution; use lossless intermediates and lossless final video.
Never silently substitute draft quality, 30 fps, 8-bit or 1080p for a higher-quality source. HDR/Dolby Vision,
non-square pixels, unsupported formats and ambiguous/VFR rates require an explicit supported workflow.
Cropping/resampling/effects change the image; no claim of pixel identity applies across those transformations.

`output.profile=social` explicitly accepts 1080x1920/30 fps/8-bit H.264/AAC delivery conversion.
Changing profiles invalidates the cut. For browser handoff without changing the master, use
`ose export proj --format browser`. Lossless masters can be large and may not play in every browser/platform.

## Reruns and review

`edl.json` is the source of cut decisions, not `plan.json`. Its `review` array records similar take pairs
whose quantities or negation differ. Both alternatives remain in the cut unless you make an explicit edit.
`stats.review_required` counts those candidates; `roughcut --report` displays them and QA warns about them.
Review the deletion reel with `ose review proj --reel`, then persist approval with
`ose review proj --approve cut --note "..."`. The ledger is bound to the exact EDL revision. Final approval
additionally binds the plan, rendered file and asset bytes. Technical QA and human approval remain separate.

`transcript_sha256` identifies the transcript used to build a new EDL. With `transcript_fingerprint_version: 1`,
it hashes language, ordered words, timestamps and confidence, ignoring formatting, elapsed time and unrelated
metadata. The earlier raw-file fingerprint format remains readable. A changed transcript causes `auto`
and `cut` to stop until you deliberately rebuild/review the EDL. Source bytes are also fingerprinted.
Old transcripts/EDLs require retranscription or explicit `ose provenance proj --adopt` after manual review;
old intermediates must be rebuilt. Adoption asserts a relationship, not transcription accuracy.

`auto` preserves an existing EDL. `auto --rebuild-edl` replaces it. After any timeline change, recheck every
plan timestamp and run `plan --accept-timeline`; placements are not automatically remapped. The plan's
`edl_revision` records that confirmation. `render --draft` previews the existing cut without
changing its editorial decisions. Final rendering promotes a recorded draft-quality cut before encoding.
