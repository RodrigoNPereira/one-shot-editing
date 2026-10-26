# one-shot-editing

An agent skill that turns raw talking-head footage into a finished short-form vertical video (TikTok / Reels / Shorts) in one shot.

## Pipeline

1. Hook: picked from a hook library and scored against your past performance
2. Rough cut: word-level timestamps (WhisperX); removes pauses, breaths and filler words; keeps the best take
3. Captions: 2–3 words on screen at a time
4. Music: library built with yt-dlp, tagged by mood/BPM, mixed under the voice
5. B-roll: automatic labelling and matching; optional app footage (your recordings or a repo the agent runs)
6. Pacing: a visual change at least every ~3 s, with punch-in zooms
7. Call to action

Plus audio cleanup, 16:9→9:16 reframe, captions/metadata, QA and platform export.

- Languages: PT-BR and EN (detected automatically)
- Rendering: ffmpeg for the cut and audio; HyperFrames for designed output

## Status

🚧 Work in progress.
