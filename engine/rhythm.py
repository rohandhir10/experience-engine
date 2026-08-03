"""Deterministic syllable counting, replacing an LLM's unverified opinion
about "Singability & Rhythm" with an actual computed baseline the Judge
can reason from.

English (and Latin-transliterated source text) only, right now: uses the
CMU Pronouncing Dictionary via the `pronouncing` package for known words,
falling back to a vowel-cluster heuristic for anything out of dictionary
(slang, names, contractions, transliterated words). Devanagari and other
non-Latin scripts are not supported yet — source_syllable_estimate returns
None for those rather than fabricating a number nothing backs.
"""
from __future__ import annotations

import re

import pronouncing

# Any Unicode letters, with internal apostrophes (don't, l'amour) — NOT
# [A-Za-z], which silently split accented words ("café" -> "caf" + dropped
# tail) and miscounted their syllables.
_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")
_VOWEL_GROUPS_RE = re.compile(r"[aeiouyàáâäãèéêëìíîïòóôöõùúûü]+")


def is_latin_script(text: str) -> bool:
    """True for English or Latin-transliterated source text — false for
    Devanagari or other scripts this module can't count syllables for.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    latin = sum(1 for c in letters if c.isascii())
    return (latin / len(letters)) > 0.8


def _count_word_fallback(word: str) -> int:
    """Vowel-cluster heuristic for out-of-dictionary words."""
    word = word.lower()
    groups = _VOWEL_GROUPS_RE.findall(word)
    count = len(groups)
    if word.endswith("e") and not word.endswith("le") and count > 1:
        count -= 1  # silent trailing e
    return max(count, 1)


def count_syllables_word(word: str) -> int:
    phones_list = pronouncing.phones_for_word(word.lower())
    if phones_list:
        return pronouncing.syllable_count(phones_list[0])
    return _count_word_fallback(word)


def count_syllables_line(line: str) -> int:
    words = _WORD_RE.findall(line)
    return sum(count_syllables_word(w) for w in words if w)


def count_syllables_text(text: str) -> int:
    return sum(count_syllables_line(line) for line in text.splitlines() if line.strip())


def syllable_profile(text: str) -> list[dict]:
    """Per non-empty line: {"line": str, "syllables": int}."""
    profile = []
    for line in text.splitlines():
        if line.strip():
            profile.append({"line": line.strip(), "syllables": count_syllables_line(line)})
    return profile


# Marks a word absent from the CMU dictionary in a stress pattern string.
# Deliberately NOT '0' or '1': the vowel-cluster fallback used for syllable
# counting carries no stress information, and guessing would be exactly the
# silent-fabrication failure this codebase rejects elsewhere (see
# japanese.py degrading to None for kanji with no tokenizer, rather than
# under-counting). 'x' breaks any clash/lapse run a caller is scanning for
# rather than being silently skipped — missing information, not evidence
# of smooth prosody.
STRESS_UNKNOWN = "x"


def stress_pattern_word(word: str) -> str | None:
    """Per-syllable stress as a string of '1' (stressed, ARPAbet 1 or 2)
    and '0' (unstressed, ARPAbet 0), from the CMU dictionary's first
    pronunciation. None if the word isn't in the dictionary.
    """
    phones_list = pronouncing.phones_for_word(word.lower())
    if not phones_list:
        return None
    raw = pronouncing.stresses(phones_list[0])
    return "".join("0" if c == "0" else "1" for c in raw)


def stress_pattern_line(line: str) -> str:
    """Concatenates stress_pattern_word for every word in the line, using
    STRESS_UNKNOWN for any word not in the CMU dictionary.
    """
    words = _WORD_RE.findall(line)
    parts = []
    for word in words:
        pattern = stress_pattern_word(word)
        parts.append(pattern if pattern is not None else STRESS_UNKNOWN)
    return "".join(parts)


def source_syllable_estimate(source_text: str) -> int | None:
    """A rough source-side baseline — only meaningful when the source is
    Latin-script (transliterated, e.g. romanized Hindi/Punjabi). Returns
    None for Devanagari or other non-Latin-script source text rather than
    applying an English vowel heuristic to a script it has no bearing on.
    """
    if not is_latin_script(source_text):
        return None
    return count_syllables_text(source_text)


# --- Phrase-end sustainability: can a singer hold the last sound of a
# line, regardless of what language it's in? Two scripts are actually
# tractable without a full pronunciation dictionary:
#
# Latin script: a stop consonant (p/b/t/d/k/g) is a momentary release -
# physically impossible to sustain, full stop. Anything else (a vowel, a
# nasal, a liquid, even a fricative) can be held to some degree.
#
# Hangul: every Korean syllable block is algorithmically decomposable
# (initial+medial+final, straight from the Unicode codepoint), and
# Korean's coda neutralization - the 27 possible written final consonants
# collapsing to 7 surface sounds - is standard, textbook phonology, not a
# guess. That gives a real answer for whether a block's final sound is a
# sustained nasal/liquid/open-vowel or an unreleased stop.
#
# Devanagari (Hindi) is resolved via engine/g2p_hi.py's schwa-deletion
# heuristic - see that module for the algorithm and its disclosed limits.
# Perso-Arabic script (Urdu) is still NOT supported here: it needs real
# pronunciation data this module doesn't have (Urdu's script is a
# consonant-heavy abjad that often doesn't write short vowels at all,
# a harder problem than Hindi's schwa deletion, not a smaller version of
# it). None means exactly that for Urdu: no answer, not a guessed one.
_LATIN_STOP_CONSONANTS = frozenset("pbtdkg")

_HANGUL_BASE = 0xAC00
_HANGUL_LAST = 0xD7A3
_JONGSEONG_COUNT = 28

# Index into a Hangul block's final-consonant slot -> True if that slot's
# neutralized surface pronunciation is sustainable (open vowel, nasal, or
# liquid), False if it neutralizes to an unreleased stop. Order matches
# the standard jongseong table (0 = no final consonant).
_JONGSEONG_SUSTAINABLE = [
    True,  # 0: none (open vowel)
    False, False, False,  # 1-3: ㄱㄲㄳ -> k̚
    True, True, True,  # 4-6: ㄴㄵㄶ -> n
    False,  # 7: ㄷ -> t̚
    True,  # 8: ㄹ -> l
    False,  # 9: ㄺ -> k̚
    True,  # 10: ㄻ -> m
    True, True, True,  # 11-13: ㄼㄽㄾ -> l
    False,  # 14: ㄿ -> p̚
    True,  # 15: ㅀ -> l
    True,  # 16: ㅁ -> m
    False,  # 17: ㅂ -> p̚
    False,  # 18: ㅄ -> p̚
    False, False,  # 19-20: ㅅㅆ -> t̚
    True,  # 21: ㅇ -> ng
    False, False,  # 22-23: ㅈㅊ -> t̚
    False,  # 24: ㅋ -> k̚
    False,  # 25: ㅌ -> t̚
    False,  # 26: ㅍ -> p̚
    False,  # 27: ㅎ -> t̚ (in coda position, before a pause)
]


def _is_hangul_syllable(ch: str) -> bool:
    return _HANGUL_BASE <= ord(ch) <= _HANGUL_LAST


def phrase_end_sustainability(line: str) -> str | None:
    """"sustainable" or "closed" for the last word's final sound, or None
    if the script isn't one of the three this can actually answer for
    (see module comment above). Never guesses for Perso-Arabic (Urdu).
    """
    words = re.findall(r"\S+", line.strip())
    if not words:
        return None
    last_word = words[-1].strip(".,!?;:\"'()[]«»।")
    if not last_word:
        return None

    last_char = last_word[-1]
    if _is_hangul_syllable(last_char):
        jongseong = (ord(last_char) - _HANGUL_BASE) % _JONGSEONG_COUNT
        return "sustainable" if _JONGSEONG_SUSTAINABLE[jongseong] else "closed"

    if is_latin_script(last_word):
        return "closed" if last_char.lower() in _LATIN_STOP_CONSONANTS else "sustainable"

    from .g2p_hi import get_hindi_phonetic_coda

    hindi_coda = get_hindi_phonetic_coda(last_word)
    if hindi_coda is not None:
        return hindi_coda["coda_type"]

    return None
