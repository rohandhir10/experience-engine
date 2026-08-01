"""Turns a raw block of pasted lyrics into SectionInput objects.

The frontend's homepage is deliberately a single textarea with no
structure fields (docs — the "one input, one button" product decision) —
whoever pastes a song doesn't name their verses and choruses. This module
is the thin, heuristic bridge from that raw paste into what the engine
actually requires: a list of named sections.

The heuristic is intentionally simple and stated plainly, same spirit as
youtube_ingest.py's timing-gap guess: a blank line is treated as a section
break. This will sometimes be wrong (a verse a user pasted without a blank
line before its chorus stays one section) - there is no attempt here to
detect real verse/chorus structure from the text itself.
"""
from __future__ import annotations

import re

from .models import SectionInput

_BLANK_LINE_RE = re.compile(r"\n\s*\n+")


def split_into_sections(text: str) -> list[SectionInput]:
    """Splits on blank lines into SectionInput objects named section_1,
    section_2, ... Raises ValueError if the text has no non-empty content.
    """
    blocks = [b.strip() for b in _BLANK_LINE_RE.split(text.strip()) if b.strip()]
    if not blocks:
        raise ValueError("No non-empty lyric text found.")
    return [
        SectionInput(name=f"section_{i + 1}", source_text=block)
        for i, block in enumerate(blocks)
    ]
