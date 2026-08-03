"""Tests for engine/g2p_hi.py's Hindi schwa-deletion heuristic.

Every word here is a well-known, real Hindi word whose correct
pronunciation isn't in dispute - these aren't invented test fixtures,
they're independent checks that the algorithm (terminal deletion +
alternating medial deletion by position-from-the-end + word-initial
protection) actually reproduces known-correct results, not just
internally-consistent ones.
"""
from __future__ import annotations

import unicodedata

from engine.g2p_hi import get_hindi_phonetic_coda, is_devanagari


def test_is_devanagari_detects_the_script():
    assert is_devanagari("कमल") is True
    assert is_devanagari("kamal") is False
    assert is_devanagari("") is False


def test_terminal_deletion_on_a_three_consonant_word():
    """कमल "kamal" (lotus): only the final schwa deletes - क and म both
    keep theirs. 2 syllables (ka-mal), ends on ल, a liquid: sustainable."""
    result = get_hindi_phonetic_coda("कमल")
    assert result == {"coda_type": "sustainable", "final_sound": "ल", "syllable_count": 2}


def test_medial_deletion_on_a_four_consonant_word():
    """करवट "karvaṭ" (turning side): र (position 3 from the end, odd)
    deletes; व (position 2, even) is retained. 2 syllables (kar-vaṭ),
    ends on ट, a retroflex stop: closed."""
    result = get_hindi_phonetic_coda("करवट")
    assert result == {"coda_type": "closed", "final_sound": "ट", "syllable_count": 2}


def test_word_initial_protection():
    """नमक "namak" (salt): न is word-initial, so it keeps its schwa even
    though a naive parity rule alone would delete it. म (even position)
    also retained. Only क (terminal) deletes."""
    result = get_hindi_phonetic_coda("नमक")
    assert result == {"coda_type": "closed", "final_sound": "क", "syllable_count": 2}


def test_short_two_unit_word():
    """एक "ek" (one): ए is a vowel-only akshara, क is terminal and
    deletes - single syllable, ends on क, a stop: closed."""
    result = get_hindi_phonetic_coda("एक")
    assert result == {"coda_type": "closed", "final_sound": "क", "syllable_count": 1}


def test_explicit_final_vowel_is_never_deleted():
    """कमला "Kamala" (a name): ends on an explicit vowel sign (ा), not an
    inherent schwa - terminal deletion doesn't apply at all, and the word
    keeps its open ending, exactly as follow-on words like कमला (vs.
    कमल) are supposed to behave."""
    result = get_hindi_phonetic_coda("कमला")
    assert result == {"coda_type": "sustainable", "final_sound": "vowel", "syllable_count": 3}


def test_nasal_final_consonant_is_sustainable():
    result = get_hindi_phonetic_coda("राम")  # Ram - ends on म, a nasal
    assert result["coda_type"] == "sustainable"
    assert result["final_sound"] == "म"


def test_liquid_final_consonant_is_sustainable():
    result = get_hindi_phonetic_coda("दिल")  # dil, heart - ends on ल
    assert result["coda_type"] == "sustainable"
    assert result["final_sound"] == "ल"


def test_conjunct_cluster_is_treated_as_one_unit():
    """विद्या "vidyā" (knowledge): द्य is a virama-joined conjunct - it
    must not be split into two independent deletion candidates. Ends on
    an explicit vowel: sustainable."""
    result = get_hindi_phonetic_coda("विद्या")
    assert result["coda_type"] == "sustainable"
    assert result["final_sound"] == "vowel"


def test_nukta_consonant_is_classified_correctly():
    """इश्क़ "ishq" (love/passion): the nukta consonant क़ is a stop
    (uvular), so this closes off - matches the word's real, single-
    syllable pronunciation ending in a hard consonant cluster."""
    result = get_hindi_phonetic_coda("इश्क़")
    assert result == {"coda_type": "closed", "final_sound": "क़", "syllable_count": 1}


def test_nukta_consonant_survives_nfd_decomposed_input():
    """The 8 nukta consonants are on Unicode's composition-exclusion list
    - real-world text can spell क़ as base+combining-nukta (NFD) instead
    of the precomposed codepoint. Both must resolve identically."""
    decomposed = unicodedata.normalize("NFD", "इश्क़")
    composed = unicodedata.normalize("NFC", "इश्क़")
    assert get_hindi_phonetic_coda(decomposed) == get_hindi_phonetic_coda(composed)


def test_non_devanagari_input_returns_none():
    assert get_hindi_phonetic_coda("hello") is None
    assert get_hindi_phonetic_coda("こんにちは") is None


def test_empty_input_returns_none():
    assert get_hindi_phonetic_coda("") is None
    assert get_hindi_phonetic_coda("   ") is None
