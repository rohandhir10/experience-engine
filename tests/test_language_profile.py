"""Language Profile tests (docs/MULTILINGUAL_V2.md §7).

The central guarantee under test: the neutral profile renders every
prompt block as the empty string, so an unrecognized language behaves
exactly like the pre-V2 engine. tests/test_golden_prompts.py enforces the
same thing end to end at the prompt level.
"""
from __future__ import annotations

from engine.language_profile import (
    NEUTRAL_PROFILE,
    LanguageProfile,
    available_profiles,
    resolve_profile,
)


# ---------------------------------------------------------------------------
# The neutral default must be invisible
# ---------------------------------------------------------------------------


def test_neutral_profile_is_neutral():
    assert NEUTRAL_PROFILE.is_neutral


def test_neutral_profile_renders_every_block_empty():
    assert NEUTRAL_PROFILE.song_dna_block() == ""
    assert NEUTRAL_PROFILE.translator_block() == ""
    assert NEUTRAL_PROFILE.constitution_block() == ""
    assert NEUTRAL_PROFILE.anchor_block() == ""


def test_unknown_language_falls_back_to_neutral():
    assert resolve_profile("xx").is_neutral
    assert resolve_profile(None, "Klingon").is_neutral
    assert resolve_profile().is_neutral


def test_partial_profile_only_renders_what_it_has():
    partial = LanguageProfile(code="zz", name="Testish", emotional_baseline="quite flat")
    assert partial.song_dna_block() == ""
    assert partial.translator_block() == ""
    assert partial.anchor_block() == ""
    assert "quite flat" in partial.constitution_block()
    assert "Compression Floor" not in partial.constitution_block()


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def test_hindi_profile_is_available():
    assert "hi" in available_profiles()


def test_resolve_by_code():
    assert resolve_profile("hi").name == "Hindi"


def test_resolve_by_code_is_case_insensitive():
    assert resolve_profile("HI").name == "Hindi"


def test_resolve_by_free_text_language_name():
    # SongInput.source_language is free text like "Hindi/Punjabi (code-switched)"
    assert resolve_profile(None, "Hindi/Punjabi (code-switched)").code == "hi"


def test_code_takes_precedence_over_name():
    assert resolve_profile("hi", "something else entirely").code == "hi"


# ---------------------------------------------------------------------------
# The Hindi profile's content actually reaches the prompts
# ---------------------------------------------------------------------------


def test_hindi_profile_is_not_neutral():
    assert not resolve_profile("hi").is_neutral


def test_hindi_song_dna_block_calibrates_symbol_register():
    block = resolve_profile("hi").song_dna_block()
    assert "monsoon" in block or "rain" in block
    # The whole point of symbol calibration: judged within the tradition,
    # not against an English reader's sense of the exotic.
    assert "not to an English reader" in block


def test_hindi_translator_block_names_the_pronoun_trap():
    block = resolve_profile("hi").translator_block()
    assert "aap" in block and "tum" in block


def test_hindi_constitution_block_states_the_law_is_unchanged():
    block = resolve_profile("hi").constitution_block()
    assert "unchanged" in block
    assert "Compression Floor" in block and "Restraint Ceiling" in block


def test_hindi_anchor_block_carries_recognizability():
    block = resolve_profile("hi").anchor_block()
    assert "ishq" in block
    assert "currency in the target language" in block
    # The disposition rule from the constitution's title-word exception.
    assert "comprehensibility wins" in block


# ---------------------------------------------------------------------------
# Phase 2 languages
# ---------------------------------------------------------------------------


def test_phase_two_profiles_are_available():
    assert {"hi", "ko", "es"}.issubset(set(available_profiles()))


def test_korean_profile_names_the_speech_level_trap():
    block = resolve_profile("ko").translator_block()
    assert "해요체" in block or "speech level" in block.lower()


def test_korean_profile_calibrates_indirect_emotional_expression():
    block = resolve_profile("ko").constitution_block()
    assert "indirectly" in block or "image" in block


def test_korean_anchor_lexicon_includes_han_and_jeong():
    block = resolve_profile("ko").anchor_block()
    assert "한 (han)" in block and "정 (jeong)" in block


def test_spanish_profile_names_the_tu_usted_vos_trap():
    block = resolve_profile("es").translator_block()
    assert "usted" in block and "vos" in block


def test_spanish_profile_explains_assonant_rhyme_is_a_real_form():
    block = resolve_profile("es").song_dna_block()
    assert "ssonan" in block  # assonant / assonance


def test_spanish_and_korean_baselines_differ():
    """Law 4 is calibrated per tradition — a Spanish baseline that reads
    like the Korean one would mean the calibration is doing nothing.
    """
    es = resolve_profile("es").emotional_baseline
    ko = resolve_profile("ko").emotional_baseline
    assert es and ko and es != ko
    assert "direct" in es
    assert "indirect" in ko


def test_every_profile_selects_a_grounding_counter():
    from engine.grounding.base import supported_languages

    for code in available_profiles():
        profile = resolve_profile(code)
        assert profile.grounding_language_code in supported_languages(), code


def test_every_shipped_profile_has_required_fields():
    for code in available_profiles():
        profile = resolve_profile(code)
        assert profile.code and profile.name, code
        assert not profile.is_neutral, f"{code} profile is empty"
