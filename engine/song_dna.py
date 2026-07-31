"""Builds a SongDNA from a SongInput via one LLM call (docs/SONG_DNA.md)."""
from __future__ import annotations

from .llm_client import LLMClient
from .models import SongDNA, SongInput
from .prompts import song_dna_prompt


def generate_song_dna(song: SongInput, client: LLMClient) -> SongDNA:
    system, user = song_dna_prompt(song)
    data = client.complete_json(system, user, max_tokens=8000)
    return SongDNA.model_validate(data)
