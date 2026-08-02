"""Pure-function tests for engine/rhythm.py — no LLM involved at all. This
replaces "the Judge just says a rhythm number" with an actual deterministic
baseline; these tests prove the baseline itself is computed correctly
before it's ever handed to a model.
"""
from __future__ import annotations

from engine.rhythm import (
    STRESS_UNKNOWN,
    count_syllables_line,
    count_syllables_word,
    source_syllable_estimate,
    stress_pattern_line,
    stress_pattern_word,
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


# ---------------------------------------------------------------------------
# Stress patterns — hand-verified against the CMU dictionary directly
# ---------------------------------------------------------------------------


def test_stress_pattern_word_matches_the_cmu_dictionary():
    # B Y UW1 T AH0 F AH0 L -> stressed, unstressed, unstressed, unstressed
    assert stress_pattern_word("beautiful") == "100"
    # K AH0 N V ER1 S IH0 NG -> unstressed, stressed, unstressed
    assert stress_pattern_word("conversing") == "010"
    assert stress_pattern_word("love") == "1"
    assert stress_pattern_word("the") == "0"


def test_stress_pattern_word_returns_none_for_unknown_words():
    assert stress_pattern_word("xyzzyplorp") is None


def test_stress_pattern_line_concatenates_and_marks_unknown_words():
    # I(1) love(1) the(0) sea(1)
    assert stress_pattern_line("I love the sea") == "1101"
    # A word CMUdict has never heard of breaks the pattern with 'x'
    # rather than being silently dropped or guessed.
    pattern = stress_pattern_line("I love xyzzyplorp")
    assert pattern == f"11{STRESS_UNKNOWN}"
