"""Builds a ChapterDNA from a ChapterInput via one LLM call — the
comics-side equivalent of engine/song_dna.py, item #3 of the
chapter-level-context roadmap (docs/CAPABILITY_MATRIX.md).

Deliberately simpler than song_dna.py: ChapterDNA has no per-bubble
array to validate or backfill (unlike SongDNA.sections, which needs one
entry per input section) - this is a single chapter-wide read, not a
per-bubble breakdown. That granularity belongs to the actual adaptation
pass over each BubbleInput, a separate, later step (item #4) that
doesn't exist yet.

Known architectural bound, same one song_dna.py discloses: the whole
chapter is analyzed in ONE call. Fine for a typical chapter's worth of
dialogue; a very long chapter (many dozens of bubbles) risks the same
silent-degradation failure mode already documented for Song DNA - no
chunked analysis exists here either.
"""
from __future__ import annotations

from .llm_client import LLMClient
from .models import ChapterDNA, ChapterInput
from .prompts import chapter_dna_prompt


def generate_chapter_dna(chapter: ChapterInput, client: LLMClient) -> ChapterDNA:
    system, user = chapter_dna_prompt(chapter)
    data = client.complete_json(system, user, max_tokens=8000, stage="chapter_dna")
    return ChapterDNA.model_validate(data)
