"""Data shapes for the benchmark, independent of the engine's own models.

The benchmark deliberately has its own evaluation rubric (the four
dimensions below) rather than reusing the engine's five scored
dimensions — reviewers must judge outputs as listeners, not audit them
against AURA's internal criteria, or the rubric itself would bias the
comparison toward what AURA optimizes.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# What bilingual reviewers score, 1-5 each, per output.
DIMENSIONS = (
    "artistic_fidelity",
    "naturalness",
    "emotional_preservation",
    "readability",
)

DIMENSION_LABELS = {
    "artistic_fidelity": "Faithful to the original's artistry",
    "naturalness": "Reads like real English, not a translation",
    "emotional_preservation": "Carries the same feeling as the original",
    "readability": "Clear and easy to read",
}


class SystemOutput(BaseModel):
    """One system's adaptation of one song, normalized to plain text."""

    song_id: str
    system: str
    sections: list[str]  # normalized, ordered, no section labels

    def joined(self) -> str:
        return "\n\n".join(self.sections)


class BlindKeyEntry(BaseModel):
    """Secret mapping for one (reviewer, song, letter) -> system."""

    reviewer: str
    song_id: str
    letter: str
    system: str


class Rating(BaseModel):
    """One reviewer's scores for one blinded output of one song."""

    reviewer: str
    song_id: str
    letter: str
    scores: dict[str, int]  # dimension -> 1..5
    best_overall: bool = False


class ReviewerSubmission(BaseModel):
    """The JSON file a reviewer's browser downloads when they finish."""

    reviewer: str
    ratings: list[Rating] = Field(default_factory=list)
