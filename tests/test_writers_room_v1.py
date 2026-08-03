"""Verifies the V1 minimal room (docs/WRITERS_ROOM_V1.md): the routing
signals are pure functions tested with no LLM at all, and the pipeline is
tested against a fake client for both the "Judge rules immediately" path
(3 calls) and the "Judge requests a specialist" path (extra calls).
"""
from __future__ import annotations

import re

from engine.models import Candidate, SectionInput, SongInput
from engine.pipeline import run_engine
from engine.routing import compute_routing_signals
from engine.writers_room_v1 import _content_max_tokens, _judge_max_tokens

from .test_pipeline_mock import FAKE_SONG_DNA
from engine.models import SongDNA

DNA = SongDNA.model_validate(FAKE_SONG_DNA)


# ---------------------------------------------------------------------------
# Token budget scaling — pure functions, zero LLM calls
# ---------------------------------------------------------------------------


def test_content_max_tokens_grows_with_source_length():
    short = _content_max_tokens("a short line", num_outputs=1)
    long = _content_max_tokens("a much longer source line " * 200, num_outputs=1)
    assert long > short


def test_content_max_tokens_scales_with_num_outputs():
    source = "a line of source text " * 50
    one = _content_max_tokens(source, num_outputs=1)
    five = _content_max_tokens(source, num_outputs=5)
    assert five > one


def test_content_max_tokens_never_drops_below_floor():
    assert _content_max_tokens("", num_outputs=1, floor=1200) == 1200


def test_judge_max_tokens_grows_with_candidate_count():
    source = "a line of source text " * 50
    few = _judge_max_tokens(source, num_candidates=2)
    many = _judge_max_tokens(source, num_candidates=6)
    assert many > few


def test_judge_max_tokens_grows_with_source_length():
    small = _judge_max_tokens("short", num_candidates=6)
    large = _judge_max_tokens("a long repetitive refrain " * 200, num_candidates=6)
    assert large > small


# ---------------------------------------------------------------------------
# Routing signals — pure logic, zero LLM calls
# ---------------------------------------------------------------------------


def test_routing_flags_culturally_specific_symbol():
    # FAKE_SONG_DNA's symbol register is "invented_for_this_song", not
    # "culturally_specific" — so no cultural signal should fire here.
    candidates = [
        Candidate(id="a", agent="translator", text="x", round="generation", confidence=1.0),
        Candidate(id="b", agent="creative_adapter", text="y", round="generation", confidence=1.0),
    ]
    signals = compute_routing_signals(DNA, "verse_1", candidates)
    assert signals.culturally_specific_symbol_count == 0
    assert "cultural_historian" not in signals.suggested_specialists


def test_routing_flags_guarded_vulnerability():
    # FAKE_SONG_DNA's verse_1 vulnerability directness is "buried_in_imagery"
    # — this should route to the psychologist.
    candidates = [
        Candidate(id="a", agent="translator", text="x", round="generation", confidence=1.0),
        Candidate(id="b", agent="creative_adapter", text="y", round="generation", confidence=1.0),
    ]
    signals = compute_routing_signals(DNA, "verse_1", candidates)
    assert signals.guarded_vulnerability_present is True
    assert "psychologist" in signals.suggested_specialists


def test_routing_flags_low_confidence_with_uncertainty_type():
    candidates = [
        Candidate(
            id="a",
            agent="translator",
            text="x",
            round="generation",
            confidence=0.4,
            uncertainty_type="cultural",
        ),
        Candidate(id="b", agent="creative_adapter", text="y", round="generation", confidence=0.9),
    ]
    signals = compute_routing_signals(DNA, "verse_1", candidates)
    assert "translator" in signals.low_confidence_agents
    assert "cultural_historian" in signals.suggested_specialists


def test_routing_fires_no_signals_when_everything_is_confident_and_clean():
    # Build a DNA with no guarded vulnerability, no cultural symbol, no
    # ambiguity, to confirm the "quiet" path produces zero suggestions.
    clean_dna_dict = {**FAKE_SONG_DNA, "symbols": [], "sections": [
        {**FAKE_SONG_DNA["sections"][0], "vulnerability": []}
    ]}
    clean_dna = SongDNA.model_validate(clean_dna_dict)
    candidates = [
        Candidate(id="a", agent="translator", text="x", round="generation", confidence=0.95),
        Candidate(id="b", agent="creative_adapter", text="y", round="generation", confidence=0.9),
    ]
    signals = compute_routing_signals(clean_dna, "verse_1", candidates)
    assert signals.suggested_specialists == []
    assert signals.reasons == []


# ---------------------------------------------------------------------------
# Full pipeline against a fake client
# ---------------------------------------------------------------------------

READY_LINE = "I keep the drawer locked, just like you kept your hurt."
SPECIALIST_LINE = "I keep the drawer locked — not grief, just a habit I won't break."


FIVE_PHILOSOPHY_CANDIDATES = [
    {
        "text": READY_LINE,
        "philosophy": "maximum_fidelity",
        "leans_into": "guarded attachment",
        "confidence": 0.9,
        "uncertainty_type": "none",
    },
    {
        "text": "I keep it locked, the way you'd write a songwriter's line.",
        "philosophy": "native_english_lyricist",
        "leans_into": "guarded attachment",
        "confidence": 0.85,
        "uncertainty_type": "none",
    },
    {
        "text": "The drawer stays locked. It always has.",
        "philosophy": "performance_first",
        "leans_into": "guarded attachment",
        "confidence": 0.85,
        "uncertainty_type": "none",
    },
    {
        "text": "Locked, still — the way you kept it.",
        "philosophy": "emotion_first",
        "leans_into": "guarded attachment",
        "confidence": 0.8,
        "uncertainty_type": "none",
    },
    {
        "text": "I keep the drawer locked, plain and simple.",
        "philosophy": "genre_first",
        "leans_into": "guarded attachment",
        "confidence": 0.8,
        "uncertainty_type": "none",
    },
]

DIMENSION_SCORES = [
    {"dimension": d, "score": 0.9, "note": "test"}
    for d in (
        "artistic_fidelity",
        "genre_authenticity",
        "natural_target_language",
        "voice_consistency",
        "singability_rhythm",
    )
]


class FakeClientRulesImmediately:
    """Judge always says ready_to_rule on its first (triage) call."""

    def __init__(self):
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append(system[:60])
        if "You are a songwriting analyst" in system:
            return FAKE_SONG_DNA
        if "You are the Creative Adapter" in system:
            return {"candidates": FIVE_PHILOSOPHY_CANDIDATES}
        if "uncertainty_type" in system:
            return {
                "text": READY_LINE,
                "leans_into": "guarded attachment",
                "confidence": 0.9,
                "uncertainty_type": "none",
            }
        if "running the minimal V1 room" in system:
            return {
                "ready_to_rule": True,
                "ruling": {
                    "final_line": READY_LINE,
                    "sources_used": [{"agent": "creative_adapter", "contribution": "phrasing"}],
                    "vetoes_applied": [],
                    "deviations": [],
                    "dimension_scores": DIMENSION_SCORES,
                    "priority_tradeoffs_made": "chose the maximum_fidelity candidate outright",
                    "disagreements_overruled": [],
                },
                "specialists_needed": [],
                "why": "no signals fired, no unjustified deviations found",
            }
        raise AssertionError(f"Unexpected prompt: {system[:80]!r}")


def test_v1_rules_immediately_with_three_calls():
    song = SongInput(
        source_language="English (test)",
        sections=[SectionInput(name="verse_1", source_text="line one")],
    )
    client = FakeClientRulesImmediately()

    result = run_engine(song, client=client, room_version="v1")

    section_result = result.section_results[0]
    # 1 translator + 5 creative_adapter candidates (one per philosophy).
    assert len(section_result.candidates) == 6
    assert section_result.specialists_invoked == []
    assert section_result.ruling.final_line == READY_LINE
    assert len(section_result.ruling.dimension_scores) == 5
    assert section_result.ruling.deviations == []
    # 1 song-dna call + 1 translator call + 1 creative_adapter call +
    # 1 judge-triage call = 4 total, regardless of candidate count.
    assert len(client.calls) == 4


class FakeClientNeedsSpecialist:
    """Judge requests the psychologist on triage, then rules on the second call."""

    def __init__(self):
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append(system[:60])
        if "You are a songwriting analyst" in system:
            return FAKE_SONG_DNA
        if "You are the Creative Adapter" in system:
            return {
                "candidates": [
                    {**c, "confidence": 0.5, "uncertainty_type": "emotional"}
                    for c in FIVE_PHILOSOPHY_CANDIDATES
                ]
            }
        if "uncertainty_type" in system:
            return {"text": READY_LINE, "leans_into": "guarded attachment", "confidence": 0.5, "uncertainty_type": "emotional"}
        if "running the minimal V1 room" in system:
            return {
                "ready_to_rule": False,
                "ruling": None,
                "specialists_needed": ["psychologist"],
                "why": "candidates disagree on how guarded the admission should read",
            }
        if "Comment ONLY from your own expertise" in system:
            ids = re.findall(r"\[(\w+)\]", user)
            return {
                "critiques": [
                    {
                        "candidate_id": cid,
                        "verdict": "workable",
                        "strength": "keeps the guardedness",
                        "failure": "slightly on the nose",
                        "suggested_fix": None,
                    }
                    for cid in ids
                ]
            }
        if "You previously requested specialist input" in system:
            return {
                "final_line": SPECIALIST_LINE,
                "sources_used": [{"agent": "psychologist", "contribution": "guardedness note"}],
                "vetoes_applied": [],
                "deviations": [
                    {
                        "fragment_original": "just like you kept your hurt",
                        "fragment_adapted": "just a habit I won't break",
                        "justification": "psychologist's read: the guardedness is a defense, not plain grief",
                        "dimension": "artistic_fidelity",
                    }
                ],
                "dimension_scores": DIMENSION_SCORES,
                "priority_tradeoffs_made": "favored the psychologist's read of defensive downplaying",
                "disagreements_overruled": [],
            }
        raise AssertionError(f"Unexpected prompt: {system[:80]!r}")


def test_v1_invokes_specialist_when_judge_requests_it():
    song = SongInput(
        source_language="English (test)",
        sections=[SectionInput(name="verse_1", source_text="line one")],
    )
    client = FakeClientNeedsSpecialist()

    result = run_engine(song, client=client, room_version="v1")

    section_result = result.section_results[0]
    assert section_result.specialists_invoked == ["psychologist"]
    # 1 translator + 5 creative_adapter candidates = 6, one critique each.
    assert len(section_result.candidates) == 6
    assert len(section_result.specialist_critiques) == 6
    assert section_result.ruling.final_line == SPECIALIST_LINE
    assert section_result.ruling.specialists_invoked == ["psychologist"]
    assert len(section_result.ruling.deviations) == 1
    assert section_result.ruling.deviations[0].dimension == "artistic_fidelity"
    assert len(section_result.ruling.dimension_scores) == 5
    # 1 song-dna + 1 translator + 1 creative_adapter + 1 triage + 1 specialist
    # + 1 final = 6 total, regardless of candidate count.
    assert len(client.calls) == 6
