"""Typed data structures for Song DNA and the Writers' Room, mirroring
docs/SONG_DNA.md and docs/WRITERS_ROOM.md. These are the plain-Python
objects every stage of the engine passes to the next: the model never
produces these classes directly, each stage parses the model's JSON reply
into one of these and validates it against the schema.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


class SectionInput(BaseModel):
    name: str
    source_text: str
    # If set, this section is an exact (or near-exact) repeat of an earlier
    # section's text — e.g. a chorus that recurs verbatim later in the song.
    # The engine reuses that earlier section's final ruling directly instead
    # of re-running the whole room, at zero extra LLM cost, so a song's full
    # repeated structure can be represented without wasting calls re-judging
    # identical text.
    repeats: str | None = None


class SongInput(BaseModel):
    title: str | None = None
    source_language: str
    # Locked to "English" in the current product — see engine/prompts.py and
    # docs/WRITERS_ROOM_V1.md §10. Threaded through the whole pipeline as a
    # real field (not a hardcoded string) purely for architectural
    # readiness: swapping this later should not require another prompt
    # redesign, just a different value here.
    target_language: str = "English"
    context_note: str | None = None
    sections: list[SectionInput]


# ---------------------------------------------------------------------------
# Song DNA  (docs/SONG_DNA.md)
# ---------------------------------------------------------------------------


class EmotionalArcPoint(BaseModel):
    section: str
    valence: float
    intensity: float
    dominant_feeling: str


class TurnPoint(BaseModel):
    section: str
    cause: str


class ImageryItem(BaseModel):
    section: str
    image: str
    sensory_channel: str
    stands_in_for: str


class MotifOccurrence(BaseModel):
    section: str
    how_meaning_shifted: str


class Motif(BaseModel):
    motif: str
    first_occurrence: str
    occurrences: list[MotifOccurrence] = Field(default_factory=list)
    resolves_or_breaks_at_end: str | None = None


class AmbiguityItem(BaseModel):
    section: str
    ambiguous_element: str
    competing_readings: list[str]
    is_the_ambiguity_the_point: bool


class SymbolItem(BaseModel):
    model_config = {"populate_by_name": True}

    section: str
    symbol: str
    concrete_form: str
    symbolic_meaning: str
    symbol_register: Literal[
        "archetypal", "culturally_specific", "invented_for_this_song"
    ] = Field(alias="register")


class VulnerabilityItem(BaseModel):
    section: str
    what_is_admitted: str
    directness: Literal[
        "stated_plainly",
        "deflected_through_humor",
        "buried_in_imagery",
        "undercut_by_irony",
    ]
    felt_cost: str


class RhythmNote(BaseModel):
    section: str
    line: str | None = None
    scansion_note: str
    rhythmic_function: str


class RepetitionPattern(BaseModel):
    repeated_element: str
    occurrences: int
    exact_or_varied: str
    craft_function: str


class NarrativeFunctionItem(BaseModel):
    section: str
    function: str
    relation_to_adjacent: str


class DensityItem(BaseModel):
    section: str
    density: Literal["sparse", "moderate", "dense"]
    note: str


class StyleProfile(BaseModel):
    diction_register: str
    rhyme_type: str
    syntax_tendency: str
    signature_devices: list[str] = Field(default_factory=list)


class SectionProfile(BaseModel):
    """Per-section slice of every dimension, for one named section."""

    name: str
    narrative_function: NarrativeFunctionItem
    density: DensityItem
    emotional_arc_point: EmotionalArcPoint
    imagery: list[ImageryItem] = Field(default_factory=list)
    vulnerability: list[VulnerabilityItem] = Field(default_factory=list)
    rhythm: list[RhythmNote] = Field(default_factory=list)


class SongDNA(BaseModel):
    artistic_thesis: str
    genre_feel: str
    arc_shape: str
    songwriter_intention: str
    turn_points: list[TurnPoint] = Field(default_factory=list)
    sections: list[SectionProfile]
    motifs: list[Motif] = Field(default_factory=list)
    ambiguities: list[AmbiguityItem] = Field(default_factory=list)
    symbols: list[SymbolItem] = Field(default_factory=list)
    repetition_patterns: list[RepetitionPattern] = Field(default_factory=list)
    style: StyleProfile

    def section(self, name: str) -> SectionProfile:
        for s in self.sections:
            if s.name == name:
                return s
        raise KeyError(f"No SectionProfile named {name!r} in this SongDNA")


# ---------------------------------------------------------------------------
# Writers' Room  (docs/WRITERS_ROOM.md)
# ---------------------------------------------------------------------------

GENERATIVE_AGENTS = ("translator", "poet", "songwriter")
DIAGNOSTIC_AGENTS = ("native_speaker", "cultural_historian", "film_critic", "psychologist")

# V1 minimal room (docs/WRITERS_ROOM_V1.md)
V1_GENERATIVE_AGENTS = ("translator", "creative_adapter")
SPECIALIST_AGENTS = ("cultural_historian", "native_speaker", "psychologist")

# The five adaptation philosophies the Creative Adapter produces one
# candidate for (docs/WRITERS_ROOM_V1.md §9, "Burden of Change" redesign).
# Every philosophy is still bound by the deviation ledger — they differ in
# which fidelity-compatible dimension they prioritize, never in how much
# license to invent they get.
ADAPTATION_PHILOSOPHIES = (
    "maximum_fidelity",
    "native_english_lyricist",
    "performance_first",
    "emotion_first",
    "genre_first",
)


class Candidate(BaseModel):
    id: str
    agent: str
    text: str
    leans_into: str = ""  # which part of the emotional core this candidate emphasizes
    round: Literal["generation", "recombination"]
    # V1 routing inputs (docs/WRITERS_ROOM_V1.md §3) — unused by the full room,
    # default to "confident" so full-room Candidates need no changes.
    confidence: float = 1.0
    uncertainty_type: Literal["cultural", "authenticity", "emotional", "none"] = "none"
    # Which of the five adaptation philosophies this candidate embodies
    # (creative_adapter only; empty for the Translator's literal anchor).
    philosophy: str = ""
    # Deterministic syllable count (engine/rhythm.py), computed in code, not
    # by the model — grounds "Singability & Rhythm" in an actual number
    # instead of the Judge's unverified opinion. None if not computed
    # (e.g. the full room, which doesn't wire this in).
    syllable_count: int | None = None


class Critique(BaseModel):
    candidate_id: str
    agent: str
    verdict: Literal["strong", "workable", "fails"]
    strength: str
    failure: str
    suggested_fix: str | None = None


class Rebuttal(BaseModel):
    responding_agent: str
    target_agent: str
    about_candidate_id: str | None = None
    text: str


class Deviation(BaseModel):
    """One fragment of the winning candidate that differs from the
    Translator's literal anchor, and the burden-of-proof justification for
    letting it stand (docs/WRITERS_ROOM_V1.md §9, "Burden of Change").

    An unjustified deviation is not supposed to exist in a final ruling —
    the Judge is instructed to revert any fragment it cannot justify back
    to the literal wording before shipping final_line. This list is the
    audit trail proving that discipline was actually followed, fragment by
    fragment, rather than a holistic "this all seems fine" judgment.
    """

    fragment_original: str  # the Translator's literal wording for this fragment
    fragment_adapted: str  # what final_line actually says instead
    justification: str
    dimension: Literal[
        "artistic_fidelity",
        "genre_authenticity",
        "natural_english",
        "voice_consistency",
        "singability_rhythm",
    ]


class DimensionScore(BaseModel):
    """One of the five scored dimensions (docs/WRITERS_ROOM_V1.md §9),
    applied to the winning candidate. Literal Accuracy and Authenticity are
    gates (vetoes), not scored here — everything in this list is a real,
    comparative judgment among candidates that already cleared the gates.
    """

    dimension: Literal[
        "artistic_fidelity",
        "genre_authenticity",
        "natural_english",
        "voice_consistency",
        "singability_rhythm",
    ]
    score: float  # 0-1
    note: str


class JudgeRuling(BaseModel):
    section: str
    final_line: str
    sources_used: list[dict[str, str]] = Field(default_factory=list)
    vetoes_applied: list[str] = Field(default_factory=list)
    priority_tradeoffs_made: str
    disagreements_overruled: list[dict[str, str]] = Field(default_factory=list)
    # V1 only — which specialists (if any) the Judge actually invoked.
    specialists_invoked: list[str] = Field(default_factory=list)
    # Burden-of-Change ledger (docs/WRITERS_ROOM_V1.md §9) — replaces the
    # old holistic fidelity_checks/violations_found with a per-fragment
    # audit: every deviation from the literal anchor, and why it earned
    # its existence.
    deviations: list[Deviation] = Field(default_factory=list)
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    # Aggregate 0-1 measure of how much unjustified/borderline invention
    # showed up across the candidates the Judge reviewed (not just the
    # winner) — 0 means no invention risk was found anywhere; higher means
    # more of the deviation ledger leaned on weak or borderline
    # justifications. Separate from per-deviation justifications so a
    # human reviewer has one number to scan before reading the ledger.
    invention_penalty: float = 0.0


class SectionResult(BaseModel):
    section: str
    candidates_round1: list[Candidate]
    critiques: list[Critique]
    rebuttals: list[Rebuttal]
    candidates_round4: list[Candidate]
    ruling: JudgeRuling


class RoutingSignals(BaseModel):
    """Free routing signals for the V1 room (docs/WRITERS_ROOM_V1.md §3) —
    computed from Song DNA and candidate self-reports, at zero extra LLM cost.
    Handed to the Judge as input to its triage decision, never as an
    automatic trigger.
    """

    culturally_specific_symbol_count: int = 0
    deliberate_ambiguity_present: bool = False
    guarded_vulnerability_present: bool = False
    low_confidence_agents: list[str] = Field(default_factory=list)
    suggested_specialists: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)

    def summary_for_prompt(self) -> str:
        if not self.reasons:
            return (
                "No routing signals fired — Song DNA shows no flagged cultural/"
                "ambiguity/vulnerability load for this section, and both "
                "candidates reported adequate confidence."
            )
        lines = ["Signals that fired:"] + [f"- {r}" for r in self.reasons]
        lines.append(
            "Suggested specialists (not binding — you decide): "
            + (", ".join(self.suggested_specialists) or "none")
        )
        return "\n".join(lines)


class SectionResultV1(BaseModel):
    """Result of running the V1 minimal room (docs/WRITERS_ROOM_V1.md) on
    one section — no recombination round, no cross-critique transcript,
    just the two candidates, whatever routing signals fired, whichever
    specialists the Judge actually invoked, and the final ruling.
    """

    section: str
    candidates: list[Candidate]
    routing_signals: RoutingSignals
    specialists_invoked: list[str] = Field(default_factory=list)
    specialist_critiques: list[Critique] = Field(default_factory=list)
    ruling: JudgeRuling


class RoomMemory(BaseModel):
    """Carried forward across sections of the same song (docs/WRITERS_ROOM.md §8)."""

    motif_decisions: dict[str, str] = Field(default_factory=dict)
    prior_rulings: list[JudgeRuling] = Field(default_factory=list)

    def summary_for_prompt(self) -> str:
        if not self.prior_rulings:
            return "No prior sections yet — this is the first section of the song."
        lines = ["Decisions already made earlier in this song:"]
        for r in self.prior_rulings:
            lines.append(
                f'- [{r.section}] final line: "{r.final_line}" — {r.priority_tradeoffs_made}'
            )
        if self.motif_decisions:
            lines.append("Motif renderings established so far:")
            for motif, rendering in self.motif_decisions.items():
                lines.append(f"- {motif}: {rendering}")
        return "\n".join(lines)
