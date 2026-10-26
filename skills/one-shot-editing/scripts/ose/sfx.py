"""Built-in, licence-free sound effects synthesised with ffmpeg (cached under OSE_HOME/cache/sfx)."""
from __future__ import annotations

from pathlib import Path

from .common import OSE_HOME, OseError, ffmpeg

BUILTIN = {
    "whoosh": "anoisesrc=d=0.45:c=pink:a=0.7:r=48000,highpass=f=500,lowpass=f=5000,"
              "afade=t=in:d=0.22:curve=exp,afade=t=out:st=0.22:d=0.23:curve=exp",
    "pop": "aevalsrc='0.8*sin(2*PI*(500+4000*exp(-60*t))*t)*exp(-35*t)':d=0.15:s=48000",
    "click": "aevalsrc='0.7*sin(2*PI*2200*t)*exp(-120*t)':d=0.05:s=48000",
    "ding": "aevalsrc='0.5*sin(2*PI*1320*t)*exp(-5*t)+0.25*sin(2*PI*2640*t)*exp(-8*t)':d=0.9:s=48000",
    "boom": "aevalsrc='0.9*sin(2*PI*(45+80*exp(-12*t))*t)*exp(-4*t)':d=0.9:s=48000",
    "riser": "anoisesrc=d=1.2:c=white:a=0.4:r=48000,highpass=f=800,afade=t=in:d=1.15:curve=exp,afade=t=out:st=1.15:d=0.05",
}


def resolve(name_or_path: str) -> Path:
    p = Path(str(name_or_path)).expanduser()
    if p.exists():
        return p
    key = str(name_or_path).lower()
    if key not in BUILTIN:
        raise OseError(f"unknown sfx {name_or_path!r}: use a file path or one of {', '.join(BUILTIN)}")
    out = OSE_HOME / "cache" / "sfx" / f"{key}.wav"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg(["-f", "lavfi", "-i", BUILTIN[key], "-ac", "2", str(out)])
    return out
