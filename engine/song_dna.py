"""Builds a SongDNA from a SongInput via one LLM call (docs/SONG_DNA.md)."""
from __future__ import annotations

from .llm_client import LLMClient
from .models import (
    DensityItem,
    EmotionalArcPoint,
    NarrativeFunctionItem,
    SectionProfile,
    SongDNA,
    SongInput,
)
from .prompts import song_dna_prompt


def _fill_missing_sections(dna: SongDNA, song: SongInput) -> SongDNA:
    """The prompt requires one SectionProfile per input section, but model
    output isn't guaranteed — a short or wordless section (an "oh oh" hook,
    a vocal refrain) is the most likely one to get skipped. Rather than let
    a missing section crash the whole run, synthesize a minimal, honestly
    neutral placeholder for it so the pipeline can still proceed.
    """
    present = {s.name for s in dna.sections}
    missing = [s.name for s in song.sections if s.name not in present]
    if not missing:
        return dna

    for name in missing:
        dna.sections.append(
            SectionProfile(
                name=name,
                narrative_function=NarrativeFunctionItem(
                    section=name,
                    function="unspecified",
                    relation_to_adjacent="not analyzed — model omitted this section",
                ),
                density=DensityItem(
                    section=name,
                    density="sparse",
                    note="not analyzed — placeholder inserted after generation",
                ),
                emotional_arc_point=EmotionalArcPoint(
                    section=name, valence=0.0, intensity=0.0, dominant_feeling="unspecified"
                ),
            )
        )
    return dna


def generate_song_dna(song: SongInput, client: LLMClient) -> SongDNA:
    system, user = song_dna_prompt(song)
    data = client.complete_json(system, user, max_tokens=8000)
    dna = SongDNA.model_validate(data)
    return _fill_missing_sections(dna, song)
