"""End-to-end profile integration (docs/MULTILINGUAL_V2.md Phase 1).

Two guarantees under test:
  1. A song with no resolvable profile produces prompts byte-identical to
     the pre-V2 engine (the no-regression promise).
  2. A song that DOES resolve a profile actually gets that language's
     content in the right prompts — not just stored somewhere unused.
"""
from __future__ import annotations

from engine import prompts
from engine.language_profile import NEUTRAL_PROFILE, resolve_profile
from engine.models import RoomMemory, SectionInput, SongInput
from tests.test_golden_prompts import (
    FIXTURE_CANDIDATES,
    FIXTURE_DNA,
    FIXTURE_MEMORY,
    FIXTURE_SIGNALS,
    FIXTURE_SONG,
    _hash,
)

HINDI = resolve_profile("hi")
SOURCE = "मैंने दराज़ बंद रखी"


# ---------------------------------------------------------------------------
# 1. The neutral profile must be indistinguishable from passing nothing
# ---------------------------------------------------------------------------


def test_neutral_profile_matches_no_profile_everywhere():
    pairs = [
        (
            prompts.song_dna_prompt(FIXTURE_SONG),
            prompts.song_dna_prompt(FIXTURE_SONG, NEUTRAL_PROFILE),
        ),
        (
            prompts.generation_prompt_v1(
                "translator", SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY
            ),
            prompts.generation_prompt_v1(
                "translator",
                SOURCE,
                FIXTURE_DNA,
                "verse_1",
                FIXTURE_MEMORY,
                profile=NEUTRAL_PROFILE,
            ),
        ),
        (
            prompts.creative_adapter_prompt(
                SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY
            ),
            prompts.creative_adapter_prompt(
                SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY, profile=NEUTRAL_PROFILE
            ),
        ),
        (
            prompts.judge_triage_prompt(
                FIXTURE_CANDIDATES,
                FIXTURE_SIGNALS,
                SOURCE,
                FIXTURE_DNA,
                "verse_1",
                FIXTURE_MEMORY,
            ),
            prompts.judge_triage_prompt(
                FIXTURE_CANDIDATES,
                FIXTURE_SIGNALS,
                SOURCE,
                FIXTURE_DNA,
                "verse_1",
                FIXTURE_MEMORY,
                profile=NEUTRAL_PROFILE,
            ),
        ),
    ]
    for without, with_neutral in pairs:
        assert _hash(*without) == _hash(*with_neutral)


def test_song_with_unknown_language_resolves_neutral():
    song = SongInput(
        source_language="Some Unlisted Language",
        sections=[SectionInput(name="v1", source_text="x")],
    )
    assert resolve_profile(song.source_language_code, song.source_language).is_neutral


# ---------------------------------------------------------------------------
# 2. A real profile must actually reach the prompts
# ---------------------------------------------------------------------------


def test_hindi_profile_reaches_the_song_dna_prompt():
    _, user = prompts.song_dna_prompt(FIXTURE_SONG, HINDI)
    assert "ghazal" in user
    assert "Sanskritized" in user


def test_hindi_profile_reaches_the_translator_but_not_other_agents():
    _, _ = prompts.generation_prompt_v1(
        "translator", SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY, profile=HINDI
    )
    translator_system, _ = prompts.generation_prompt_v1(
        "translator", SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY, profile=HINDI
    )
    poet_system, _ = prompts.generation_prompt_v1(
        "poet", SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY, profile=HINDI
    )
    # Structural traps are the Translator's problem specifically.
    assert "aap" in translator_system
    assert "aap" not in poet_system


def test_hindi_profile_gives_the_creative_adapter_its_anchor_lexicon():
    system, _ = prompts.creative_adapter_prompt(
        SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY, profile=HINDI
    )
    assert "ishq" in system
    assert "comprehensibility wins" in system


def test_hindi_profile_calibrates_the_judge_without_changing_the_laws():
    system, _ = prompts.judge_triage_prompt(
        FIXTURE_CANDIDATES,
        FIXTURE_SIGNALS,
        SOURCE,
        FIXTURE_DNA,
        "verse_1",
        FIXTURE_MEMORY,
        profile=HINDI,
    )
    # Calibration present...
    assert "more emotionally direct than English pop convention" in system
    # ...and the actual law text still there, unmodified.
    assert "THE BURDEN OF CHANGE, made mechanical" in system
    assert "artistic_fidelity" in system and "singability_rhythm" in system


def test_both_judge_prompts_receive_calibration():
    for builder_args in (
        (
            FIXTURE_CANDIDATES,
            FIXTURE_SIGNALS,
            SOURCE,
            FIXTURE_DNA,
            "verse_1",
            FIXTURE_MEMORY,
        ),
    ):
        triage, _ = prompts.judge_triage_prompt(*builder_args, profile=HINDI)
        final, _ = prompts.judge_final_prompt(
            FIXTURE_CANDIDATES,
            [],
            FIXTURE_SIGNALS,
            SOURCE,
            FIXTURE_DNA,
            "verse_1",
            FIXTURE_MEMORY,
            profile=HINDI,
        )
        assert "Restraint Ceiling (Law 4)" in triage
        assert "Restraint Ceiling (Law 4)" in final


# ---------------------------------------------------------------------------
# 3. Source grounding is wired to the profile
# ---------------------------------------------------------------------------


def test_hindi_profile_selects_devanagari_grounding():
    from engine.grounding import count_source_units

    result = count_source_units("तुम साथ हो", HINDI.grounding_language_code)
    assert result is not None
    assert result.value == 3
    assert result.unit == "syllables"


def test_neutral_profile_grounds_nothing():
    from engine.grounding import count_source_units

    assert count_source_units("तुम साथ हो", NEUTRAL_PROFILE.grounding_language_code) is None
