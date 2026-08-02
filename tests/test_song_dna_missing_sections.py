"""Regression test: a model can omit a section from its Song DNA response
(most likely a short/wordless one, e.g. a vocal refrain) — this must not
crash the pipeline. See engine/song_dna.py's _fill_missing_sections.
"""
from __future__ import annotations

from engine.models import SectionInput, SongInput
from engine.song_dna import generate_song_dna

from .test_pipeline_mock import FAKE_SONG_DNA

# FAKE_SONG_DNA (in test_pipeline_mock.py) only has a SectionProfile for
# "verse_1" — deliberately reused here unmodified to simulate a model
# response that omitted a section the song actually has.


class FakeClientOmitsASection:
    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        if "You are a songwriting analyst" in system:
            return FAKE_SONG_DNA
        raise AssertionError("Only the Song DNA call is exercised in this test")


def test_missing_section_is_patched_not_fatal():
    song = SongInput(
        source_language="English (test)",
        sections=[
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="refrain", source_text="na na naah"),
        ],
    )
    client = FakeClientOmitsASection()

    dna = generate_song_dna(song, client)

    names = {s.name for s in dna.sections}
    assert names == {"verse_1", "refrain"}

    patched = dna.section("refrain")
    assert patched.narrative_function.function == "unspecified"
    assert patched.density.density == "sparse"
    assert patched.emotional_arc_point.dominant_feeling == "unspecified"

    # The section the model did return is untouched.
    original = dna.section("verse_1")
    assert original.emotional_arc_point.dominant_feeling == "guarded grief"
