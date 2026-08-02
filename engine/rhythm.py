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


def _is_latin_script(text: str) -> bool:
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
    if not _is_latin_script(source_text):
        return None
    return count_syllables_text(source_text)
