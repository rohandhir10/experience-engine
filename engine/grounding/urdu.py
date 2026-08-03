"""Urdu syllable counting — Perso-Arabic script (Nastaliq/Naskh).

Urdu is written in an ABJAD, not an abugida like Devanagari: short vowels
are not letters, they are optional diacritics (i'raab) that ordinary
written Urdu drops almost entirely — song lyrics, prose, and most
poetry compilations alike. Without them, a bare consonant string is
genuinely ambiguous: there is no dictionary or model in this codebase
that could recover the missing vowels, and guessing would produce a
number that looks exact and is fabricated. This is exactly why
`engine/rhythm.py::phrase_end_sustainability` already declines Urdu
output outright rather than approximating it — Urdu isn't a smaller
version of the Hindi schwa-deletion problem, it's a different, harder
one, for the same underlying reason.

The one case that genuinely is solvable: text that DOES carry the
diacritics (fully-voweled Urdu, as printed in some diwans and religious
texts for correct recitation). Given every short vowel written
explicitly, syllable counting is deterministic — the same well-
established algorithm used for fully-voweled Arabic. This module
implements that case and nothing else. Undiacritized text — the
overwhelming majority of real pasted lyrics — returns None, honestly,
rather than guessing.
"""
from __future__ import annotations

import re

from .base import GroundingResult, register_counter

_ARABIC_RANGE = (0x0600, 0x06FF)
_ARABIC_EXT_RANGE = (0x0750, 0x077F)

# Short vowel diacritics — each marks one vowel on the preceding letter.
_FATHA = "َ"  # zabar
_DAMMA = "ُ"  # pesh
_KASRA = "ِ"  # zer
_SHORT_VOWELS = {_FATHA, _DAMMA, _KASRA}

_TANWIN = {"ً", "ٌ", "ٍ"}  # nunation — vowel + trailing "n", one nucleus
_SUKUN = "ْ"    # explicit "no vowel" — closes a syllable
_SHADDA = "ّ"   # gemination marker, not a vowel itself

_DIACRITICS = _SHORT_VOWELS | _TANWIN | {_SUKUN, _SHADDA}

# Long vowel letters (matres lectionis). ا/آ/ے are unambiguously vowels;
# و and ی double as consonants (w/y) and are only a vowel when bare (no
# diacritic, no sukun of their own) — otherwise they behave the same as
# any other letter under the rules below.
_UNAMBIGUOUS_LONG_VOWELS = set("اآے")
_AMBIGUOUS_LONG_VOWELS = set("وی")

_WORD_SPLIT_RE = re.compile(r"[\s۔،؛؟!,.;:—\-]+")

_MIN_DIACRITIC_DENSITY = 0.5


def _in_arabic_script(c: str) -> bool:
    cp = ord(c)
    return _ARABIC_RANGE[0] <= cp <= _ARABIC_RANGE[1] or _ARABIC_EXT_RANGE[0] <= cp <= _ARABIC_EXT_RANGE[1]


def _is_diacritic(c: str) -> bool:
    return c in _DIACRITICS


def _is_letter(c: str) -> bool:
    return _in_arabic_script(c) and not _is_diacritic(c)


def _has_urdu_script(text: str) -> bool:
    return any(_in_arabic_script(c) for c in text)


def _diacritic_density(word: str) -> float:
    """Fraction of letters immediately followed by an explicit diacritic.

    Ordinary undiacritized Urdu scores near 0 — this is the gate that
    tells apart the rare fully-voweled text this module can honestly
    count from the normal case it can't.
    """
    letters = [c for c in word if _is_letter(c)]
    if not letters:
        return 0.0
    marked = sum(
        1
        for i, c in enumerate(word)
        if _is_letter(c) and i + 1 < len(word) and word[i + 1] in _DIACRITICS
    )
    return marked / len(letters)


def _count_word_nuclei(word: str) -> int:
    nuclei = 0
    i = 0
    n = len(word)
    while i < n:
        c = word[i]
        if not _is_letter(c):
            i += 1
            continue
        nxt = word[i + 1] if i + 1 < n else ""

        if nxt in _SHORT_VOWELS or nxt in _TANWIN:
            nuclei += 1
            i += 2
            continue
        if nxt == _SHADDA:
            after = word[i + 2] if i + 2 < n else ""
            if after in _SHORT_VOWELS or after in _TANWIN:
                nuclei += 1
                i += 3
            else:
                i += 2  # geminated consonant with no vowel shown
            continue
        if nxt == _SUKUN:
            i += 2  # this letter (consonant or glide) closes a syllable
            continue
        if c in _UNAMBIGUOUS_LONG_VOWELS:
            nuclei += 1
            i += 1
            continue
        if c in _AMBIGUOUS_LONG_VOWELS:
            # bare و/ی with no diacritic or sukun of its own — standing in
            # for the vowel itself (mater lectionis), one nucleus
            nuclei += 1
            i += 1
            continue
        i += 1  # bare consonant with nothing following — no nucleus
    return nuclei


def count_urdu(text: str) -> GroundingResult | None:
    if not _has_urdu_script(text):
        return None
    words = [w for w in _WORD_SPLIT_RE.split(text) if w]
    if not words:
        return None

    densities = [_diacritic_density(w) for w in words]
    if sum(densities) / len(densities) < _MIN_DIACRITIC_DENSITY:
        # The vowels literally aren't written — there is nothing honest
        # to count them from. This is the common case for real lyrics.
        return None

    total = sum(_count_word_nuclei(w) for w in words)
    return GroundingResult(
        value=total,
        unit="syllables",
        language="Urdu",
        caveat=(
            "counted from explicit i'raab diacritics in this text — most "
            "Urdu, including most pasted lyrics, omits them entirely, in "
            "which case this counter declines rather than guesses"
        ),
    )


register_counter("ur", count_urdu)
