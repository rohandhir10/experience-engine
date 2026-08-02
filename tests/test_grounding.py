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


def test_registered_languages_include_phase_one_set():
    assert {"hi", "ko"}.issubset(set(supported_languages()))


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
