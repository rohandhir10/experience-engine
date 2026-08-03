"""Typed data structures for Song DNA and the Writers' Room, mirroring
docs/SONG_DNA.md and docs/WRITERS_ROOM.md. These are the plain-Python
objects every stage of the engine passes to the next: the model never
produces these classes directly, each stage parses the model's JSON reply
into one of these and validates it against the schema.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

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
    # Who is speaking/singing this section, when the work has more than one
    # voice (a duet, a dialogue). Voice consistency is judged WITHIN a
    # voice, not across different voices — before this field existed,
    # multi-voice works had to smuggle the speaker into the section name
    # (e.g. "verse_1_alka"), where the engine couldn't reason about it.
    # None means single-voice / unattributed, which changes nothing.
    voice: str | None = None


# AURA's supported language roster, for either side of a direction: the
# original 4 ("Hindi"/"Korean"/"Japanese"/"Spanish") + English, plus Urdu
# (added when direct, non-English-pivot pairs were opened up). Any two
# distinct languages from this set are a supported direction now (full
# matrix, not a curated allow-list) - server/main.py validates
# AdaptRequest.source_language/target_language against this set and
# rejects source == target.
#
# "Supported" here means the prompt layer will run and won't error - not
# that every pair has been quality-checked. engine/verify.py's CMU-
# dictionary-backed checks (rhythm, rhyme) only run when
# target_language == "English"; engine/language_profile.py's source-side
# profiles exist for Hindi/Korean/Japanese/Spanish only (Urdu and every
# non-English target fall back to the neutral profile, by design - see
# resolve_profile's docstring - not a crash, just less source-side
# craft-dimension support than the four original languages have).
SUPPORTED_LANGUAGES = frozenset(
    {"English", "Hindi", "Korean", "Japanese", "Spanish", "Urdu"}
)


class SongInput(BaseModel):
    title: str | None = None
    source_language: str
    # Real, product-scoped plumbing, not aspirational: see
    # SUPPORTED_LANGUAGES above.
    target_language: str = "English"
    # ISO-ish code selecting a Language Profile (engine/profiles/*.json) and
    # a source-side grounding counter (engine/grounding/). Optional: when
    # absent the engine falls back to matching `source_language`, and then
    # to the neutral profile, which reproduces pre-V2 behavior exactly.
    # docs/MULTILINGUAL_V2.md §7.
    source_language_code: str | None = None
    context_note: str | None = None
    sections: list[SectionInput]

    @model_validator(mode="after")
    def _validate_sections(self) -> "SongInput":
        """Section names are load-bearing free text: `repeats` references
        them, SongDNA.section() looks them up (first match wins), and room
        memory labels rulings by them. Duplicates silently alias instead of
        erroring, and a `repeats` pointing forward or at nothing crashes
        deep in the pipeline — so validate both here, at the boundary.
        """
        seen: set[str] = set()
        for section in self.sections:
            if not section.name.strip():
                raise ValueError("Every section needs a non-empty name.")
            if section.name in seen:
                raise ValueError(
                    f"Duplicate section name {section.name!r} — names must be "
                    "unique, they are how repeats/rulings/DNA reference sections."
                )
            if section.repeats is not None and section.repeats not in seen:
                raise ValueError(
                    f"Section {section.name!r} sets repeats={section.repeats!r}, "
                    "which must name an EARLIER section in this song."
                )
            seen.add(section.name)
        return self


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
    # The song's poetic/rhetorical register (sacred-devotional, street-
    # vernacular, melodramatic-romantic, playful, elegiac, defiant, etc.)
    # — a distinct axis from genre_feel (musical genre, e.g. "melancholic
    # pop ballad"). Extracted so the Creative Adapter can be told to find
    # the TARGET language's own equivalent tradition for this register
    # (Urdu Ghazal, Korean trot, Spanish copla, whatever it actually is),
    # rather than either flattening register entirely or importing the
    # source culture's specific references untranslated. Free text, not
    # an enum: registers this needs to name are genuinely open-ended, and
    # forcing a fixed vocabulary would eventually mis-classify a real song
    # into the nearest wrong bucket rather than describing it accurately.
    poetic_register: str
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
        "natural_target_language",
        "voice_consistency",
        "singability_rhythm",
    ]


class AnchorDecision(BaseModel):
    """What the Judge decided to do with a culturally dense term
    (docs/MULTILINGUAL_V2.md §6). Recorded so the decision is auditable
    and so verify.py can check it was applied identically at every
    recurrence — the same discipline Law 5 applies to motifs.
    """

    term: str
    disposition: Literal[
        "preserve",  # kept untranslated
        "preserve_with_gloss",  # kept, with a light in-line gloss
        "adapt",  # rendered with a target-language equivalent
        "translate_plainly",  # the density was incidental here
    ]
    rationale: str


class DimensionScore(BaseModel):
    """One of the five scored dimensions (docs/WRITERS_ROOM_V1.md §9),
    applied to the winning candidate. Literal Accuracy and Authenticity are
    gates (vetoes), not scored here — everything in this list is a real,
    comparative judgment among candidates that already cleared the gates.
    """

    dimension: Literal[
        "artistic_fidelity",
        "genre_authenticity",
        "natural_target_language",
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
    # The specific rendered wording for each motif this ruling touched
    # (motif -> the exact target-language phrase used). Without this, room
    # memory could only store the whole section's final_line per motif —
    # which made the Ambiguity Lock (constitution Law 5, "same source
    # phrase -> identical wording on every recurrence") unenforceable from
    # stored state.
    motif_renderings: dict[str, str] = Field(default_factory=dict)
    # Culturally dense terms this ruling had to decide about, and what it
    # decided (docs/MULTILINGUAL_V2.md §6). Empty for songs with none.
    cultural_anchors: list[AnchorDecision] = Field(default_factory=list)
    # Which voice (speaker/singer) delivered this section, copied from
    # SectionInput.voice so room-memory summaries can label prior rulings
    # per voice. None for single-voice works.
    voice: str | None = None


class SectionResult(BaseModel):
    section: str
    candidates_round1: list[Candidate]
    critiques: list[Critique]
    rebuttals: list[Rebuttal]
    candidates_round4: list[Candidate]
    ruling: JudgeRuling


class Compensation(BaseModel):
    """One thing the source language encodes that English has no channel
    for, and the channel English will use instead.

    This is *compensation* in the literary-translation sense: when a
    feature cannot be reproduced in place, reproduce its effect elsewhere.
    Japanese is the sharpest case — 僕 vs 俺 is a whole self-presentation
    carried by one pronoun, and English "I" has no way to hold it — but
    every language has some: Hindi's tu/tum/aap, Korean's speech levels,
    Spanish's tú/usted/vos.

    Two properties make this work rather than becoming licensed invention:

    1. **It is decided once and carried, not re-improvised per line.**
       These are persona facts, not line facts: a speaker who is 俺 is 俺
       for the whole song. The decision travels in RoomMemory, exactly as
       motif renderings do, and verify.py checks it stayed consistent.
    2. **Its carrier is diction, not addition.** The honest way to carry
       俺 is shorter words, no hedging, harder consonants — a register the
       whole line is written in. Bolting on an extra adjective to "convey
       bluntness" is invention, and the Restraint Ceiling will (rightly)
       flag it. A deviation made to serve a declared compensation is
       justified under `voice_consistency`, which is precisely what it is;
       it does not get a dimension of its own.
    """

    source_feature: str  # e.g. "first-person pronoun 俺 (ore)"
    what_it_encodes: str  # e.g. "blunt, assertive, masculine self-presentation"
    english_carrier: str  # e.g. "short Anglo-Saxon diction, no hedging, contractions"
    # Some features genuinely have no carrier — script choice is close to
    # unreproducible. Recording the loss is better than pretending.
    carried: bool = True


class LLMCallRecord(BaseModel):
    """One real API call, measured after the fact from the provider's own
    response — never estimated, never predicted before the call happens.
    This is the only source of truth for token/cost/latency accounting in
    the engine; nothing else should invent these numbers. See
    engine/llm_client.py::LLMClient.complete_json, which appends one of
    these per attempt (an initial call, plus one more if the JSON-repair
    retry fires) to `LLMClient.call_log`.
    """

    stage: str  # e.g. "song_dna", "translator", "creative_adapter",
    # "judge_triage", "judge_final", "specialist_native_speaker",
    # "corrective_retry" — matches the label passed at the call site.
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float
    attempt: Literal["initial", "json_repair_retry"] = "initial"


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
    # Untranslatable source encodings the Translator identified here. The
    # pipeline merges these into RoomMemory so the decision binds the rest
    # of the song, the same path motif renderings take.
    compensations: list[Compensation] = Field(default_factory=list)
    # The source-side count (engine/grounding, or the Latin-script estimate
    # as fallback) computed once at generation time and handed to the
    # Judge as prompt context. Persisted here too — without it, a stored
    # result has no way to check the Judge's singability_rhythm score
    # against anything after the fact; it existed only transiently at
    # generation time and was otherwise discarded. None means no count
    # could be computed (never a fabricated number).
    source_syllable_count: int | None = None


class RoomMemory(BaseModel):
    """Carried forward across sections of the same song (docs/WRITERS_ROOM.md §8)."""

    motif_decisions: dict[str, str] = Field(default_factory=dict)
    prior_rulings: list[JudgeRuling] = Field(default_factory=list)
    # Untranslatable source encodings and the English channel chosen to
    # carry each. Decided once, then binding for the rest of the song —
    # a speaker who is 俺 in verse 1 cannot become 僕 in the chorus.
    compensations: list[Compensation] = Field(default_factory=list)

    def summary_for_prompt(self) -> str:
        compensation_block = ""
        if self.compensations:
            entries = "\n".join(
                f"- {c.source_feature} encodes {c.what_it_encodes} — English "
                + (
                    f"carries it through: {c.english_carrier}"
                    if c.carried
                    else f"cannot carry it; accepted loss ({c.english_carrier})"
                )
                for c in self.compensations
            )
            compensation_block = (
                "\nThe source encodes these things English has no direct "
                "channel for. The carrier below was chosen earlier in this "
                "song and is now binding — write in that register rather "
                "than re-deciding, and do NOT bolt on extra words to signal "
                "it; the carrier is diction, not addition:\n" + entries + "\n"
            )

        if not self.prior_rulings:
            return (
                "No prior sections yet — this is the first section of the song."
                + compensation_block
            )
        lines = ["Decisions already made earlier in this song:"]
        for r in self.prior_rulings:
            label = f"{r.section} — voice: {r.voice}" if r.voice else r.section
            lines.append(
                f'- [{label}] final line: "{r.final_line}" — {r.priority_tradeoffs_made}'
            )
        if self.motif_decisions:
            lines.append("Motif renderings established so far:")
            for motif, rendering in self.motif_decisions.items():
                lines.append(f"- {motif}: {rendering}")
        return "\n".join(lines) + compensation_block
