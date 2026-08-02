"""Spanish syllable counting, with synalepha.

Spanish syllabification is rule-governed and needs no dictionary, but a
naive vowel-group count is wrong for verse in one specific, very common
way: **synalepha** (sinalefa). When a word ends in a vowel and the next
begins with a vowel, they merge into a single syllable across the word
boundary — "mi alma" is *mial-ma*, two syllables, not three. Spanish
verse is counted this way as a matter of course, so ignoring synalepha
systematically overcounts every line.

Within a word, the counting rules are:
  - Strong vowels (a, e, o and their accented forms) next to each other
    are a **hiatus**: two syllables (po-e-ta).
  - Strong + weak, or weak + weak, form a **diphthong**: one syllable
    (ai-re, cie-lo).
  - An *accented* weak vowel (í, ú) breaks the diphthong back into a
    hiatus (dí-a).
  - h is silent and does not block either process (des-hi-dra-tar,
    and "la hora" still merges).

Deliberately NOT applied: the verse-length convention that adds a
syllable for a line ending in an *agudo* word and subtracts one for an
*esdrújulo*. That is a metrical convention for counting a line of verse,
not a count of the syllables actually present, and applying it silently
would make the number mean something different from every other
language's count here. It is named in the caveat instead.
"""
from __future__ import annotations

import re
import unicodedata

from .base import GroundingResult, register_counter

_STRONG = set("aeoáéó")
_WEAK = set("iuü")
_ACCENTED_WEAK = set("íú")
_VOWELS = _STRONG | _WEAK | _ACCENTED_WEAK

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
# Spanish-specific letters; used to decline text that clearly isn't Spanish.
_SPANISH_HINT_RE = re.compile(r"[ñáéíóúü¿¡]", re.IGNORECASE)


def _is_vowel(ch: str) -> bool:
    return ch in _VOWELS


def _breaks_diphthong(first: str, second: str) -> bool:
    """True when two adjacent vowels are a hiatus (two syllables)."""
    if first in _ACCENTED_WEAK or second in _ACCENTED_WEAK:
        return True  # dí-a, ba-úl
    if first in _STRONG and second in _STRONG:
        return True  # po-e-ta, ca-os
    return False


def _count_word(word: str) -> int:
    """Syllable nuclei in one word, before synalepha."""
    word = word.lower()
    syllables = 0
    i = 0
    while i < len(word):
        if not _is_vowel(word[i]):
            i += 1
            continue
        # Walk the maximal vowel run, splitting it at each hiatus.
        syllables += 1
        j = i
        while j + 1 < len(word):
            nxt = word[j + 1]
            if nxt == "h" and j + 2 < len(word) and _is_vowel(word[j + 2]):
                # Silent h inside a word doesn't block the vowel run.
                if _breaks_diphthong(word[j], word[j + 2]):
                    syllables += 1
                j += 2
                continue
            if not _is_vowel(nxt):
                break
            if _breaks_diphthong(word[j], nxt):
                syllables += 1
            j += 1
        i = j + 1
    return syllables


def _starts_with_vowel_sound(word: str) -> bool:
    w = word.lower()
    if not w:
        return False
    if w[0] == "h" and len(w) > 1:
        return _is_vowel(w[1])  # silent h — "la hora" still merges
    return _is_vowel(w[0])


def _ends_with_vowel_sound(word: str) -> bool:
    w = word.lower()
    return bool(w) and _is_vowel(w[-1])


def _count_line(line: str) -> int:
    words = _WORD_RE.findall(line)
    if not words:
        return 0
    total = sum(_count_word(w) for w in words)
    # Synalepha: each vowel-to-vowel word boundary merges two syllables
    # into one, so subtract one per junction.
    for prev, nxt in zip(words, words[1:]):
        if _ends_with_vowel_sound(prev) and _starts_with_vowel_sound(nxt):
            total -= 1
    return max(total, 0)


def count_spanish(text: str) -> GroundingResult | None:
    normalized = unicodedata.normalize("NFC", text)
    if not _WORD_RE.search(normalized):
        return None

    total = sum(_count_line(line) for line in normalized.splitlines() if line.strip())
    if total == 0:
        return None

    return GroundingResult(
        value=total,
        unit="syllables",
        language="Spanish",
        caveat=(
            "synalepha applied across word boundaries, as Spanish verse is "
            "counted; the agudo/esdrújulo line-ending adjustment is NOT "
            "applied, so this is a count of syllables present rather than a "
            "metrical verse length"
        ),
    )


register_counter("es", count_spanish)
