"""Pure-function tests for engine/rhyme.py — no LLM involved. Every
expected rhyming_part below was checked directly against the installed
`pronouncing`/CMU-dictionary data, not read off this module's own output.
"""
from __future__ import annotations

from engine.rhyme import (
    end_rhyme_scheme,
    phoneme_distinct2,
    phoneme_repetition_similarity,
    rhyme_density,
    rhyming_part_word,
)


def test_rhyming_part_ignores_spelling_and_uses_pronunciation():
    # "though" (OW1) does NOT rhyme with "true"/"through"/"shoe" (UW1),
    # despite "through" and "though" looking alike on the page.
    assert rhyming_part_word("true") == "UW1"
    assert rhyming_part_word("shoe") == "UW1"
    assert rhyming_part_word("though") == "OW1"
    assert rhyming_part_word("true") != rhyming_part_word("though")


def test_rhyming_part_finds_rhymes_spelling_would_miss():
    # "fire" and "higher" rhyme (AY1 ER0 both) despite no shared spelling
    # after the first letter.
    assert rhyming_part_word("fire") == rhyming_part_word("higher")


def test_rhyming_part_returns_none_for_unknown_words():
    assert rhyming_part_word("xyzzyplorp") is None


def test_end_rhyme_scheme_labels_matching_endings_the_same_letter():
    lines = [
        "I wonder why it's true",
        "the sky is always blue",
        "nothing here is new",
        "the old and something though",
    ]
    # true/blue/new all end UW1 -> same label; "though" is OW1 -> different.
    scheme = end_rhyme_scheme(lines)
    assert scheme[0] == scheme[1] == scheme[2]
    assert scheme[3] != scheme[0]


def test_end_rhyme_scheme_is_none_for_unresolvable_words():
    scheme = end_rhyme_scheme(["this line ends in xyzzyplorp", "a normal line here"])
    assert scheme[0] is None
    assert scheme[1] is not None


def test_rhyme_density_counts_the_rhymed_fraction():
    # 3 of 4 end words rhyme (true/blue/new); "though" does not.
    lines = [
        "I wonder why it's true",
        "the sky is always blue",
        "nothing here is new",
        "the old and something though",
    ]
    assert rhyme_density(lines) == 0.75


def test_rhyme_density_is_none_with_fewer_than_two_resolvable_lines():
    assert rhyme_density(["only one line here"]) is None
    assert rhyme_density([]) is None


def test_rhyme_density_is_zero_when_nothing_rhymes():
    lines = ["ends in cat", "ends in dog", "ends in bird"]
    assert rhyme_density(lines) == 0.0


# ---------------------------------------------------------------------------
# Phoneme repetition similarity — adapted from Kim et al. 2023 (ISMIR),
# see engine/rhyme.py's module comment for exactly what's being compared.
# ---------------------------------------------------------------------------


def test_phoneme_distinct2_is_low_for_a_highly_repetitive_line():
    assert phoneme_distinct2("la la la la la la") == 0.25


def test_phoneme_distinct2_is_high_for_a_varied_line():
    varied = phoneme_distinct2("the quick brown fox jumps over the lazy dog")
    assert varied > 0.9


def test_phoneme_distinct2_is_none_below_the_minimum_phoneme_count():
    assert phoneme_distinct2("hi") is None
    assert phoneme_distinct2("") is None


def test_phoneme_repetition_similarity_is_positive_when_anchor_and_final_track_together():
    repetitive = "la la la la la la"
    varied = "the quick brown fox jumps over the lazy dog"
    pairs = [
        (repetitive, repetitive),
        (varied, varied),
        (repetitive, repetitive),
        (varied, varied),
    ]
    assert phoneme_repetition_similarity(pairs) == 1.0


def test_phoneme_repetition_similarity_is_negative_when_they_diverge():
    """The failure this metric exists to catch: the shipped rendering's
    repetition pattern runs opposite the literal anchor's — a repetitive
    anchor section rendered as varied, and vice versa."""
    repetitive = "la la la la la la"
    varied = "the quick brown fox jumps over the lazy dog"
    pairs = [
        (repetitive, varied),
        (varied, repetitive),
        (repetitive, varied),
        (varied, repetitive),
    ]
    assert phoneme_repetition_similarity(pairs) == -1.0


def test_phoneme_repetition_similarity_is_none_with_too_few_sections():
    repetitive = "la la la la la la"
    varied = "the quick brown fox jumps over the lazy dog"
    assert phoneme_repetition_similarity([(repetitive, repetitive), (varied, varied)]) is None
    assert phoneme_repetition_similarity([]) is None
