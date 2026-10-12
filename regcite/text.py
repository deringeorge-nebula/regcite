

from __future__ import annotations

import re

STOPWORDS = frozenset(
    """
    a an and are as at be been by for from has have how in into is it its
    of on or that the their there these this those to was were what when
    where which who will with within without do does i my me we our you
    your any all can could would should about than then also such
    """.split()
)

_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


_QUOTE_CHARS = str.maketrans(
    {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "−": "-", " ": " ",
    }
)


def normalize_for_quote(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_QUOTE_CHARS)).strip()
