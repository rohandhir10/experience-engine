"""Byte-identical prompt regression guard.

This is the safety net for the V2 multilingual refactor
(docs/MULTILINGUAL_V2.md, Phase 1). Every prompt the engine can build is
hashed for a fixed fixture under the default (neutral) language profile.
If any refactor changes a single byte of any prompt, one of these fails.

The promise Phase 1 makes is that adding the Language Profile system
changes NOTHING until a real profile is supplied. That promise is only
worth anything if it is enforced mechanically — a human reading a diff
cannot verify "no prompt changed" across seven builders.

When a prompt is INTENTIONALLY changed, update the expected hash here in
the same commit, so the change is visible in review rather than silent.
"""
from __future__ import annotations

import hashlib

import pytest

from engine import prompts
from engine.models import (
    Candidate,
    Critique,
    RoomMemory,
    RoutingSignals,
    SectionInput,
    SongDNA,
    SongInput,
)

FIXTURE_DNA = SongDNA.model_validate(
    {
        "artistic_thesis": "Holding on can be its own form of loyalty.",
        "genre_feel": "sparse acoustic ballad",
        "arc_shape": "slow ambivalence resolving into release",
        "songwriter_intention": "justify an act of letting go",
        "turn_points": [{"section": "chorus", "cause": "the drawer opens"}],
        "sections": [
            {
                "name": "verse_1",
                "narrative_function": {
                    "section": "verse_1",
                    "function": "establish the withheld object",
                    "relation_to_adjacent": "sets up the chorus turn",
                },
                "density": {"section": "verse_1", "density": "sparse", "note": "few images"},
                "emotional_arc_point": {
                    "section": "verse_1",
                    "valence": -0.3,
                    "intensity": 0.4,
                    "dominant_feeling": "guarded attachment",
                },
                "imagery": [
                    {
                        "section": "verse_1",
                        "image": "a locked drawer",
                        "sensory_channel": "tactile",
                        "stands_in_for": "a memory kept deliberately unexamined",
                    }
                ],
                "vulnerability": [
                    {
                        "section": "verse_1",
                        "what_is_admitted": "she has not moved on",
                        "directness": "buried_in_imagery",
                        "felt_cost": "admitting the years were wasted",
                    }
                ],
                "rhythm": [],
            }
        ],
        "motifs": [
            {
                "motif": "the drawer",
                "first_occurrence": "verse_1",
                "occurrences": [
                    {"section": "verse_1", "how_meaning_shifted": "introduced as closed"}
                ],
            }
        ],
        "ambiguities": [
            {
                "section": "verse_1",
                "ambiguous_element": "whether the drawer is ever opened",
                "competing_readings": ["she opens it", "she never does"],
                "is_the_ambiguity_the_point": True,
            }
        ],
        "symbols": [
            {
                "section": "verse_1",
                "symbol": "the drawer",
                "concrete_form": "a bedside drawer with a key",
                "symbolic_meaning": "withheld grief",
                "register": "archetypal",
            }
        ],
        "repetition_patterns": [],
        "style": {
            "diction_register": "plain, unliterary",
            "rhyme_type": "slant",
            "syntax_tendency": "short declaratives",
            "signature_devices": ["understatement"],
        },
    }
)

FIXTURE_SONG = SongInput(
    title="Locked Drawer",
    source_language="Hindi",
    context_note="A woman sorting a dead partner's things.",
    sections=[SectionInput(name="verse_1", source_text="मैंने दराज़ बंद रखी")],
)

FIXTURE_CANDIDATES = [
    Candidate(
        id="a1",
        agent="translator",
        text="I kept the drawer closed",
        leans_into="the literal fact",
        round="generation",
        syllable_count=6,
    ),
    Candidate(
        id="c1",
        agent="creative_adapter",
        text="The drawer stayed shut.",
        leans_into="restraint",
        confidence=0.9,
        philosophy="maximum_fidelity",
        round="generation",
        syllable_count=5,
    ),
]

FIXTURE_MEMORY = RoomMemory()
FIXTURE_SIGNALS = RoutingSignals(
    culturally_specific_symbol_count=0,
    suggested_specialists=[],
    reasons=[],
)
FIXTURE_CRITIQUES = [
    Critique(
        candidate_id="c1",
        agent="native_speaker",
        verdict="strong",
        strength="reads naturally",
        failure="",
    )
]


def _hash(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:16]


def _v1_prompts() -> dict[str, tuple[str, str]]:
    """Every prompt the V1 room can build, for the fixture above."""
    return {
        "song_dna": prompts.song_dna_prompt(FIXTURE_SONG),
        "generation_translator": prompts.generation_prompt_v1(
            "translator", "मैंने दराज़ बंद रखी", FIXTURE_DNA, "verse_1", FIXTURE_MEMORY
        ),
        "creative_adapter": prompts.creative_adapter_prompt(
            "मैंने दराज़ बंद रखी", FIXTURE_DNA, "verse_1", FIXTURE_MEMORY
        ),
        "judge_triage": prompts.judge_triage_prompt(
            FIXTURE_CANDIDATES,
            FIXTURE_SIGNALS,
            "मैंने दराज़ बंद रखी",
            FIXTURE_DNA,
            "verse_1",
            FIXTURE_MEMORY,
        ),
        "judge_final": prompts.judge_final_prompt(
            FIXTURE_CANDIDATES,
            FIXTURE_CRITIQUES,
            FIXTURE_SIGNALS,
            "मैंने दराज़ बंद रखी",
            FIXTURE_DNA,
            "verse_1",
            FIXTURE_MEMORY,
        ),
        "diagnosis_native_speaker": prompts.diagnosis_prompt(
            "native_speaker",
            FIXTURE_CANDIDATES,
            "मैंने दराज़ बंद रखी",
            FIXTURE_DNA,
            "verse_1",
        ),
    }


# Captured from the pre-refactor engine. A failure here means a prompt
# changed — intentional or not.
#
# creative_adapter/judge_triage/judge_final updated deliberately: added
# explicit instructions to preserve repetition count, rhetorical questions,
# metaphor/imagery, and to reject "sounds smoother/more relatable/more
# natural" as sufficient justification for dropping a source device —
# following a real production run that collapsed a triple-repeated phrase
# ("then who is right") to a single occurrence, justified exactly that way.
EXPECTED_HASHES = {
    "song_dna": "cb396a04e923a3f4",
    "generation_translator": "8e9b94913c4a3da8",
    "creative_adapter": "d10e3c2cea7ded75",
    "judge_triage": "435269b27d16c754",
    "judge_final": "559460aceaa370ff",
    "diagnosis_native_speaker": "9452b56158c2d859",
}


@pytest.mark.parametrize("name", sorted(EXPECTED_HASHES))
def test_prompt_is_byte_identical(name: str):
    system, user = _v1_prompts()[name]
    assert _hash(system, user) == EXPECTED_HASHES[name], (
        f"The {name!r} prompt changed. If that was intentional, update "
        "EXPECTED_HASHES in the same commit so the change is reviewable."
    )


def test_every_v1_prompt_is_covered():
    """A new prompt builder must be added to this guard, not skipped."""
    assert set(_v1_prompts()) == set(EXPECTED_HASHES)


def test_agent_briefs_have_no_unresolved_placeholders():
    for agent in prompts.AGENT_BRIEFS:
        brief = prompts.agent_brief(agent, "English")
        assert "{" not in brief, f"{agent} brief has an unrendered placeholder"
