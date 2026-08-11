"""Verifies the `varies_from` mechanism — a section that's a NEAR-repeat of
an earlier one (same lines, a small number changed, e.g. a final chorus
with one "lifted" line). Unlike `repeats` (tests/test_section_repeats.py),
the room still runs for this section, but RoomMemory.variation_note should
carry an explicit instruction anchoring it to the earlier section's ruling.

Also covers the detection this mechanism depends on
(engine/recurrence.py::detect_section_repeats) and the auto-population of
`repeats`/`varies_from` for real user songs
(engine/text_ingest.py::split_into_sections) — before that auto-detection
existed, both fields were real but only ever set by hand in test fixtures,
never by anything a real user's pasted lyrics went through.
"""
from __future__ import annotations

import pytest

from engine.models import SectionInput, SongInput
from engine.pipeline import run_engine
from engine.recurrence import detect_section_repeats, diff_line_indices
from engine.text_ingest import split_into_sections

from .test_writers_room_v1 import DIMENSION_SCORES, FIVE_PHILOSOPHY_CANDIDATES
from .test_pipeline_mock import FAKE_SONG_DNA

CHORUS = "You are the reason I stay\nEven when the light fades away\nI won't let this go"
CHORUS_VARIANT = "You are the reason I stay\nEven when the light fades away\nI never let this go"
CHORUS_TOO_DIFFERENT = "Something completely different here\nNothing like the chorus at all\nNot even close"


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def test_diff_line_indices_finds_changed_lines():
    assert diff_line_indices(CHORUS, CHORUS_VARIANT) == [2]


def test_diff_line_indices_none_on_line_count_mismatch():
    assert diff_line_indices(CHORUS, "just one line") is None


def test_diff_line_indices_empty_list_for_identical_text():
    assert diff_line_indices(CHORUS, CHORUS) == []


def test_detect_exact_repeat():
    sections = [("verse_1", "line one"), ("chorus", CHORUS), ("chorus_2", CHORUS)]
    matches = detect_section_repeats(sections)
    assert matches.keys() == {"chorus_2"}
    assert matches["chorus_2"].kind == "exact"
    assert matches["chorus_2"].repeats_from == "chorus"


def test_detect_variant_repeat():
    sections = [("verse_1", "line one"), ("chorus", CHORUS), ("chorus_2", CHORUS_VARIANT)]
    matches = detect_section_repeats(sections)
    assert matches.keys() == {"chorus_2"}
    assert matches["chorus_2"].kind == "variant"
    assert matches["chorus_2"].repeats_from == "chorus"
    assert matches["chorus_2"].changed_line_indices == [2]


def test_detect_no_match_for_unrelated_sections():
    sections = [("verse_1", "line one"), ("chorus", CHORUS), ("bridge", CHORUS_TOO_DIFFERENT)]
    matches = detect_section_repeats(sections)
    assert matches == {}


def test_detect_prefers_exact_over_variant_when_both_available():
    sections = [
        ("chorus", CHORUS),
        ("chorus_variant", CHORUS_VARIANT),
        # Matches "chorus" exactly AND "chorus_variant" as a variant -
        # exact should win.
        ("chorus_3", CHORUS),
    ]
    matches = detect_section_repeats(sections)
    assert matches["chorus_3"].kind == "exact"
    assert matches["chorus_3"].repeats_from == "chorus"


def test_detect_prefers_fewer_changed_lines_among_variants():
    # chorus_2 changes CHORUS's line 2 ("light" -> "sun") - 1 line from
    # CHORUS. chorus_3 keeps that same "sun" line but changes line 3 to a
    # THIRD wording - so chorus_3 differs from CHORUS by 2 lines, but from
    # chorus_2 by only 1. It should match chorus_2, the closer section,
    # not CHORUS.
    chorus_2 = "You are the reason I stay\nEven when the sun fades away\nI won't let this go"
    chorus_3 = "You are the reason I stay\nEven when the sun fades away\nI still won't let it go"
    sections = [
        ("chorus", CHORUS),
        ("chorus_2", chorus_2),
        ("chorus_3", chorus_3),
    ]
    matches = detect_section_repeats(sections)
    assert matches["chorus_2"].repeats_from == "chorus"
    assert matches["chorus_2"].changed_line_indices == [1]
    assert matches["chorus_3"].repeats_from == "chorus_2"
    assert matches["chorus_3"].changed_line_indices == [2]


def test_detect_ignores_short_sections_for_variant_matching():
    # Two lines is below MIN_LINES_FOR_VARIANT_MATCH (3) - a coincidental
    # same-length short section shouldn't be treated as a variation.
    sections = [("hook", "oh oh"), ("hook_2", "oh no")]
    matches = detect_section_repeats(sections)
    assert matches == {}


def test_detect_requires_a_minority_of_changed_lines():
    # 2 of 3 lines differ - more than half, so this is "a different
    # section that happens to share a line count," not a variation.
    mostly_different = "Something else entirely\nNothing like the chorus\nI won't let this go"
    sections = [("chorus", CHORUS), ("verse_2", mostly_different)]
    matches = detect_section_repeats(sections)
    assert matches == {}


# ---------------------------------------------------------------------------
# Ingestion: real user songs actually get this now
# ---------------------------------------------------------------------------


def test_split_into_sections_auto_detects_exact_repeat():
    text = f"line one\n\n{CHORUS}\n\n{CHORUS}"
    sections = split_into_sections(text)
    assert sections[2].repeats == "section_2"
    assert sections[2].varies_from is None


def test_split_into_sections_auto_detects_variant_repeat():
    text = f"line one\n\n{CHORUS}\n\n{CHORUS_VARIANT}"
    sections = split_into_sections(text)
    assert sections[2].varies_from == "section_2"
    assert sections[2].repeats is None


def test_split_into_sections_leaves_unrelated_sections_alone():
    text = f"line one\n\n{CHORUS}\n\n{CHORUS_TOO_DIFFERENT}"
    sections = split_into_sections(text)
    assert sections[2].repeats is None
    assert sections[2].varies_from is None


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


def test_section_cannot_set_both_repeats_and_varies_from():
    with pytest.raises(ValueError, match="both repeats and"):
        SongInput(
            source_language="English (test)",
            sections=[
                SectionInput(name="chorus", source_text=CHORUS),
                SectionInput(
                    name="chorus_2",
                    source_text=CHORUS_VARIANT,
                    repeats="chorus",
                    varies_from="chorus",
                ),
            ],
        )


def test_varies_from_must_reference_an_earlier_section():
    with pytest.raises(ValueError, match="EARLIER section"):
        SongInput(
            source_language="English (test)",
            sections=[
                SectionInput(name="chorus_2", source_text=CHORUS_VARIANT, varies_from="chorus"),
                SectionInput(name="chorus", source_text=CHORUS),
            ],
        )


# ---------------------------------------------------------------------------
# Pipeline orchestration: the room still runs, anchored to the earlier ruling
# ---------------------------------------------------------------------------


class FakeClientForVariation:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append((system[:60], user))
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


def test_variant_section_still_runs_the_room():
    variant_song = SongInput(
        source_language="English (test)",
        sections=[
            SectionInput(name="chorus", source_text=CHORUS),
            SectionInput(name="chorus_2", source_text=CHORUS_VARIANT, varies_from="chorus"),
        ],
    )
    repeat_song = SongInput(
        source_language="English (test)",
        sections=[
            SectionInput(name="chorus", source_text=CHORUS),
            SectionInput(name="chorus_2", source_text=CHORUS, repeats="chorus"),
        ],
    )

    variant_client = FakeClientForVariation()
    variant_result = run_engine(variant_song, client=variant_client, room_version="v1")

    repeat_client = FakeClientForVariation()
    run_engine(repeat_song, client=repeat_client, room_version="v1")

    # Same 2-section shape either way: 1 song-dna call + 3 calls
    # (translator/adapter/triage) for "chorus". A `repeats` chorus_2 adds
    # nothing (4 calls total) - a `varies_from` chorus_2 gets its own
    # full room run instead (7 calls total), which is the whole point:
    # the changed line needs a REAL adaptation, not a copy.
    assert len(repeat_client.calls) == 4
    assert len(variant_client.calls) == 7
    assert variant_result.section_results[1].section == "chorus_2"


def test_variation_note_reaches_the_room_prompt_and_then_clears():
    song = SongInput(
        source_language="English (test)",
        sections=[
            SectionInput(name="chorus", source_text=CHORUS),
            SectionInput(name="chorus_2", source_text=CHORUS_VARIANT, varies_from="chorus"),
            SectionInput(name="outro", source_text="Just a plain unrelated outro line"),
        ],
    )
    client = FakeClientForVariation()

    run_engine(song, client=client, room_version="v1")

    translator_calls = [user for system, user in client.calls if "You are the Translator" in system]
    # First translator call (chorus itself) should carry no variation note.
    assert "NEAR-repeat" not in translator_calls[0]
    # Second translator call (chorus_2, the variant) should.
    assert "NEAR-repeat of section 'chorus'" in translator_calls[1]
    assert "I keep the drawer locked." in translator_calls[1]
    # Third translator call (outro, unrelated) should NOT still carry it -
    # variation_note must be cleared after the one section it applies to.
    assert "NEAR-repeat" not in translator_calls[2]
