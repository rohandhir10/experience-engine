"""Runs the whole engine end to end for one song: Song DNA once, then the
Writers' Room section by section, carrying room memory forward
(docs/WRITERS_ROOM.md §8 / docs/WRITERS_ROOM_V1.md).

Two room implementations are available:
  - "v1"   (default) — minimal room, docs/WRITERS_ROOM_V1.md. 3 agents by
            default (Translator, Creative Adapter, Judge), specialists
            invoked only when the Judge asks for them.
  - "full" — the original seven-agent room, docs/WRITERS_ROOM.md. Higher
            cost/latency, higher blanket-coverage ceiling; opt in for
            songs where that redundancy is worth paying for.

A section may set `repeats` to an earlier section's name (e.g. a chorus
that recurs verbatim later in the song) — its ruling is reused directly at
zero extra LLM cost instead of re-running the whole room on identical text.
"""
from __future__ import annotations

import logging
from typing import Literal

from .llm_client import LLMClient, create_default_client
from .models import RoomMemory, SectionResult, SectionResultV1, SongDNA, SongInput
from .song_dna import generate_song_dna
from .writers_room import run_section as run_section_full
from .writers_room_v1 import run_section as run_section_v1

RoomVersion = Literal["v1", "full"]

logger = logging.getLogger(__name__)


class EngineResult:
    def __init__(
        self,
        song: SongInput,
        dna: SongDNA,
        section_results: list[SectionResult | SectionResultV1],
        room_version: RoomVersion,
    ):
        self.song = song
        self.dna = dna
        self.section_results = section_results
        self.room_version = room_version

    def final_lyrics(self) -> str:
        return "\n\n".join(
            f"[{r.section}]\n{r.ruling.final_line}" for r in self.section_results
        )

    def to_dict(self) -> dict:
        return {
            "title": self.song.title,
            "source_language": self.song.source_language,
            "room_version": self.room_version,
            "song_dna": self.dna.model_dump(by_alias=True),
            "sections": [r.model_dump() for r in self.section_results],
            "final_lyrics": self.final_lyrics(),
        }


def _reuse_repeated_section(
    section_name: str,
    repeated_from: str,
    results_by_name: dict[str, SectionResult | SectionResultV1],
) -> SectionResult | SectionResultV1:
    if repeated_from not in results_by_name:
        raise ValueError(
            f"Section {section_name!r} sets repeats={repeated_from!r}, but "
            f"{repeated_from!r} hasn't been processed yet — repeats must "
            "reference an earlier section in the song."
        )
    source_result = results_by_name[repeated_from]
    reused = source_result.model_copy(deep=True)
    reused.section = section_name
    reused.ruling.section = section_name
    return reused


def run_engine(
    song: SongInput,
    client: LLMClient | None = None,
    room_version: RoomVersion = "v1",
) -> EngineResult:
    client = client or create_default_client()
    dna = generate_song_dna(song, client)
    room_memory = RoomMemory()
    section_results: list[SectionResult | SectionResultV1] = []
    results_by_name: dict[str, SectionResult | SectionResultV1] = {}

    run_section = run_section_v1 if room_version == "v1" else run_section_full

    for section in song.sections:
        if section.repeats:
            result = _reuse_repeated_section(section.name, section.repeats, results_by_name)
        elif room_version == "v1":
            result = run_section(
                client,
                section.source_text,
                dna,
                section.name,
                room_memory,
                song.target_language,
                section.voice,
            )
        else:
            # The full seven-agent room predates per-voice threading and
            # does not use it — say so rather than silently dropping data.
            if section.voice:
                logger.warning(
                    "Section %r sets voice=%r, but the full room does not "
                    "thread voice into its prompts — only the v1 room does.",
                    section.name,
                    section.voice,
                )
            result = run_section(
                client, section.source_text, dna, section.name, room_memory, song.target_language
            )

        section_results.append(result)
        results_by_name[section.name] = result
        room_memory.prior_rulings.append(result.ruling)
        # Prefer the Judge's own phrase-level motif renderings (the exact
        # wording used for each motif, which is what the Ambiguity Lock
        # needs); fall back to the whole final_line only when the ruling
        # didn't report renderings, preserving the old coarse behavior.
        reported = dict(result.ruling.motif_renderings)
        for motif in dna.motifs:
            if motif.motif in reported:
                room_memory.motif_decisions[motif.motif] = reported[motif.motif]
                continue
            touches_section = motif.first_occurrence == section.name or any(
                o.section == section.name for o in motif.occurrences
            )
            if touches_section and motif.motif not in room_memory.motif_decisions:
                room_memory.motif_decisions[motif.motif] = result.ruling.final_line

    return EngineResult(song, dna, section_results, room_version)
