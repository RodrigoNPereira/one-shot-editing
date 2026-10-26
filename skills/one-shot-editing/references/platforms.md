# Platforms

Output for all platforms: **1080×1920, 30 fps, H.264 High, yuv420p, AAC 48 kHz 192k, `+faststart`, loudness −14
LUFS, true peak ≤ −1.5 dB**. Set the platform with `ose init --platform` or `ose plan --set platform=reels`.

| | TikTok | Instagram Reels | YouTube Shorts |
|---|---|---|---|
| Max length | 10 min (upload) | 3 min | 3 min |
| Sweet spot | 21–34 s | 15–30 s | 20–50 s |
| Unsafe top | ~160 px | ~220 px | ~160 px |
| Unsafe bottom | ~480 px (caption, music, username) | ~420 px | ~400 px |
| Unsafe right | ~140 px (like/comment/share) | ~120 px | ~120 px |
| Cover | Chosen in app from a frame or uploaded | Uploaded cover, 4:5 crop in the profile grid | Frame chosen in app |
| Trending audio | In-app sound library | In-app (Reels audio) | In-app (Shorts audio) |

Notes:
- Keep the essential content inside the centre 4:5 area (1080×1350, y 285–1635) so the Instagram grid crop still
  works.
- Upload at full quality. In TikTok, enable "Allow high-quality uploads"; on Instagram, turn off "Data saver" and
  "Upload at highest quality".
- Post captions: hook restated + value + 3–5 relevant hashtags (one broad, two niche, one branded). PT-BR captions
  for PT-BR videos.
- For copyrighted music, publish without it and add the sound in-app. Platform sound libraries license trending
  music for use inside the app; baked-in songs risk muting or Content ID claims.
- Cross-posting: TikTok's watermarked download is penalised on Reels and Shorts. Always upload the clean
  `final.mp4`.
