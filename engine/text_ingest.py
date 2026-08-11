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

This IS, however, the one real place a repeated chorus gets recognized as
one: engine/recurrence.py's detect_section_repeats runs over the split
blocks and marks a later block that matches an earlier one (exactly, or
with a small number of lines changed) via SectionInput.repeats/
varies_from - see engine/pipeline.py for what the engine does with that.
Before this existed, `repeats`/`varies_from` were real fields with real
engine-side handling that no real user's song ever actually set (only
test fixtures did) - a verbatim chorus re-ran the whole Writers' Room
from scratch every time it recurred, with no guarantee it came out
worded the same way twice.
"""
from __future__ import annotations

import re

from .models import SectionInput
from .recurrence import detect_section_repeats

_BLANK_LINE_RE = re.compile(r"\n\s*\n+")


def split_into_sections(text: str) -> list[SectionInput]:
    """Splits on blank lines into SectionInput objects named section_1,
    section_2, ... Raises ValueError if the text has no non-empty content.
    """
    blocks = [b.strip() for b in _BLANK_LINE_RE.split(text.strip()) if b.strip()]
    if not blocks:
        raise ValueError("No non-empty lyric text found.")
    names = [f"section_{i + 1}" for i in range(len(blocks))]
    repeats = detect_section_repeats(list(zip(names, blocks)))
    sections = []
    for name, block in zip(names, blocks):
        match = repeats.get(name)
        sections.append(
            SectionInput(
                name=name,
                source_text=block,
                repeats=match.repeats_from if match and match.kind == "exact" else None,
                varies_from=match.repeats_from if match and match.kind == "variant" else None,
            )
        )
    return sections
