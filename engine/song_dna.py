"""Builds a SongDNA from a SongInput via one LLM call (docs/SONG_DNA.md).

Known architectural bound: the whole work is analyzed in ONE call with an
8k-token reply budget. Fine for a song's 3-9 sections; for long-form input
the model omits more and the placeholder machinery below fills more, so
quality degrades silently rather than crashing. The warnings here make
that degradation visible instead of silent.
"""
from __future__ import annotations

import logging

from .language_profile import NEUTRAL_PROFILE, LanguageProfile
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

logger = logging.getLogger(__name__)

# Above this many distinct sections, the one-call analysis is running
# outside the territory it was built and tested for.
SECTION_COUNT_SOFT_LIMIT = 15


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

    logger.warning(
        "Song DNA omitted %d section(s) (%s); inserting neutral placeholders. "
        "These sections will be adapted WITHOUT real per-section analysis.",
        len(missing),
        ", ".join(missing),
    )
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


def generate_song_dna(
    song: SongInput,
    client: LLMClient,
    profile: LanguageProfile = NEUTRAL_PROFILE,
) -> SongDNA:
    dna_input = _build_dna_input(song)
    if len(dna_input.sections) > SECTION_COUNT_SOFT_LIMIT:
        logger.warning(
            "%d distinct sections exceeds the single-call Song DNA soft "
            "limit of %d — expect omissions/truncation; long-form input "
            "needs chunked analysis (not yet implemented).",
            len(dna_input.sections),
            SECTION_COUNT_SOFT_LIMIT,
        )
    system, user = song_dna_prompt(dna_input, profile)
    data = client.complete_json(system, user, max_tokens=8000)
    dna = SongDNA.model_validate(data)
    dna = _fill_missing_sections(dna, dna_input)
    dna = _duplicate_repeated_profiles(dna, song)
    return dna
