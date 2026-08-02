"""Deterministic end-rhyme measurement for shipped English lines, using
the same CMU-dictionary-backed `pronouncing` library already in use for
syllable counting (engine/rhythm.py). `rhyming_part()` exposes the part
of a word's pronunciation that actually has to match for a rhyme, which
is the right unit to compare — orthography is not: "though" and "through"
don't rhyme (OW1 vs UW1); "fire" and "higher" do (AY1 ER0 both), despite
neither spelling pair suggesting the opposite of what's true.

This module MEASURES. It does not judge. Whether a given rhyme_density is
"enough" varies by language and genre: Hindi film-song couplets expect
dense end rhyme, while traditional Japanese verse does not rhyme at all
by convention (engine/profiles/japanese.json's rhyme_convention says so
explicitly — Japanese phonology makes rhyme nearly automatic and
therefore uninformative). A single hardcoded threshold across every
language/genre would misfire constantly on exactly the cases the profiles
already document. Calibrating an expectation per genre is future work,
gated on real corpus data existing to calibrate it — not something to
guess at here.
"""
from __future__ import annotations

import re

import pronouncing

_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")


def rhyming_part_word(word: str) -> str | None:
    """The ARPAbet suffix from the last stressed vowel onward — the part
    that has to match for two words to rhyme. None if the word isn't in
    the CMU dictionary (never guessed from spelling).
    """
    phones_list = pronouncing.phones_for_word(word.lower())
    if not phones_list:
        return None
    return pronouncing.rhyming_part(phones_list[0])


def _line_end_word(line: str) -> str | None:
    words = _WORD_RE.findall(line)
    return words[-1] if words else None


def end_rhyme_scheme(lines: list[str]) -> list[str | None]:
    """One label per line: lines whose end words share a rhyming part get
    the same letter (A, B, C, ...), assigned in order of first appearance
    — the conventional ABAB/AABB notation. None for a line whose end word
    isn't in the CMU dictionary, reported as unresolved rather than
    guessed.
    """
    end_words = [_line_end_word(line) for line in lines]
    parts = [rhyming_part_word(w) if w else None for w in end_words]

    labels: dict[str, str] = {}
    result: list[str | None] = []
    next_label = ord("A")
    for part in parts:
        if part is None:
            result.append(None)
            continue
        if part not in labels:
            labels[part] = chr(next_label)
            next_label += 1
        result.append(labels[part])
    return result


def rhyme_density(lines: list[str]) -> float | None:
    """Fraction of resolvable end words that rhyme with at least one
    other end word in the same set of lines. None when fewer than 2 end
    words are resolvable (density is undefined here, not zero — reporting
    0.0 would claim "measured no rhyme" when the truth is "couldn't
    measure enough of it").
    """
    scheme = end_rhyme_scheme(lines)
    resolvable = [label for label in scheme if label is not None]
    if len(resolvable) < 2:
        return None
    counts: dict[str, int] = {}
    for label in resolvable:
        counts[label] = counts.get(label, 0) + 1
    rhymed = sum(1 for label in resolvable if counts[label] > 1)
    return rhymed / len(resolvable)
