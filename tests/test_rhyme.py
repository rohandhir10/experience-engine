"""Pure-function tests for engine/rhyme.py — no LLM involved. Every
expected rhyming_part below was checked directly against the installed
`pronouncing`/CMU-dictionary data, not read off this module's own output.
"""
from __future__ import annotations

from engine.rhyme import end_rhyme_scheme, rhyme_density, rhyming_part_word


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
