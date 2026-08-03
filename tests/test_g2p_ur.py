"""Tests for engine/g2p_ur.py's Urdu phrase-end coda heuristic.

The load-bearing case here isn't "does it read the last letter right" -
it's "does it correctly REFUSE to answer when the last letter alone
can't settle the question." Urdu's izafat construction (an unwritten
"-e-" vowel joining two nouns/adjectives — dast-e-tanha, kitab-e-
zindagi) can turn a word that looks stop-consonant-final into one that
is actually sung open, and real text almost never marks the diacritic
that would disambiguate it. Every "closed" assertion below is backed by
an explicit sukun ruling out that hidden vowel; every undiacritized
stop-final word is checked to decline (None), not guess.
"""
from __future__ import annotations

from engine.g2p_ur import URDU_CLOSED_STOPS, URDU_SUSTAINABLE_ENDINGS, get_urdu_phrase_end_coda


def test_unambiguous_long_vowel_ending_is_sustainable():
    """کیا "kya" (what): ends on ا, an unambiguous long vowel - no
    diacritic needed, an unwritten trailing vowel isn't a real
    possibility after an already-vowel-final word."""
    result = get_urdu_phrase_end_coda("کیا")
    assert result == {"coda_type": "sustainable", "final_character": "ا"}


def test_bari_ye_ending_is_sustainable():
    result = get_urdu_phrase_end_coda("پیارے")  # pyaare - ends ے
    assert result == {"coda_type": "sustainable", "final_character": "ے"}


def test_liquid_consonant_ending_is_sustainable_without_a_diacritic():
    """دل "dil" (heart) ends on ل, a liquid, not a stop - both possible
    readings (bare-consonant-final, or vowel-final via an unwritten
    izafat ending) are "sustainable", so this is safe to answer even
    without a diacritic."""
    result = get_urdu_phrase_end_coda("دل")
    assert result == {"coda_type": "sustainable", "final_character": "ل"}


def test_nasal_letter_ending_is_sustainable_without_a_diacritic():
    result = get_urdu_phrase_end_coda("مکان")  # makaan, house - ends ن
    assert result == {"coda_type": "sustainable", "final_character": "ن"}


def test_bare_stop_consonant_declines_rather_than_guessing():
    """کتاب "kitab" (book) ends on ب, a stop, with no diacritic. In
    isolation it's pronounced with a bare final "b" (closed) - but the
    exact same spelling heads real izafat constructions (kitab-e-
    zindagi, "book of life") where it is sung open. The bare script
    can't tell these apart, so this must return None."""
    assert get_urdu_phrase_end_coda("کتاب") is None


def test_bare_stop_consonant_declines_for_every_word_in_the_closed_set():
    for stop in URDU_CLOSED_STOPS:
        word = f"اب{stop}"  # any vowel-led filler + the stop, undiacritized
        result = get_urdu_phrase_end_coda(word)
        assert result is None, f"{stop} should decline without a diacritic"


def test_sukun_disambiguates_a_stop_consonant_as_closed():
    """کِتابْ - the same word, but fully voweled: an explicit sukun on
    the final ب rules out any unwritten trailing vowel, so the ambiguity
    that made the undiacritized form decline is gone."""
    result = get_urdu_phrase_end_coda("کِتابْ")
    assert result == {"coda_type": "closed", "final_character": "ب"}


def test_sukun_on_a_non_stop_letter_is_sustainable():
    result = get_urdu_phrase_end_coda("دَرْ")  # dar - ر with sukun, a liquid
    assert result == {"coda_type": "sustainable", "final_character": "ر"}


def test_short_vowel_diacritic_is_unambiguously_sustainable():
    result = get_urdu_phrase_end_coda("کِ")  # bare consonant + kasra
    assert result == {"coda_type": "sustainable", "final_character": "ِ"}


def test_tanwin_is_unambiguously_sustainable():
    result = get_urdu_phrase_end_coda("خیراً")  # khairan - fatḥatan/tanwin ending
    assert result is not None
    assert result["coda_type"] == "sustainable"


def test_shadda_with_nothing_after_it_declines():
    result = get_urdu_phrase_end_coda("مکّ")  # gemination marker with no vowel after it
    assert result is None


def test_gol_he_ending_is_sustainable():
    """بچہ "bachcha" (child): ہ here marks a vowel, not a consonant "h" -
    included in URDU_SUSTAINABLE_ENDINGS for exactly this reason."""
    result = get_urdu_phrase_end_coda("بچہ")
    assert result == {"coda_type": "sustainable", "final_character": "ہ"}


def test_noon_ghunna_ending_is_sustainable():
    result = get_urdu_phrase_end_coda("میں")  # main/mein - ends ں, nasalization
    assert result == {"coda_type": "sustainable", "final_character": "ں"}


def test_endings_lists_do_not_overlap():
    assert not (URDU_CLOSED_STOPS & URDU_SUSTAINABLE_ENDINGS)


def test_non_urdu_input_returns_none():
    assert get_urdu_phrase_end_coda("hello") is None
    assert get_urdu_phrase_end_coda("こんにちは") is None


def test_empty_input_returns_none():
    assert get_urdu_phrase_end_coda("") is None
    assert get_urdu_phrase_end_coda("   ") is None


def test_strips_surrounding_punctuation():
    result = get_urdu_phrase_end_coda("دل۔")  # trailing Urdu full stop
    assert result == {"coda_type": "sustainable", "final_character": "ل"}
