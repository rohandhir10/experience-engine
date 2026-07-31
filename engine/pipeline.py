"""Runs the whole engine end to end for one song: Song DNA once, then the
Writers' Room section by section, carrying room memory forward
(docs/WRITERS_ROOM.md §8).
"""
from __future__ import annotations

from .llm_client import LLMClient
from .models import RoomMemory, SectionResult, SongDNA, SongInput
from .song_dna import generate_song_dna
from .writers_room import run_section


class EngineResult:
    def __init__(
        self, song: SongInput, dna: SongDNA, section_results: list[SectionResult]
    ):
        self.song = song
        self.dna = dna
        self.section_results = section_results

    def final_lyrics(self) -> str:
        return "\n\n".join(
            f"[{r.section}]\n{r.ruling.final_line}" for r in self.section_results
        )

    def to_dict(self) -> dict:
        return {
            "title": self.song.title,
            "source_language": self.song.source_language,
            "song_dna": self.dna.model_dump(by_alias=True),
            "sections": [r.model_dump() for r in self.section_results],
            "final_lyrics": self.final_lyrics(),
        }


def run_engine(song: SongInput, client: LLMClient | None = None) -> EngineResult:
    client = client or LLMClient()
    dna = generate_song_dna(song, client)
    room_memory = RoomMemory()
    section_results: list[SectionResult] = []

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

    return EngineResult(song, dna, section_results)
