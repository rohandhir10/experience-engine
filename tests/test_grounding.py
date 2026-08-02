"""Per-language source grounding tests, with hand-verified counts.

Every expected number here was worked out by hand from the writing
system's rules, not read off the implementation — a test that just
records whatever the code currently returns proves nothing.
"""
from __future__ import annotations

import pytest

from engine.grounding import count_source_units
from engine.grounding.base import supported_languages
from engine.grounding.devanagari import count_hindi
from engine.grounding.hangul import count_korean
from engine.grounding.japanese import count_japanese, count_morae_in_kana
from engine.grounding.spanish import _count_line, _count_word, count_spanish


# ---------------------------------------------------------------------------
# Korean — Hangul blocks are syllables by construction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("한국어", 3),  # han-gu-geo
        ("사랑", 2),  # sa-rang
        ("안녕하세요", 5),  # an-nyeong-ha-se-yo
        ("너를 사랑해", 5),  # neo-reul sa-rang-hae, spaces don't count
    ],
)
def test_korean_block_counts(text: str, expected: int):
    result = count_korean(text)
    assert result is not None
    assert result.value == expected
    assert result.unit == "syllables"


def test_korean_composes_separated_jamo():
    # ㅎ + ㅏ + ㄴ written separately still forms one block after NFC.
    composed = count_korean("한")
    decomposed = count_korean("한")
    assert composed is not None and decomposed is not None
    assert composed.value == decomposed.value == 1


def test_korean_counts_mixed_latin_words_too():
    # K-pop lyrics routinely mix English; dropping it undercounts the line.
    result = count_korean("사랑 baby")
    assert result is not None
    assert result.value == 4  # sa-rang (2) + ba-by (2)
    assert result.caveat and "Latin" in result.caveat


def test_korean_returns_none_for_non_korean():
    assert count_korean("just english here") is None


# ---------------------------------------------------------------------------
# Hindi — Devanagari with schwa deletion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected,why",
    [
        ("कमल", 2, "ka-mal: word-final schwa deletes, not ka-ma-la"),
        ("दिल", 1, "dil: matra on द, final ल schwa deletes"),
        ("नाम", 1, "naam: matra, final schwa deletes"),
        ("आग", 1, "aag: independent vowel + final schwa deleted"),
        ("प्यार", 1, "pyaar: प्+य conjunct via virama, one nucleus"),
        ("सागर", 2, "saa-gar: final schwa deletes"),
        ("तुम", 1, "tum"),
        ("मैं", 1, "main: matra + anusvara adds no syllable"),
    ],
)
def test_hindi_word_counts(text: str, expected: int, why: str):
    result = count_hindi(text)
    assert result is not None, why
    assert result.value == expected, f"{text}: expected {expected} ({why})"


def test_hindi_monosyllable_keeps_its_schwa():
    # न is "na" — the final-schwa rule must not zero out a one-syllable word.
    result = count_hindi("न")
    assert result is not None
    assert result.value == 1


def test_hindi_counts_across_a_phrase():
    # तुम (1) + साथ (1) + हो (1)
    result = count_hindi("तुम साथ हो")
    assert result is not None
    assert result.value == 3


def test_hindi_result_is_honest_about_precision():
    result = count_hindi("कमल")
    assert result is not None
    assert result.caveat and "not fully regular" in result.caveat


def test_hindi_returns_none_for_latin_text():
    assert count_hindi("tum saath ho") is None


# ---------------------------------------------------------------------------
# Spanish — diphthong/hiatus rules plus synalepha
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word,expected,why",
    [
        ("aire", 2, "ai- is a diphthong (strong+weak)"),
        ("cielo", 2, "cie- is a diphthong (weak+strong)"),
        ("poeta", 3, "po-e-ta: two strong vowels are a hiatus"),
        ("día", 2, "accented weak í breaks the diphthong"),
        ("dia", 1, "unaccented, ia IS a diphthong — why the word takes an accent"),
        ("corazón", 3, "co-ra-zón"),
        ("baúl", 2, "ba-úl: accented weak ú breaks it"),
        ("casa", 2, "ca-sa"),
    ],
)
def test_spanish_word_counts(word: str, expected: int, why: str):
    assert _count_word(word) == expected, f"{word}: {why}"


@pytest.mark.parametrize(
    "line,expected,why",
    [
        ("mi alma", 2, "synalepha: mi+al merge, mial-ma"),
        ("una casa", 4, "no vowel junction, u-na ca-sa"),
        ("la hora", 2, "silent h does not block synalepha: lao-ra"),
        ("corazón mío", 5, "co-ra-zón mí-o, no junction"),
    ],
)
def test_spanish_synalepha_across_words(line: str, expected: int, why: str):
    assert _count_line(line) == expected, f"{line}: {why}"


def test_spanish_result_is_honest_about_the_verse_convention():
    result = count_spanish("mi alma")
    assert result is not None
    assert result.caveat and "agudo" in result.caveat


def test_spanish_returns_none_for_empty_input():
    assert count_spanish("   \n  ") is None


# ---------------------------------------------------------------------------
# Japanese — morae, not syllables
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected,why",
    [
        ("きょう", 2, "kyo-u: small ょ fuses with き, it is not its own mora"),
        ("とうきょう", 4, "to-u-kyo-u — 5 characters, 4 morae"),
        ("にっぽん", 4, "ni-p-po-n: っ (sokuon) IS a full mora"),
        ("らーめん", 4, "ra-a-me-n: ー (chōonpu) IS a full mora"),
        ("しゃしん", 3, "sha-shi-n"),
        ("さくら", 3, "sa-ku-ra"),
        ("ん", 1, "the moraic nasal alone is one mora"),
    ],
)
def test_japanese_mora_counts_from_kana(text: str, expected: int, why: str):
    assert count_morae_in_kana(text) == expected, f"{text}: {why}"


def test_japanese_counts_pure_kana_without_a_tokenizer():
    result = count_japanese("さくらがちる")
    assert result is not None
    assert result.value == 6
    assert result.unit == "morae"


def test_japanese_unit_is_labelled_morae_not_syllables():
    """A bare integer would invite comparing morae to English syllables as
    though they were the same quantity. They are not.
    """
    result = count_japanese("さくら")
    assert result is not None
    assert result.unit == "morae"
    assert "morae, not syllables" in (result.caveat or "")


@pytest.mark.parametrize(
    "text,expected,why",
    [
        ("東京", 4, "to-u-kyo-u via kanji reading"),
        ("桜が散る", 6, "sa-ku-ra-ga-chi-ru"),
        ("今日は雨が降る", 8, "kyo-u-wa-a-me-ga-fu-ru"),
    ],
)
def test_japanese_resolves_kanji_readings(text: str, expected: int, why: str):
    result = count_japanese(text)
    if result is None:
        pytest.skip("SudachiPy not installed — kanji readings unavailable")
    assert result.value == expected, f"{text}: {why}"


def test_japanese_declines_rather_than_undercounting_kanji():
    """Without a reader, a kanji-heavy line must return None. Counting
    only its kana would report roughly half the true value while looking
    exact — worse than no grounding.
    """
    import engine.grounding.japanese as ja

    ja._tokenizer.cache_clear()
    original = ja._tokenizer
    try:
        ja._tokenizer = lambda: None
        assert ja.count_japanese("今日は雨が降る") is None
        # Pure kana still works with no reader at all.
        assert ja.count_japanese("さくら") is not None
    finally:
        ja._tokenizer = original
        ja._tokenizer.cache_clear()


def test_japanese_returns_none_for_non_japanese():
    assert count_japanese("just english") is None
    assert count_japanese("   ") is None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_dispatches_by_language_code():
    assert count_source_units("한국어", "ko").value == 3
    assert count_source_units("कमल", "hi").value == 2


def test_registry_is_case_insensitive():
    assert count_source_units("한국어", "KO") is not None


def test_unknown_language_returns_none_rather_than_guessing():
    assert count_source_units("whatever", "xx") is None
    assert count_source_units("whatever", None) is None


def test_registered_languages_include_every_shipped_language():
    assert {"hi", "ko", "es", "ja"}.issubset(set(supported_languages()))


def test_counters_register_on_package_import_alone():
    """Importing engine.grounding must be enough to register every
    counter. Without the re-exports in __init__, count_source_units()
    silently returns None for everything — indistinguishable from
    "language unsupported", which is exactly how this bug hid once.
    """
    import subprocess
    import sys

    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from engine.grounding import count_source_units;"
            "r = count_source_units('कमल', 'hi');"
            "print(r.value if r else 'NONE')",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.stdout.strip() == "2", proc.stderr


def test_grounding_result_labels_its_unit_for_the_judge():
    result = count_source_units("한국어", "ko")
    rendered = result.for_prompt()
    assert "syllables" in rendered and "Korean" in rendered
