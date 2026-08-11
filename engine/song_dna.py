"""Builds a SongDNA from a SongInput via one LLM call (docs/SONG_DNA.md), or —
above SECTION_COUNT_SOFT_LIMIT distinct sections — via the chunked long-song
path (_generate_chunked_song_dna): one call for the whole-work fields
(artistic thesis, arc shape, motifs, etc. — dimensions that genuinely need to
see the whole song at once), then the per-section breakdown in batches of
SECTION_CHUNK_SIZE sections each, every batch anchored to that same
whole-work read so separate batches don't drift into inconsistent readings
of the same song. This still isn't the SAME analysis a true single-call read
of a short song gets — each section-batch call sees only its own sections'
text, not the others', so a narrative_function's "relation_to_adjacent" note
for the last section of one batch can't literally see the first section of
the next. That's a real, disclosed trade-off against the alternative this
replaces (silent truncation, no per-section analysis at all for the omitted
sections) — see docs/CAPABILITY_MATRIX.md for the honest comparison.
"""
from __future__ import annotations

import logging

from .language_profile import NEUTRAL_PROFILE, LanguageProfile
from .llm_client import LLMClient
from .models import (
    DensityItem,
    EmotionalArcPoint,
    NarrativeFunctionItem,
    SectionInput,
    SectionProfile,
    SongDNA,
    SongInput,
)
from .prompts import song_dna_overview_prompt, song_dna_prompt, song_dna_sections_prompt

logger = logging.getLogger(__name__)

# Above this many distinct sections, a single-call analysis is running
# outside the territory it was built and tested for (silent omissions past
# this point, before the chunked path existed) — generate_song_dna switches
# to _generate_chunked_song_dna instead of running the one-call prompt.
SECTION_COUNT_SOFT_LIMIT = 15

# Sections per batch in the chunked path — comfortably inside the 3-9
# section range the single-call prompt was actually built and tested
# against, leaving real headroom in the 8k reply budget per batch rather
# than picking a size that just barely avoids the soft limit's own failure
# mode.
SECTION_CHUNK_SIZE = 8


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


def _chunk_sections(sections: list[SectionInput], size: int) -> list[list[SectionInput]]:
    return [sections[i : i + size] for i in range(0, len(sections), size)]


def _generate_chunked_song_dna(
    dna_input: SongInput, client: LLMClient, profile: LanguageProfile
) -> SongDNA:
    """The long-song path: one call for the whole-work fields, then the
    per-section breakdown in SECTION_CHUNK_SIZE-sized batches, each batch
    grounded in that same whole-work read. See this module's docstring for
    the honest trade-off against a true single-call analysis.
    """
    logger.info(
        "%d distinct sections exceeds the single-call Song DNA soft limit "
        "of %d — using the chunked long-song path (%d sections per batch) "
        "instead of one call.",
        len(dna_input.sections),
        SECTION_COUNT_SOFT_LIMIT,
        SECTION_CHUNK_SIZE,
    )
    overview_system, overview_user = song_dna_overview_prompt(dna_input, profile)
    overview = client.complete_json(
        overview_system, overview_user, max_tokens=4000, stage="song_dna_overview"
    )

    sections: list[dict] = []
    for chunk in _chunk_sections(dna_input.sections, SECTION_CHUNK_SIZE):
        system, user = song_dna_sections_prompt(dna_input, chunk, overview)
        reply = client.complete_json(system, user, max_tokens=8000, stage="song_dna_sections")
        sections.extend(reply.get("sections", []))

    return SongDNA.model_validate({**overview, "sections": sections})


def generate_song_dna(
    song: SongInput,
    client: LLMClient,
    profile: LanguageProfile = NEUTRAL_PROFILE,
) -> SongDNA:
    dna_input = _build_dna_input(song)
    if len(dna_input.sections) > SECTION_COUNT_SOFT_LIMIT:
        dna = _generate_chunked_song_dna(dna_input, client, profile)
    else:
        system, user = song_dna_prompt(dna_input, profile)
        data = client.complete_json(system, user, max_tokens=8000, stage="song_dna")
        dna = SongDNA.model_validate(data)
    dna = _fill_missing_sections(dna, dna_input)
    dna = _duplicate_repeated_profiles(dna, song)
    return dna
