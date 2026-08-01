"""Pure-function tests for engine/rhythm.py — no LLM involved at all. This
replaces "the Judge just says a rhythm number" with an actual deterministic
baseline; these tests prove the baseline itself is computed correctly
before it's ever handed to a model.
"""
from __future__ import annotations

from engine.rhythm import (
    count_syllables_line,
    count_syllables_word,
    source_syllable_estimate,
    syllable_profile,
)


def test_known_words_use_the_pronunciation_dictionary():
    assert count_syllables_word("hello") == 2
    assert count_syllables_word("wonderful") == 3
    assert count_syllables_word("cat") == 1


def test_unknown_words_fall_back_to_the_vowel_heuristic():
    # Not in CMUdict, but the fallback should still produce a plausible count.
    assert count_syllables_word("zzyxq") >= 1  # never returns 0
    assert count_syllables_word("aitthe") >= 1


def test_count_syllables_line_sums_across_words():
    assert count_syllables_line("I keep the drawer locked") == (
        count_syllables_word("I")
        + count_syllables_word("keep")
        + count_syllables_word("the")
        + count_syllables_word("drawer")
        + count_syllables_word("locked")
    )


def test_syllable_profile_returns_one_entry_per_non_empty_line():
    text = "line one here\n\nline two also here"
    profile = syllable_profile(text)
    assert len(profile) == 2
    assert profile[0]["line"] == "line one here"
    assert profile[0]["syllables"] > 0


def test_source_syllable_estimate_works_on_latin_transliteration():
    # Romanized Punjabi — Latin script, should get a real count.
    estimate = source_syllable_estimate("Sadda haq, aitthe rakh")
    assert isinstance(estimate, int)
    assert estimate > 0


def test_source_syllable_estimate_returns_none_for_devanagari():
    # Non-Latin script (a generic test phrase, not song lyrics) — must not
    # fabricate a number for a script this module has no bearing on.
    estimate = source_syllable_estimate("यह एक परीक्षण वाक्य है")
    assert estimate is None
