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
"""
from __future__ import annotations

from typing import Literal

from .llm_client import LLMClient
from .models import RoomMemory, SectionResult, SectionResultV1, SongDNA, SongInput
from .song_dna import generate_song_dna
from .writers_room import run_section as run_section_full
from .writers_room_v1 import run_section as run_section_v1

RoomVersion = Literal["v1", "full"]


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


def run_engine(
    song: SongInput,
    client: LLMClient | None = None,
    room_version: RoomVersion = "v1",
) -> EngineResult:
    client = client or LLMClient()
    dna = generate_song_dna(song, client)
    room_memory = RoomMemory()
    section_results: list[SectionResult | SectionResultV1] = []

    run_section = run_section_v1 if room_version == "v1" else run_section_full

    for section in song.sections:
        result = run_section(client, section.source_text, dna, section.name, room_memory)
        section_results.append(result)
        room_memory.prior_rulings.append(result.ruling)
        for motif in dna.motifs:
            touches_section = motif.first_occurrence == section.name or any(
                o.section == section.name for o in motif.occurrences
            )
            if touches_section:
                room_memory.motif_decisions[motif.motif] = result.ruling.final_line

    return EngineResult(song, dna, section_results, room_version)
