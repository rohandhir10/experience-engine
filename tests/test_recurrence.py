"""Tests for source-side formal-recurrence detection. Every expected value
here is worked out by hand from the words involved, not read off the
implementation (same convention as test_grounding.py).
"""
from __future__ import annotations

from engine.recurrence import detect_recurring_endings


def test_finds_the_longest_shared_ending_across_three_sections():
    # Hand-worked: full last lines differ, but the trailing 3 words
    # ("what is true") are identical in all three, while the trailing 4th
    # word back ("now"/"me"/"me") is not shared by all three — so the
    # longest valid match is exactly 3 words, not 4.
    sections = [
        ("a", "Verse one line\nTell me now what is true"),
        ("b", "Verse two\nJust tell me what is true"),
        ("c", "Bridge\nSo tell me what is true"),
    ]
    result = detect_recurring_endings(sections)
    assert len(result) == 1
    assert result[0].shared_suffix == "what is true"
    assert set(result[0].sections) == {"a", "b", "c"}


def test_radif_style_recurrence_in_devanagari():
    # Mirrors the real Ghalib ghazal case: every couplet's second line
    # ends on the same two-word radif, "क्या है" (kya hai, "what is").
    sections = [
        ("sher_1", "हर एक बात पे कहते हो तुम कि तू\nतुम्हीं कहो कि ये अंदाज़-ए-गुफ़्तुगू क्या है"),
        ("sher_2", "न शो'ले में ये करिश्मा न बर्क़ में ये अदा\nकोई बताओ कि वो शोख़-ए-तुंद-ख़ू क्या है"),
        ("sher_3", "ये रश्क है कि वो होता है हम-सुख़न तुम से\nवगर्ना ख़ौफ़-ए-बद-आमोज़ी-ए-अदू क्या है"),
    ]
    result = detect_recurring_endings(sections)
    assert len(result) == 1
    assert result[0].shared_suffix == "क्या है"
    assert set(result[0].sections) == {"sher_1", "sher_2", "sher_3"}


def test_no_shared_ending_returns_nothing():
    sections = [
        ("a", "hello there\nthe sky is blue today"),
        ("b", "greetings\nthe grass is green now"),
        ("c", "hi\nwater tastes like nothing"),
    ]
    assert detect_recurring_endings(sections) == []


def test_below_minimum_section_count_is_not_a_recurrence():
    # Only two of three sections share "what is true" — a coincidence
    # between two sections is common and must not fire on its own.
    sections = [
        ("a", "x\nwhat is true"),
        ("b", "y\nwhat is true"),
        ("c", "z\nnothing at all"),
    ]
    assert detect_recurring_endings(sections) == []


def test_single_shared_word_is_below_the_suffix_floor():
    # All three end on "true", but no two of them share a second word
    # before it ("is"/"was"/"felt" all differ) — a bare shared final word
    # is exactly the kind of function-word-tail false positive the
    # MIN_SUFFIX_WORDS floor exists to reject.
    sections = [
        ("a", "x\nthis is true"),
        ("b", "y\nthat was true"),
        ("c", "z\nit felt true"),
    ]
    assert detect_recurring_endings(sections) == []


def test_fewer_than_three_sections_total_cannot_recur():
    sections = [
        ("a", "x\nwhat is true"),
        ("b", "y\nwhat is true"),
    ]
    assert detect_recurring_endings(sections) == []


def test_ignores_blank_lines_and_uses_the_last_non_empty_line():
    sections = [
        ("a", "what is true\n\n"),
        ("b", "something else\nwhat is true\n"),
        ("c", "another line\nwhat is true"),
    ]
    result = detect_recurring_endings(sections)
    assert len(result) == 1
    assert result[0].shared_suffix == "what is true"
