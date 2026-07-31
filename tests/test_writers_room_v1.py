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

from .test_pipeline_mock import FAKE_SONG_DNA
from engine.models import SongDNA

DNA = SongDNA.model_validate(FAKE_SONG_DNA)


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


class FakeClientRulesImmediately:
    """Judge always says ready_to_rule on its first (triage) call."""

    def __init__(self):
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str, max_tokens=None) -> dict:
        self.calls.append(system[:60])
        if "You are a songwriting analyst" in system:
            return FAKE_SONG_DNA
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
                    "priority_tradeoffs_made": "chose the Creative Adapter's version outright",
                    "disagreements_overruled": [],
                },
                "specialists_needed": [],
                "why": "both candidates align, no signals fired",
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
    assert len(section_result.candidates) == 2  # translator, creative_adapter
    assert section_result.specialists_invoked == []
    assert section_result.ruling.final_line == READY_LINE
    # 1 song-dna call + 2 generation calls + 1 judge-triage call = 4 total.
    assert len(client.calls) == 4


class FakeClientNeedsSpecialist:
    """Judge requests the psychologist on triage, then rules on the second call."""

    def __init__(self):
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str, max_tokens=None) -> dict:
        self.calls.append(system[:60])
        if "You are a songwriting analyst" in system:
            return FAKE_SONG_DNA
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
    assert len(section_result.specialist_critiques) == 2  # one per candidate
    assert section_result.ruling.final_line == SPECIALIST_LINE
    assert section_result.ruling.specialists_invoked == ["psychologist"]
    # 1 song-dna + 2 generation + 1 triage + 1 specialist + 1 final = 6 total.
    assert len(client.calls) == 6
