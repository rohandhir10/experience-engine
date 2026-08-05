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
from engine.grounding.hangul import count_korean, sino_korean_syllables
from engine.grounding.japanese import count_japanese, count_morae_in_kana
from engine.grounding.spanish import _count_line, _count_word, count_spanish
from engine.grounding.urdu import count_urdu


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


@pytest.mark.parametrize(
    "number,expected,reading",
    [
        (0, 1, "영"),
        (5, 1, "오"),
        (10, 1, "십 — not 일십, the leading 1 is dropped"),
        (24, 3, "이십사"),
        (100, 1, "백"),
        (365, 5, "삼백육십오"),
        (2024, 5, "이천이십사"),
    ],
)
def test_sino_korean_number_readings(number: int, expected: int, reading: str):
    assert sino_korean_syllables(number) == expected, f"{number} = {reading}"


def test_korean_counts_digits_as_they_are_sung():
    """"24시간" is sung 이-십-사-시-간. Counting only the Hangul gave 2 —
    a silent undercount that still looked exact.
    """
    result = count_korean("24시간")
    assert result is not None
    assert result.value == 5
    assert result.caveat and "Sino-Korean" in result.caveat


def test_korean_digit_caveat_names_the_numeral_ambiguity():
    """Korean has two numeral systems and the counter word decides which.
    Sino-Korean is the common case in lyrics, but the result must say so
    rather than presenting one reading as the only one.
    """
    result = count_korean("24시간")
    assert result is not None
    assert "two numeral systems" in (result.caveat or "")


def test_korean_counts_hanja():
    # Each Hanja character is one Korean syllable when read aloud.
    result = count_korean("우리 愛")
    assert result is not None
    assert result.value == 3


def test_korean_ideophone_reduplication_counts_in_full():
    # 반짝반짝 is four blocks and four sung syllables — the doubling is
    # part of the rhythm, not decoration to be collapsed.
    result = count_korean("반짝반짝")
    assert result is not None
    assert result.value == 4


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
# Urdu — Perso-Arabic abjad; only fully-diacritized text is countable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word,expected,why",
    [
        ("بِسْمِ", 2, "bis-mi: kasra, then sukun closes the middle consonant, then kasra"),
        ("کِتابْ", 2, "ki-taab: kasra gives the first nucleus, bare ا gives the second, final sukun marks ب as vowelless"),
        ("قَوْل", 1, "qawl: fatha gives one nucleus, sukun closes the وْ glide, no second"),
    ],
)
def test_urdu_diacritized_word_counts(word: str, expected: int, why: str):
    result = count_urdu(word)
    assert result is not None, why
    assert result.value == expected, f"{word}: expected {expected} ({why})"
    assert result.unit == "syllables"


def test_urdu_declines_ordinary_undiacritized_text():
    """Real pasted Urdu lyrics almost never carry i'raab — the short
    vowels are genuinely not written, so there is nothing honest to
    count. This must return None, not a number that looks exact and
    is actually guessed.
    """
    assert count_urdu("کتاب اردو میں لکھا ہے") is None


def test_urdu_returns_none_for_non_urdu_text():
    assert count_urdu("just english here") is None
    assert count_urdu("   ") is None


def test_urdu_result_discloses_why_it_only_works_here():
    # Fully-marked throughout. The previous input here was "بِسْمِ اللّٰہِ",
    # which only counted because the old averaged-density gate was
    # lenient: the ا and the first ل of the اللہ ligature carry no written
    # vowel at all, so under the module's own premise it should decline -
    # and now does. The point of this test is the caveat text, so it uses
    # an input that is genuinely countable.
    result = count_urdu("بِسْمِ کِتَاب")
    assert result is not None
    assert result.caveat and "omits them entirely" in result.caveat


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
    assert {"hi", "ko", "es", "ja", "ur"}.issubset(set(supported_languages()))


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


# ---------------------------------------------------------------------------
# Urdu: two counting bugs found by hand-tracing fully-marked spellings.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word,expected,why",
    [
        ("کِتَاب", 2, "ki-tāb: fatha+alif is ONE long ā, not a short vowel plus a vowel"),
        ("سَلَام", 2, "sa-lām: same fatha+alif pairing"),
        ("دِین", 1, "dīn: kasra+ya is ONE long ī"),
        ("نُور", 1, "nūr: damma+waw is ONE long ū"),
    ],
)
def test_urdu_long_vowel_written_as_diacritic_plus_mater_is_one_nucleus(word, expected, why):
    """A short vowel immediately before its matching mater lectionis
    spells a single long vowel. Counting the diacritic and the letter as
    two nuclei over-counted every long vowel - in fully-marked text,
    which is precisely the text this counter exists to serve, since a
    diwan printed with full tashkil uses these spellings throughout.
    """
    result = count_urdu(word)
    assert result is not None, why
    assert result.value == expected, f"{word}: expected {expected} ({why})"


def test_urdu_bare_mater_without_a_diacritic_still_counts_once():
    """The counterpart spelling, which was already correct and must stay
    so: no fatha on the ت, the alif alone carries the ā."""
    result = count_urdu("کِتابْ")
    assert result is not None
    assert result.value == 2


def test_urdu_declines_when_any_single_word_is_unvocalized():
    """The gate used to average diacritic density across words, but the
    count is a SUM over words - so a line of mostly-marked words could
    clear the average while its unmarked words silently contributed only
    their long vowels. One unvocalizable word makes the whole number
    wrong, not merely approximate.
    """
    mostly_marked = " ".join(["کِتَابْ"] * 7 + ["بادشاہ"] * 3)
    assert count_urdu(mostly_marked) is None

    just_one_bare = " ".join(["کِتَابْ"] * 3 + ["بادشاہ"])
    assert count_urdu(just_one_bare) is None


def test_urdu_counts_a_fully_marked_multi_word_line():
    """The case it does serve: every word vocalized, so the sum is real."""
    result = count_urdu("کِتَاب سَلَام")
    assert result is not None
    assert result.value == 4


def test_urdu_word_determinacy_allows_a_final_bare_consonant():
    """A word-final consonant with no vowel closes the syllable and adds
    no nucleus - it is not an ambiguity and must not trigger a decline."""
    from engine.grounding.urdu import _word_is_determined

    assert _word_is_determined("کِتَاب")
    assert not _word_is_determined("بادشاہ")


# ---------------------------------------------------------------------------
# Devanagari: the same two bug classes found in the Urdu counter, checked
# for here after the fact. Hangul was audited too and was clean on both -
# it NFC-normalises, and it already counts Latin/digits/Hanja rather than
# dropping them, which is the discipline Devanagari was missing.
# ---------------------------------------------------------------------------


def test_hindi_nukta_counts_the_same_in_both_unicode_encodings():
    """क़ has two encodings: precomposed U+0958, or क + combining nukta.
    The consonant set was written with the decomposed spelling, so set()
    put the bare nukta mark in it and left U+0958 out - the same word
    then counted differently depending only on how it was encoded.
    """
    decomposed = "ब" + "क" + "़" + "ा"
    precomposed = "ब" + "क़" + "ा"
    a, b = count_hindi(decomposed), count_hindi(precomposed)
    assert a is not None and b is not None
    assert a.value == b.value == 2, "baqā is 2 syllables in either encoding"


def test_hindi_nukta_is_never_its_own_syllable():
    """The bare nukta was in the consonant set, so it could pick up an
    inherent schwa of its own."""
    from engine.grounding.devanagari import _NUKTA, _CONSONANTS

    assert _NUKTA not in _CONSONANTS


def test_hindi_counts_code_switched_english():
    """Hindi film lyrics code-switch constantly, and the Latin words were
    dropped in silence - 'तू meri baby doll' returned 1."""
    result = count_hindi("तू meri baby doll")
    assert result is not None
    assert result.value == 6, "tū me-ri ba-by doll"
    assert "Latin" in (result.caveat or "")


def test_hindi_declines_when_digits_are_present():
    """Hindi numerals are suppletive - एक दो तीन ... इक्कीस are separate
    words, unlike Sino-Korean's regular place-value system. There is no
    honest way to syllabify an arbitrary digit run, and dropping it
    silently would be an undercount that still looks exact.
    """
    assert count_hindi("दिल 24 घंटे") is None


def test_hindi_plain_devanagari_is_unchanged():
    for word, expected in [("कमल", 2), ("समझ", 2), ("अमर", 2), ("दिल", 1)]:
        result = count_hindi(word)
        assert result is not None and result.value == expected, word


# --- Hangul: audited for the same two classes, clean on both ---------------


def test_korean_counts_the_same_decomposed_or_precomposed():
    import unicodedata

    from engine.grounding.hangul import count_korean

    nfc = "공주"
    nfd = unicodedata.normalize("NFD", nfc)
    assert len(nfd) > len(nfc), "the test input must actually be decomposed"
    assert count_korean(nfc).value == count_korean(nfd).value == 2


def test_korean_does_not_silently_drop_latin_digits_or_hanja():
    from engine.grounding.hangul import count_korean

    result = count_korean("사랑 forever 24시간")
    assert result is not None
    # 사랑(2) + forever(3) + 이십사(3) + 시간(2)
    assert result.value == 10
    assert result.caveat and "Latin" in result.caveat
