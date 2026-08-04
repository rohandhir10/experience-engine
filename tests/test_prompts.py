"""Tests for engine/prompts.py's _repeated_source_lines_note — the
deterministic, computed reminder handed to the Creative Adapter naming
exactly which source lines repeat and how many times, so it doesn't have
to notice and count a repeat on its own while also following constraint
#7's abstract rule. See tests/test_golden_prompts.py for confirmation
that a section with no repetition sees a byte-identical prompt.
"""
from __future__ import annotations

from engine.prompts import _repeated_source_lines_note, creative_adapter_prompt
from engine.models import RoomMemory, SongDNA

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
