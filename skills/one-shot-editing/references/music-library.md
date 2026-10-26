# Music library

Location: `~/.one-shot-editing/library/music/` (audio files plus `index.json`). It is shared across all projects.

## Adding tracks
```bash
ose music add "https://youtu.be/…" --tags "phonk,gym" --vibe "aggressive night drive" --license platform-only
ose music add ~/Downloads/track.mp3 --title "Lo-fi 3" --license royalty-free --tags "lofi,study"
ose music tag <id> --tags "anime,epic" --vibe "final boss energy" --moods hype,dramatic
ose music list | ose music remove <id> [--delete]
```
`add` downloads with **yt-dlp** (YouTube, SoundCloud, Bandcamp, direct URLs…) to mp3 and then analyses it with
librosa: **BPM, energy (0–1), brightness, onset density, and a mood guess** (hype / upbeat / chill / calm / dark /
dramatic). You add the human part: **tags and a "vibe" sentence**, which is what makes suggestions good. The
video's creator files songs "by feeling and vibe". Do the same: listen to the user's description or infer it from
the source (title, genre), and write a vivid vibe line.

## Suggesting
```bash
ose music suggest "funny fail story, light and bouncy" [--mood upbeat] [--energy 0.6] [--min-duration 30]
```
The score combines token overlap with tags, vibe and title, plus mood and energy match, minus a penalty for tracks
used often (to keep variety). Pick from the top 3 using the topic and tone: tutorials → chill or lofi;
stories → dramatic or calm; hype or results → phonk, EDM or trending; humor → quirky game or cartoon OSTs.

## Mixing
`plan.music`: `track` (id/path), `volume_db` (default −16; use −18 to −22 under dense talk), `start_offset` (skip
an intro, in seconds), `duck` (true: sidechain-compressed under the voice). The track loops if it's shorter than
the video and fades out at the end. Beat-matching cuts to the BPM is optional polish for montage sections.

## Licences (`--license`)
| Value | Meaning | Export with music baked in? |
|---|---|---|
| `owned` | The user made or bought it with a licence | ✅ |
| `royalty-free` | Licensed library (Epidemic, Artlist, YouTube Audio Library, Pixabay) | ✅ (check terms) |
| `cc-by` | Creative Commons with attribution (e.g. incompetech) | ✅ credit the artist in the post caption |
| `platform-only` | Trending or commercial songs | ⚠ preview only. Post without music and add the sound in-app |
| `unknown` | Not checked | ⚠ treat as platform-only |

QA warns about `unknown` and `platform-only`. The creator's mix (half trending, half game and anime soundtracks)
is common, but those tracks are copyrighted. The safe pattern is to render `final.mp4` **without** the track
(`ose plan --set music={}` → render), keep a preview version with it, and add the same sound in the app. Be
explicit with the user about this.

## Free/legal sources
YouTube Audio Library, Pixabay Music, Free Music Archive (check the licence per track), incompetech (CC-BY), and
Uppbeat (free tier with credit). Platform sound libraries are the place for trending audio.
