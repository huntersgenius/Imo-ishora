"""Deterministic Uzbek text processing.

Standard-library only. This module is pure: given the same input and the same
suffix configuration it always produces the same output. It knows nothing about
the dictionary contents; the dictionary service composes these primitives.

Pipeline responsibilities (per Part 02):
- normalize apostrophe variants used in Uzbek text
- lowercase
- collapse repeated whitespace
- remove meaning-neutral punctuation
- convert simple digits to Uzbek number words within the supported range
- tokenize into ordered words
- strip suffixes longest-first, returning candidate stems for validation

Suffix data comes from source.md's "Uzbek Suffix Reference".
"""

from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------- #
# Apostrophe normalization
# --------------------------------------------------------------------------- #
# Uzbek Latin uses o' and g'. Real-world input arrives with many apostrophe
# glyphs (typographic, backtick, modifier letters). Normalize them all to a
# single ASCII apostrophe so dictionary keys match deterministically.
_APOSTROPHE_VARIANTS = {
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u02bb": "'",  # modifier letter turned comma (canonical Uzbek o'/g')
    "\u02bc": "'",  # modifier letter apostrophe
    "\u0060": "'",  # grave accent / backtick
    "\u00b4": "'",  # acute accent
    "\u2032": "'",  # prime
    "`": "'",
    "’": "'",
    "‘": "'",
}

# Suffixes, longest-first as specified in source.md. Longest-first ordering is
# essential: stripping "moqda" must be attempted before "da".
SUFFIXES_LONGEST_FIRST: tuple[str, ...] = (
    "moqda", "yotir", "yotgan", "moqchi", "aylik", "ingiz",
    "imiz", "lari", "miz", "lar", "ning", "gan", "dan", "adi",
    "ydi", "lik", "siz", "roq", "man", "san", "sin", "ish", "chi",
    "da", "ga", "ni", "li", "di", "ar", "im", "ng", "in", "si", "i",
)

# Digit -> Uzbek number word, covering the supported demo range (0..20).
_DIGIT_WORDS: dict[int, str] = {
    0: "nol",
    1: "bir",
    2: "ikki",
    3: "uch",
    4: "to'rt",
    5: "besh",
    6: "olti",
    7: "yetti",
    8: "sakkiz",
    9: "to'qqiz",
    10: "o'n",
    11: "o'n bir",
    12: "o'n ikki",
    13: "o'n uch",
    14: "o'n to'rt",
    15: "o'n besh",
    16: "o'n olti",
    17: "o'n yetti",
    18: "o'n sakkiz",
    19: "o'n to'qqiz",
    20: "yigirma",
}

MAX_SUPPORTED_NUMBER = max(_DIGIT_WORDS)

# Keep apostrophes and digits; strip other punctuation. We replace punctuation
# with a space so "salom,rahmat" becomes two tokens rather than one.
_PUNCTUATION_RE = re.compile(r"[^\w'\s]", flags=re.UNICODE)
_DIGIT_TOKEN_RE = re.compile(r"\d+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_apostrophes(text: str) -> str:
    """Replace every apostrophe variant with a single ASCII apostrophe."""
    return "".join(_APOSTROPHE_VARIANTS.get(ch, ch) for ch in text)


def convert_digits(text: str) -> str:
    """Convert standalone digit runs to Uzbek number words within range.

    Out-of-range numbers are left as-is; they will simply fail dictionary
    lookup and be reported as not found, which is the honest behavior.
    """

    def _replace(match: re.Match[str]) -> str:
        value = int(match.group())
        return _DIGIT_WORDS.get(value, match.group())

    return _DIGIT_TOKEN_RE.sub(_replace, text)


def normalize_text(text: str) -> str:
    """Full normalization: NFC, apostrophes, lowercase, digits, punctuation, spacing."""
    text = unicodedata.normalize("NFC", text)
    text = normalize_apostrophes(text)
    text = text.lower()
    text = convert_digits(text)
    text = _PUNCTUATION_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def tokenize(normalized_text: str) -> list[str]:
    """Split already-normalized text into ordered word tokens."""
    if not normalized_text:
        return []
    return normalized_text.split(" ")


def candidate_stems(token: str) -> list[str]:
    """Return safe suffix-stripped stem candidates for a token, longest-first.

    The caller validates each candidate against the dictionary and accepts the
    first one that exists. A minimum stem length of 2 prevents degenerate
    matches (e.g. stripping a one-letter word to nothing).
    """
    stems: list[str] = []
    seen: set[str] = set()
    for suffix in SUFFIXES_LONGEST_FIRST:
        if token.endswith(suffix) and len(token) - len(suffix) >= 2:
            stem = token[: -len(suffix)]
            if stem and stem not in seen:
                seen.add(stem)
                stems.append(stem)
    return stems


__all__ = [
    "MAX_SUPPORTED_NUMBER",
    "SUFFIXES_LONGEST_FIRST",
    "candidate_stems",
    "convert_digits",
    "normalize_apostrophes",
    "normalize_text",
    "tokenize",
]
