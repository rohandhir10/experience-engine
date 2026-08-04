"""Tests for engine/prompts.py's _repeated_source_lines_note — the
deterministic, computed reminder handed to the Creative Adapter naming
exactly which source lines repeat and how many times, so it doesn't have
to notice and count a repeat on its own while also following constraint
#7's abstract rule. See tests/test_golden_prompts.py for confirmation
that a section with no repetition sees a byte-identical prompt.
"""
from __future__ import annotations

from engine.prompts import (
    _repeated_source_lines_note,
    _ruling_schema,
    creative_adapter_prompt,
    judge_triage_prompt,
)
from engine.models import Candidate, RoomMemory, RoutingSignals, SongDNA

MINIMAL_DNA = SongDNA.model_validate(
    {
        "artistic_thesis": "test",
        "genre_feel": "test",
        "poetic_register": "test",
        "arc_shape": "test",
        "songwriter_intention": "test",
        "turn_points": [],
        "sections": [
            {
                "name": "verse_1",
                "narrative_function": {
                    "section": "verse_1",
                    "function": "test",
                    "relation_to_adjacent": "test",
                },
                "density": {"section": "verse_1", "density": "sparse", "note": "test"},
                "emotional_arc_point": {
                    "section": "verse_1",
                    "valence": 0.0,
                    "intensity": 0.5,
                    "dominant_feeling": "test",
                },
                "imagery": [],
                "vulnerability": [],
                "rhythm": [],
            }
        ],
        "motifs": [],
        "ambiguities": [],
        "symbols": [],
        "repetition_patterns": [],
        "style": {
            "diction_register": "test",
            "rhyme_type": "test",
            "syntax_tendency": "test",
            "signature_devices": [],
        },
    }
)


def test_no_note_when_source_has_no_repeated_lines():
    assert _repeated_source_lines_note("one line\nanother line\na third line") == ""


def test_notes_a_line_repeated_verbatim():
    note = _repeated_source_lines_note("hold me now\nsome other line\nhold me now")
    assert "'hold me now' appears 2 times" in note


def test_notes_a_repeated_couplet_as_two_separate_line_counts():
    """A two-line couplet repeated twice shows up as two separate
    line-level counts (one per line of the couplet) - the note doesn't
    need to understand "couplet" as a unit, just report each line's own
    verbatim count, which is what verify.py's deterministic check (the
    receiving end of this same failure mode) also keys off of.
    """
    source = "hold me now\nnever let go\nhold me now\nnever let go"
    note = _repeated_source_lines_note(source)
    assert "'hold me now' appears 2 times" in note
    assert "'never let go' appears 2 times" in note


def test_case_differences_still_count_as_the_same_repeated_line():
    note = _repeated_source_lines_note("Hold Me Now\nsome other line\nhold me now")
    assert "appears 2 times" in note


def test_creative_adapter_prompt_includes_the_note_when_source_repeats():
    _, user = creative_adapter_prompt(
        "hold me now\nsome other line\nhold me now",
        MINIMAL_DNA,
        "verse_1",
        RoomMemory(),
    )
    assert "appears 2 times" in user


def test_creative_adapter_prompt_omits_the_note_when_source_has_no_repeats():
    _, user = creative_adapter_prompt(
        "one line\nanother line",
        MINIMAL_DNA,
        "verse_1",
        RoomMemory(),
    )
    assert "appears" not in user


# ---------------------------------------------------------------------------
# _ruling_schema's honorific_note field — item #6 of the chapter-level-
# context roadmap. Gated on `voice` so an unattributed section (most
# songs) sees a byte-identical schema; see tests/test_golden_prompts.py
# for confirmation the no-voice fixture's hash didn't need to change.
# ---------------------------------------------------------------------------


def test_ruling_schema_omits_honorific_field_without_a_voice():
    assert "honorific_note" not in _ruling_schema(voice=None)


def test_ruling_schema_includes_honorific_field_when_voice_is_given():
    schema = _ruling_schema(voice="Guard Captain")
    assert "honorific_note" in schema


def test_judge_triage_prompt_includes_honorific_field_only_with_a_voice():
    candidates = [
        Candidate(id="a", agent="translator", text="x", round="generation", confidence=1.0),
    ]
    signals = RoutingSignals(culturally_specific_symbol_count=0, suggested_specialists=[], reasons=[])

    system_without_voice, _ = judge_triage_prompt(
        candidates, signals, "source", MINIMAL_DNA, "verse_1", RoomMemory()
    )
    assert "honorific_note" not in system_without_voice

    system_with_voice, _ = judge_triage_prompt(
        candidates, signals, "source", MINIMAL_DNA, "verse_1", RoomMemory(), voice="Guard Captain"
    )
    assert "honorific_note" in system_with_voice


def test_room_memory_surfaces_honorific_state_to_every_prompt():
    """RoomMemory.summary_for_prompt() already gets included in
    creative_adapter_prompt/judge_triage_prompt/judge_final_prompt/
    generation_prompt_v1 - confirming it here is enough to know every
    one of those stages sees the running honorific state, without
    needing to touch each prompt builder's signature.
    """
    memory = RoomMemory(honorific_state={"Guard Captain": "formal, deferential"})
    _, user = creative_adapter_prompt("source text", MINIMAL_DNA, "verse_1", memory)
    assert "Guard Captain: formal, deferential" in user
