"""Verifies the FULL room's (docs/WRITERS_ROOM.md) control flow — Song DNA,
all five rounds, and room memory carrying forward between sections —
without calling any real model provider. A FakeLLMClient returns canned,
schema-valid JSON keyed off distinctive phrases in each stage's system
prompt. See tests/test_writers_room_v1.py for the V1 minimal room (the
default pipeline as of docs/WRITERS_ROOM_V1.md) — these tests pin
room_version="full" explicitly since v1 is now the default.
"""
from __future__ import annotations

import re

from engine.models import SectionInput, SongInput
from engine.pipeline import run_engine

FAKE_SONG_DNA = {
    "artistic_thesis": "Holding on can be its own act of love.",
    "genre_feel": "melancholic pop ballad",
    "arc_shape": "slow ambivalence resolving into release",
    "songwriter_intention": "test intention",
    "turn_points": [{"section": "verse_1", "cause": "test cause"}],
    "sections": [
        {
            "name": "verse_1",
            "narrative_function": {
                "section": "verse_1",
                "function": "setup",
                "relation_to_adjacent": "n/a",
            },
            "density": {"section": "verse_1", "density": "sparse", "note": "test"},
            "emotional_arc_point": {
                "section": "verse_1",
                "valence": -0.4,
                "intensity": 0.3,
                "dominant_feeling": "guarded grief",
            },
            "imagery": [
                {
                    "section": "verse_1",
                    "image": "locked drawer",
                    "sensory_channel": "visual",
                    "stands_in_for": "guarded attachment",
                }
            ],
            "vulnerability": [
                {
                    "section": "verse_1",
                    "what_is_admitted": "she can't let go",
                    "directness": "buried_in_imagery",
                    "felt_cost": "moderate",
                }
            ],
            "rhythm": [],
        }
    ],
    "motifs": [
        {
            "motif": "locked drawer",
            "first_occurrence": "verse_1",
            "occurrences": [{"section": "verse_1", "how_meaning_shifted": "introduced"}],
            "resolves_or_breaks_at_end": None,
        }
    ],
    "ambiguities": [],
    "symbols": [
        {
            "section": "verse_1",
            "symbol": "locked drawer",
            "concrete_form": "a drawer",
            "symbolic_meaning": "guarded attachment",
            "register": "invented_for_this_song",
        }
    ],
    "repetition_patterns": [],
    "style": {
        "diction_register": "plain",
        "rhyme_type": "none",
        "syntax_tendency": "fragments",
        "signature_devices": [],
    },
}

FINAL_LINE = "I keep the drawer locked, the way you keep an old ache."


class FakeLLMClient:
    """Duck-types LLMClient.complete_json without touching the network."""

    def __init__(self):
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str, max_tokens: int | None = None) -> dict:
        self.calls.append(system[:60])

        if "You are a songwriting analyst" in system:
            return FAKE_SONG_DNA

        if "your one candidate English line" in system:
            return {
                "text": "I keep the drawer locked, just like you kept your hurt.",
                "leans_into": "guarded attachment",
            }

        if "Comment ONLY from your own expertise" in system:
            ids = re.findall(r"\[(\w+)\]", user)
            return {
                "critiques": [
                    {
                        "candidate_id": cid,
                        "verdict": "workable",
                        "strength": "test strength",
                        "failure": "test failure",
                        "suggested_fix": None,
                    }
                    for cid in ids
                ]
            }

        if "exactly one rebuttal turn" in system:
            return {"rebuttals": []}

        if "recombination pass" in system:
            return {
                "candidates": [
                    {
                        "text": FINAL_LINE,
                        "leans_into": "guarded attachment",
                        "rationale": "test",
                    }
                ]
            }

        if "You are the Judge." in system:
            return {
                "final_line": FINAL_LINE,
                "sources_used": [
                    {"agent": "songwriter_recombination", "contribution": "final phrasing"}
                ],
                "vetoes_applied": [],
                "priority_tradeoffs_made": "test tradeoff",
                "disagreements_overruled": [],
            }

        raise AssertionError(f"Unexpected prompt in test: {system[:80]!r}")


def test_run_engine_single_section():
    song = SongInput(
        title="Test Song",
        source_language="English (test)",
        sections=[
            SectionInput(
                name="verse_1",
                source_text="She keeps his letters in a locked drawer.",
            )
        ],
    )
    client = FakeLLMClient()

    result = run_engine(song, client=client, room_version="full")

    assert result.dna.artistic_thesis == FAKE_SONG_DNA["artistic_thesis"]
    assert len(result.section_results) == 1

    section_result = result.section_results[0]
    assert section_result.section == "verse_1"
    assert len(section_result.candidates_round1) == 3  # translator, poet, songwriter
    assert len(section_result.critiques) == 4 * 3  # 4 diagnostic agents x 3 candidates
    assert len(section_result.rebuttals) == 0
    assert len(section_result.candidates_round4) == 1
    assert section_result.ruling.final_line == FINAL_LINE

    # Room memory should have recorded a rendering for the motif this section touches.
    assert result.dna.motifs[0].motif == "locked drawer"

    assert FINAL_LINE in result.final_lyrics()


def test_room_memory_passed_to_second_section():
    """A second section's prompts should reference the first section's ruling,
    proving room memory (docs/WRITERS_ROOM.md §8) actually carries forward.
    """
    song = SongInput(
        source_language="English (test)",
        sections=[
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="verse_1", source_text="line one duplicate"),
        ],
    )

    class MemoryCheckingFakeClient(FakeLLMClient):
        def complete_json(self, system, user, max_tokens=None):
            if "your one candidate English line" in system and self.calls.count(
                system[:60]
            ) >= 3:
                # Second section's generation calls: room memory must mention
                # the first section's final line by now.
                assert "Decisions already made earlier in this song" in user
            return super().complete_json(system, user, max_tokens)

    client = MemoryCheckingFakeClient()
    result = run_engine(song, client=client, room_version="full")
    assert len(result.section_results) == 2
