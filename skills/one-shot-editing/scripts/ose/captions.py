"""Captions (2-3 words at a time, active word highlight) plus hook/CTA text cards, as ASS subtitles."""
from __future__ import annotations

from .common import ASSETS, H, W, Project, load_plan, log, read_json, write_json

SENT_BREAK = (".", "?", "!", "…", ",", ";", ":")

# ASS colours are &HAABBGGRR
STYLES = {
    "bold-pop": {"font": "Montserrat ExtraBold", "size": 84, "color": "&H00FFFFFF", "outline": 7, "shadow": 0,
                 "border": 1, "back": "&H00000000", "outline_color": "&H00000000", "upper": True,
                 "highlight": "&H0000E5FF", "pop": True, "margin_v": 560},
    "impact": {"font": "Anton", "size": 112, "color": "&H00FFFFFF", "outline": 8, "shadow": 2,
               "border": 1, "back": "&H80000000", "outline_color": "&H00000000", "upper": True,
               "highlight": "&H0014FF39", "pop": True, "margin_v": 560},
    "clean": {"font": "Montserrat Bold", "size": 62, "color": "&H00FFFFFF", "outline": 14, "shadow": 0,
              "border": 3, "back": "&H00000000", "outline_color": "&H99000000", "upper": False,
              "highlight": None, "pop": False, "margin_v": 520},
    "minimal": {"font": "Montserrat Bold", "size": 64, "color": "&H00FFFFFF", "outline": 3, "shadow": 1,
                "border": 1, "back": "&H80000000", "outline_color": "&H00000000", "upper": False,
                "highlight": None, "pop": False, "margin_v": 480},
}


def chunk_words(words, max_words=3, max_chars=18, gap_break=0.35, linger=0.5):
    chunks, cur = [], []
    for i, w in enumerate(words):
        if cur:
            chars = sum(len(x["word"]) + 1 for x in cur) + len(w["word"])
            gap = w["start"] - cur[-1]["end"]
            if (len(cur) >= max_words or chars > max_chars or gap > gap_break
                    or cur[-1]["word"].rstrip().endswith(SENT_BREAK)):
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        start = c[0]["start"]
        end = max(c[-1]["end"] + linger, start + 0.2)
        if i + 1 < len(chunks):
            end = min(end, chunks[i + 1][0]["start"])
        out.append({"start": round(start, 3), "end": round(end, 3), "words": c})
    return out


def _ts(t):
    t = max(t, 0)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(text, upper):
    t = text.strip().replace("{", "(").replace("}", ")").replace("\\", "/")
    t = t.rstrip(".,;:")
    return t.upper() if upper else t


def _header(style):
    s = STYLES[style]
    bold = 0
    rows = [
        f"Style: Cap,{s['font']},{s['size']},{s['color']},&H000000FF,{s['outline_color']},{s['back']},{bold},0,0,0,"
        f"100,100,0,0,{s['border']},{s['outline']},{s['shadow']},2,80,80,{s['margin_v']},1",
        "Style: Card,Montserrat ExtraBold,66,&H00101010,&H000000FF,&H00FFFFFF,&H00000000,0,0,0,0,"
        "100,100,0,0,3,18,0,8,110,110,300,1",  # BorderStyle 3: per-line boxes, like TikTok native text
        "Style: Title,Anton,120,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,"
        "100,100,0,0,1,8,3,5,90,90,0,1",
    ]
    return "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0",
        "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        *rows, "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])


def caption_events(chunks, style):
    s = STYLES[style]
    ev = []
    pop = r"{\fscx80\fscy80\t(0,90,\fscx100\fscy100)}" if s["pop"] else ""
    for c in chunks:
        toks = [_clean(w["word"], s["upper"]) for w in c["words"]]
        if not s["highlight"]:
            ev.append((c["start"], c["end"], "Cap", pop + " ".join(toks)))
            continue
        for k, w in enumerate(c["words"]):
            a = c["start"] if k == 0 else w["start"]
            b = c["words"][k + 1]["start"] if k + 1 < len(c["words"]) else c["end"]
            if b - a < 0.02:
                continue
            text = " ".join((rf"{{\c{s['highlight']}}}{t}{{\c{s['color']}}}" if j == k else t)
                            for j, t in enumerate(toks))
            ev.append((a, b, "Cap", (pop if k == 0 else "") + text))
    return ev


def card_events(plan, duration):
    ev = []
    hook = plan.get("hook") or {}
    if hook.get("text") and hook.get("on_screen", True):
        ev.append((0, min(hook.get("duration", 2.6), duration), "Card",
                   r"{\fad(80,120)}" + _clean(hook["text"], False)))
    cta = plan.get("cta") or {}
    if cta.get("text") and cta.get("on_screen", True):
        d = cta.get("duration", 2.8)
        st = cta.get("start")
        st = max(duration - d, 0) if st is None else st
        ev.append((st, min(st + d, duration), "Card", r"{\fad(120,0)}" + _clean(cta["text"], False)))
    for t in plan.get("texts", []):
        ev.append((t["start"], t["end"], t.get("style", "Title"), r"{\fad(60,60)}" + _clean(t["text"], False)))
    return ev


def build_ass(words, plan, duration, style="bold-pop", max_words=3, show_captions=True):
    words = [word for word in words if word["start"] < duration]
    chunks = chunk_words(words, max_words=max_words) if show_captions else []
    for chunk in chunks:
        chunk["end"] = min(chunk["end"], duration)
    ev = caption_events(chunks, style) + card_events(plan, duration)
    lines = [_header(style)]
    for a, b, st, text in sorted(ev, key=lambda e: e[0]):
        layer = 1 if st != "Cap" else 0
        lines.append(f"Dialogue: {layer},{_ts(a)},{_ts(b)},{st},,0,0,0,,{text}")
    return "\n".join(lines) + "\n", chunks


def to_srt(chunks):
    def ts(t):
        ms = int(round(t * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return "\n".join(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{' '.join(w['word'] for w in c['words'])}\n"
                     for i, c in enumerate(chunks, 1))


def run_captions(project: Project, *, style=None, max_words=None, show_captions=True) -> dict:
    project.require()
    from .common import probe
    words = read_json(project.cut_words)["words"]
    plan = load_plan(project)
    cap = plan.setdefault("captions", {})
    style = style or cap.get("style", "bold-pop")
    max_words = max_words or cap.get("words_per_chunk", 3)
    if style not in STYLES:
        raise SystemExit(f"unknown caption style {style}; choose from {', '.join(STYLES)}")
    duration = probe(project.cut)["duration"]
    cap.update(style=style, words_per_chunk=max_words, enabled=bool(show_captions))
    write_json(project.plan, plan)  # persisted so `ose render` can rebuild the overlay after plan edits
    ass, chunks = build_ass(words, plan, duration, style, max_words, show_captions=cap["enabled"])
    project.captions_ass.write_text(ass, encoding="utf-8")
    (project.work / "captions.srt").write_text(to_srt(chunks), encoding="utf-8")
    write_json(project.work / "captions.json",
               [{"start": c["start"], "end": c["end"], "text": " ".join(w["word"] for w in c["words"])} for c in chunks])
    log(f"{len(chunks)} caption chunks ({style}) -> {project.captions_ass}")
    return {"chunks": len(chunks), "style": style, "ass": str(project.captions_ass), "fonts": str(ASSETS / 'fonts')}
