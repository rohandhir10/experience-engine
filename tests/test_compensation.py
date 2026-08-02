"""Compensation: carrying what the source encodes and English cannot.

The gap this closes: profiles could *name* untranslatable features
(Japanese 僕/俺, Korean speech levels, Hindi tu/tum/aap), the Translator
was told to flag them — and then the observation went into free-text
leans_into where nothing downstream used it. Detected, then discarded.
"""
from __future__ import annotations

from engine import prompts
from engine.language_profile import NEUTRAL_PROFILE, resolve_profile
from engine.models import Compensation, RoomMemory
from engine.verify import verify_result
from tests.test_golden_prompts import FIXTURE_DNA, FIXTURE_MEMORY
from tests.test_verify import _adapted_section, _laws

JAPANESE = resolve_profile("ja")
SOURCE = "桜が散る"

ORE = Compensation(
    source_feature="first-person pronoun 俺 (ore)",
    what_it_encodes="blunt, assertive, masculine self-presentation",
    english_carrier="short Anglo-Saxon diction, contractions, no hedging",
)


# ---------------------------------------------------------------------------
# The Translator is asked for these only where they exist
# ---------------------------------------------------------------------------


def test_translator_is_asked_for_compensations_when_traps_exist():
    system, _ = prompts.generation_prompt_v1(
        "translator", SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY, profile=JAPANESE
    )
    assert "compensations" in system
    assert "english_carrier" in system


def test_neutral_profile_never_asks_for_compensations():
    """No declared traps means nothing to compensate for — and the Phase 1
    guarantee that neutral prompts stay byte-identical still holds.
    """
    system, _ = prompts.generation_prompt_v1(
        "translator", SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY,
        profile=NEUTRAL_PROFILE,
    )
    assert "compensations" not in system


def test_only_the_translator_is_asked():
    system, _ = prompts.generation_prompt_v1(
        "poet", SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY, profile=JAPANESE
    )
    assert "compensations" not in system


def test_the_instruction_forbids_bolting_on_words():
    """The failure mode this must not become: adding an adjective to
    'convey bluntness'. That is invention, and the Restraint Ceiling would
    rightly flag it. The carrier has to be register, not additions.
    """
    system, _ = prompts.generation_prompt_v1(
        "translator", SOURCE, FIXTURE_DNA, "verse_1", FIXTURE_MEMORY, profile=JAPANESE
    )
    assert "never extra words bolted on" in system
    assert "invention, not" in system


# ---------------------------------------------------------------------------
# Once decided, it travels and binds
# ---------------------------------------------------------------------------


def test_room_memory_carries_compensations_to_later_sections():
    memory = RoomMemory(compensations=[ORE])
    summary = memory.summary_for_prompt()
    assert "俺 (ore)" in summary
    assert "short Anglo-Saxon diction" in summary
    assert "binding" in summary


def test_compensations_reach_the_first_section_too():
    """They are decided in section one, so the memory summary must show
    them even when no prior ruling exists yet.
    """
    memory = RoomMemory(compensations=[ORE])
    assert "No prior sections yet" in memory.summary_for_prompt()
    assert "俺 (ore)" in memory.summary_for_prompt()


def test_uncarried_features_are_recorded_as_losses_not_hidden():
    """Script choice (kanji vs hiragana vs katakana) is close to genuinely
    unreproducible. Recording the loss beats pretending it was carried.
    """
    memory = RoomMemory(
        compensations=[
            Compensation(
                source_feature="hiragana where kanji is expected",
                what_it_encodes="softening, childlike or intimate tone",
                english_carrier="no reliable English channel",
                carried=False,
            )
        ]
    )
    summary = memory.summary_for_prompt()
    assert "accepted loss" in summary


def test_memory_without_compensations_is_unchanged():
    assert "binding" not in RoomMemory().summary_for_prompt()


# ---------------------------------------------------------------------------
# The verifier enforces it
# ---------------------------------------------------------------------------


def _section_with(compensation: Compensation, name: str):
    section = _adapted_section(name)
    section.compensations = [compensation]
    return section


def test_switching_carrier_mid_song_is_an_error():
    hedging = ORE.model_copy(update={"english_carrier": "soft, hedging, tentative"})
    report = verify_result(
        {
            "sections": [
                _section_with(ORE, "verse_1").model_dump(),
                _section_with(hedging, "chorus").model_dump(),
            ]
        }
    )
    assert not report.passed
    assert "Compensation consistency" in _laws(report.cross_section_findings)


def test_consistent_carrier_passes():
    report = verify_result(
        {
            "sections": [
                _section_with(ORE, "verse_1").model_dump(),
                _section_with(ORE, "chorus").model_dump(),
            ]
        }
    )
    assert report.passed
