"""Regression tests for the pre-freeze architectural fixes: input
validation, per-voice threading, phrase-level motif memory, and the
ruling-validation retry. All fake-client, no network.
"""
from __future__ import annotations

import pytest

from engine.models import JudgeRuling, RoomMemory, SectionInput, SongInput
from engine.rhythm import count_syllables_line, count_syllables_word


# ---------------------------------------------------------------------------
# Input validation (section names are load-bearing)
# ---------------------------------------------------------------------------


def test_duplicate_section_names_rejected():
    with pytest.raises(ValueError, match="Duplicate section name"):
        SongInput(
            source_language="Hindi",
            sections=[
                SectionInput(name="chorus", source_text="a"),
                SectionInput(name="chorus", source_text="b"),
            ],
        )


def test_repeats_must_reference_an_earlier_section():
    with pytest.raises(ValueError, match="EARLIER section"):
        SongInput(
            source_language="Hindi",
            sections=[
                SectionInput(name="chorus_2", source_text="x", repeats="chorus"),
                SectionInput(name="chorus", source_text="x"),
            ],
        )


def test_empty_section_name_rejected():
    with pytest.raises(ValueError, match="non-empty name"):
        SongInput(
            source_language="Hindi",
            sections=[SectionInput(name="   ", source_text="a")],
        )


def test_valid_input_with_voice_and_repeats_passes():
    song = SongInput(
        source_language="Hindi",
        sections=[
            SectionInput(name="verse_1", source_text="a", voice="Alka"),
            SectionInput(name="chorus", source_text="b", voice="Arijit"),
            SectionInput(name="chorus_2", source_text="b", repeats="chorus"),
        ],
    )
    assert song.sections[0].voice == "Alka"
    assert song.sections[2].repeats == "chorus"


# ---------------------------------------------------------------------------
# Voice in room memory
# ---------------------------------------------------------------------------


def _minimal_ruling(section: str, voice: str | None = None) -> JudgeRuling:
    return JudgeRuling(
        section=section,
        final_line="line",
        priority_tradeoffs_made="none",
        voice=voice,
    )


def test_room_memory_labels_rulings_with_voice():
    memory = RoomMemory(prior_rulings=[_minimal_ruling("verse_1", voice="Alka")])
    summary = memory.summary_for_prompt()
    assert "voice: Alka" in summary


def test_room_memory_omits_voice_label_when_unset():
    memory = RoomMemory(prior_rulings=[_minimal_ruling("verse_1")])
    assert "voice:" not in memory.summary_for_prompt()


# ---------------------------------------------------------------------------
# Phrase-level motif renderings
# ---------------------------------------------------------------------------


def test_ruling_accepts_motif_renderings():
    ruling = JudgeRuling(
        section="chorus",
        final_line="If you're here. If you're here.",
        priority_tradeoffs_made="kept refrain verbatim",
        motif_renderings={"agar tum saath ho": "If you're here."},
    )
    assert ruling.motif_renderings["agar tum saath ho"] == "If you're here."


def test_ruling_motif_renderings_default_empty():
    assert _minimal_ruling("verse_1").motif_renderings == {}


# ---------------------------------------------------------------------------
# Renamed dimension enum
# ---------------------------------------------------------------------------


def test_natural_target_language_is_the_dimension_name():
    ruling = JudgeRuling(
        section="verse_1",
        final_line="line",
        priority_tradeoffs_made="none",
        dimension_scores=[
            {"dimension": "natural_target_language", "score": 0.9, "note": "ok"}
        ],
    )
    assert ruling.dimension_scores[0].dimension == "natural_target_language"


def test_old_english_coded_dimension_name_rejected():
    with pytest.raises(Exception):
        JudgeRuling(
            section="verse_1",
            final_line="line",
            priority_tradeoffs_made="none",
            dimension_scores=[
                {"dimension": "natural_english", "score": 0.9, "note": "ok"}
            ],
        )


# ---------------------------------------------------------------------------
# Unicode-aware syllable counting
# ---------------------------------------------------------------------------


def test_accented_words_are_not_split():
    # Under the old [A-Za-z'] regex, "café" tokenized as "caf" (1 syllable).
    assert count_syllables_word("café") == 2


def test_accented_word_counts_inside_a_line():
    assert count_syllables_line("a café here") == (
        count_syllables_word("a")
        + count_syllables_word("café")
        + count_syllables_word("here")
    )
