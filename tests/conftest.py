import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "one-shot-editing" / "scripts"))


def make_words(spec):
    """spec: list of (word, start, end) -> transcript words."""
    return [{"word": w, "start": s, "end": e, "prob": 0.95} for w, s, e in spec]


def sentence(text, start, step=0.3, gap=0.0):
    out, t = [], start
    for w in text.split():
        out.append((w, round(t, 3), round(t + step - 0.05, 3)))
        t += step + gap
    return out


@pytest.fixture
def words_factory():
    return lambda *parts: make_words([w for p in parts for w in p])
