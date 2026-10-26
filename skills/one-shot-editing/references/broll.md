# B-roll library

Location: `~/.one-shot-editing/library/broll/`
```
_inbox/        ← drop anything here (videos, images, screen recordings, captures)
_unsorted/     ← ingested, waiting for labels
<category>/    ← labelled files (abstract, ui, code, people, city, product, reaction, meme…)
.thumbs/       ← thumbnails for the agent to look at
index.json
```

## Ingest → look → label
```bash
ose broll ingest                    # everything in _inbox (moved), or: ose broll ingest a.mp4 b.png [--copy]
ose broll pending                   # unlabelled items + thumbnail paths
```
**View the thumbnails** (they are images; open them) and write labels from what you actually see:
```bash
ose broll label <id> --category code --labels "vscode,typescript,dark theme,typing" --desc "VS Code typing a React hook"
```
Use 4–8 labels covering the subject, the action, the setting, colours and the mood. Write the description as a
sentence you could match against a transcript line. Videos are scene-split with PySceneDetect at ingest
(`scenes` in the index), so a long screen recording can provide several shots via `source_in`.

## Find and place
```bash
ose broll search "deploy vercel terminal" [--kind video|image] [--n 5]
ose plan proj --add-broll '{"asset":"<id>","start":6.1,"duration":2.2,"mode":"full","source_in":12.0}'
```
- `start` is on the cut timeline (`ose text proj --cut`). Start about 0.1 s before the word it illustrates.
- `mode`: `full` (covers the frame; images get a slow Ken Burns push) or `pip` (a framed window near the top, with
  the face still visible).
- `source_in`: where to start inside the B-roll video (use the scene list).
- Usage counts are tracked, and search prefers fresh assets so videos don't repeat the same shots.

## Sources
- The user's own clips and screen recordings (best: authentic).
- Web screenshots and recordings via `scripts/capture_web.sh` (agent-browser, phone viewport).
- App footage: see [app-footage.md](app-footage.md).
- Stock: Pexels and Pixabay (free licences). Download into `_inbox/` and credit when required.
- Designed inserts rendered with HyperFrames (title cards, animated stats, diagrams), dropped in as B-roll.
- Memes and reaction clips: copyright and fair-use risk; ask the user.
