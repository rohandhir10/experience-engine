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


def _build_dna_input(song: SongInput) -> SongInput:
    """Sections marked `repeats` share an earlier section's text verbatim —
    exclude them from the Song DNA prompt so identical text isn't analyzed
    twice; their SectionProfile is copied from the repeated section instead
    (_duplicate_repeated_profiles), at zero extra LLM cost.
    """
    distinct_sections = [s for s in song.sections if not s.repeats]
    return song.model_copy(update={"sections": distinct_sections})


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


def _duplicate_repeated_profiles(dna: SongDNA, song: SongInput) -> SongDNA:
    """Copies the repeated section's SectionProfile for every section that
    sets `repeats`, so every section in the original song ends up with a
    profile without ever asking the model to re-analyze identical text.
    """
    for section in song.sections:
        if not section.repeats:
            continue
        duplicated = dna.section(section.repeats).model_copy(deep=True)
        duplicated.name = section.name
        dna.sections.append(duplicated)
    return dna


def generate_song_dna(song: SongInput, client: LLMClient) -> SongDNA:
    dna_input = _build_dna_input(song)
    system, user = song_dna_prompt(dna_input)
    data = client.complete_json(system, user, max_tokens=8000)
    dna = SongDNA.model_validate(data)
    dna = _fill_missing_sections(dna, dna_input)
    dna = _duplicate_repeated_profiles(dna, song)
    return dna
