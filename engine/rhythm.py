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

_WORD_RE = re.compile(r"[A-Za-z']+")
_VOWEL_GROUPS_RE = re.compile(r"[aeiouy]+")


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


def source_syllable_estimate(source_text: str) -> int | None:
    """A rough source-side baseline — only meaningful when the source is
    Latin-script (transliterated, e.g. romanized Hindi/Punjabi). Returns
    None for Devanagari or other non-Latin-script source text rather than
    applying an English vowel heuristic to a script it has no bearing on.
    """
    if not _is_latin_script(source_text):
        return None
    return count_syllables_text(source_text)
