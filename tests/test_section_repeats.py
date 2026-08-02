"""Verifies the `repeats` mechanism (engine/pipeline.py): a section marked
as repeating an earlier one reuses that section's ruling and Song DNA
profile verbatim, at zero extra LLM calls — this is what lets a song's full
repeated structure (e.g. a chorus recurring four times) be represented
without wasting calls re-judging identical text.
"""
from __future__ import annotations

from engine.models import SectionInput, SongInput
from engine.pipeline import run_engine

from .test_writers_room_v1 import DIMENSION_SCORES, FIVE_PHILOSOPHY_CANDIDATES
from .test_pipeline_mock import FAKE_SONG_DNA


class FakeClientForRepeats:
    def __init__(self):
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append(system[:60])
        if "You are a songwriting analyst" in system:
            return FAKE_SONG_DNA
        if "You are the Creative Adapter" in system:
            return {"candidates": FIVE_PHILOSOPHY_CANDIDATES}
        if "uncertainty_type" in system:
            return {
                "text": "I keep the drawer locked.",
                "leans_into": "guarded attachment",
                "confidence": 0.9,
                "uncertainty_type": "none",
            }
        if "running the minimal V1 room" in system:
            return {
                "ready_to_rule": True,
                "ruling": {
                    "final_line": "I keep the drawer locked.",
                    "sources_used": [],
                    "vetoes_applied": [],
                    "deviations": [],
                    "dimension_scores": DIMENSION_SCORES,
                    "priority_tradeoffs_made": "test",
                    "disagreements_overruled": [],
                },
                "specialists_needed": [],
                "why": "test",
            }
        raise AssertionError(f"Unexpected prompt: {system[:80]!r}")


def test_repeated_section_reuses_ruling_at_zero_extra_calls():
    song = SongInput(
        source_language="English (test)",
        sections=[
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="chorus", source_text="chorus line"),
            # Recurs verbatim later in the song — should not trigger any
            # new Room calls, and should reuse "chorus"'s exact ruling.
            SectionInput(name="chorus_2", source_text="chorus line", repeats="chorus"),
        ],
    )
    client = FakeClientForRepeats()

    result = run_engine(song, client=client, room_version="v1")

    assert len(result.section_results) == 3
    chorus_result = result.section_results[1]
    repeated_result = result.section_results[2]

    assert repeated_result.section == "chorus_2"
    assert repeated_result.ruling.section == "chorus_2"
    assert repeated_result.ruling.final_line == chorus_result.ruling.final_line

    # Calls: 1 song-dna + (verse_1: translator+adapter+triage=3) +
    # (chorus: translator+adapter+triage=3) = 7. chorus_2 adds nothing.
    assert len(client.calls) == 7

    assert "[chorus_2]" in result.final_lyrics()


def test_song_dna_does_not_re_analyze_repeated_section_text():
    song = SongInput(
        source_language="English (test)",
        sections=[
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="chorus_2", source_text="anything", repeats="verse_1"),
        ],
    )
    client = FakeClientForRepeats()

    result = run_engine(song, client=client, room_version="v1")

    dna_section_names = {s.name for s in result.dna.sections}
    # FAKE_SONG_DNA only ever describes "verse_1" — the duplicated profile
    # for chorus_2 proves _duplicate_repeated_profiles ran instead of the
    # model being asked to analyze "chorus_2" directly.
    assert dna_section_names == {"verse_1", "chorus_2"}
    assert result.dna.section("chorus_2").emotional_arc_point.dominant_feeling == (
        result.dna.section("verse_1").emotional_arc_point.dominant_feeling
    )
