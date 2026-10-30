# Platforms

The default `source` profile produces a native-detail lossless master, not a universal upload file.
Choose `--quality social` explicitly for **1080×1920, 30 fps, 8-bit H.264, AAC 48 kHz 256k, `+faststart`**.
Final audio defaults to measured two-pass −14 LUFS/−1.5 dBTP; both are configurable editorial targets, not
universal platform requirements. Set the platform with `ose init --platform` or `ose plan --set platform=reels`.

| | TikTok | Instagram Reels | YouTube Shorts |
|---|---|---|---|
| Conservative delivery limit | 10 min | 3 min | 3 min |
| Unsafe top | ~160 px | ~220 px | ~160 px |
| Unsafe bottom | ~480 px (caption, music, username) | ~420 px | ~400 px |
| Unsafe right | ~140 px (like/comment/share) | ~120 px | ~120 px |
| Cover | Chosen in app from a frame or uploaded | Uploaded cover, 4:5 crop in the profile grid | Frame chosen in app |
| Trending audio | In-app sound library | In-app (Reels audio) | In-app (Shorts audio) |

Notes:
- Reviewed 2026-10-30. [YouTube's three-minute Shorts policy](https://support.google.com/youtube/answer/15424877)
  also states that Shorts over one minute with active copyright claims are blocked globally.
  See [TikTok help](https://support.tiktok.com/en/using-tiktok/creating-videos) and
  [Instagram help](https://help.instagram.com/) for current account/product-specific limits. TikTok/Reels limits
  above are conservative project presets, not claims about every current upload path.
- Safe-zone insets are approximate editorial presets on a 1080x1920 design canvas, not certified UI geometry.
  Rendered QA scales with native-resolution output and samples glyph bounds/collisions. Inspect on-device.
- Keep the essential content inside the centre 4:5 area (1080×1350, y 285–1635) so the Instagram grid crop still
  works.
- Upload at full quality. In TikTok, enable "Allow high-quality uploads"; on Instagram, turn off "Data saver" and
  "Upload at highest quality".
- Post captions: hook restated + value + 3–5 relevant hashtags (one broad, two niche, one branded). PT-BR captions
  for PT-BR videos.
- For copyrighted music, publish without it and add the sound in-app. Platform sound libraries license trending
  music for use inside the app; baked-in songs risk muting or Content ID claims.
- Cross-posting: use a clean, explicitly prepared social delivery file rather than a platform-watermarked download.
