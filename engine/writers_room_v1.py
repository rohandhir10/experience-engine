"""Runs the V1 minimal Writers' Room (docs/WRITERS_ROOM_V1.md) for one
section: Translator produces one literal-anchor candidate, Creative Adapter
produces exactly 5 candidates - one per adaptation philosophy (§9, "Burden
of Change") - the Judge triages using free routing signals plus its own
burden-of-change read of all of them, and only the specialists the Judge
actually asks for are invoked before a final ruling.

Best case: 3 LLM calls (2 generate + 1 judge-rules-immediately).
Worst case: ~6-7 calls (2 generate + 1 judge-triage + up to 3 specialists +
1 judge-final) — the call count doesn't change with candidate count, since
Creative Adapter still returns all 5 candidates from a single call.
"""
from __future__ import annotations

import uuid

from . import prompts
from .llm_client import LLMClient
from .models import (
    Candidate,
    Critique,
    JudgeRuling,
    RoomMemory,
    SectionResultV1,
    SPECIALIST_AGENTS,
    SongDNA,
)
from .routing import compute_routing_signals


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _generate(
    client: LLMClient,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str,
) -> list[Candidate]:
    candidates: list[Candidate] = []

    system, user = prompts.generation_prompt_v1(
        "translator", source_text, dna, section_name, room_memory, target_language
    )
    data = client.complete_json(system, user)
    candidates.append(
        Candidate(
            id=_new_id(),
            agent="translator",
            text=data["text"],
            leans_into=data.get("leans_into", ""),
            confidence=float(data.get("confidence", 1.0)),
            uncertainty_type=data.get("uncertainty_type", "none"),
            round="generation",
        )
    )

    system, user = prompts.creative_adapter_prompt(
        source_text, dna, section_name, room_memory, target_language
    )
    data = client.complete_json(system, user, max_tokens=4000)
    for item in data.get("candidates", []):
        candidates.append(
            Candidate(
                id=_new_id(),
                agent="creative_adapter",
                text=item["text"],
                leans_into=item.get("leans_into", ""),
                confidence=float(item.get("confidence", 1.0)),
                uncertainty_type=item.get("uncertainty_type", "none"),
                philosophy=item.get("philosophy", ""),
                round="generation",
            )
        )
    return candidates


def _consult_specialist(
    client: LLMClient,
    agent: str,
    candidates: list[Candidate],
    source_text: str,
    dna: SongDNA,
    section_name: str,
    target_language: str,
) -> list[Critique]:
    system, user = prompts.diagnosis_prompt(
        agent, candidates, source_text, dna, section_name, target_language
    )
    data = client.complete_json(system, user)
    return [
        Critique(
            candidate_id=item["candidate_id"],
            agent=agent,
            verdict=item["verdict"],
            strength=item.get("strength", ""),
            failure=item.get("failure", ""),
            suggested_fix=item.get("suggested_fix"),
        )
        for item in data.get("critiques", [])
    ]


def run_section(
    client: LLMClient,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str = "English",
) -> SectionResultV1:
    candidates = _generate(client, source_text, dna, section_name, room_memory, target_language)
    routing_signals = compute_routing_signals(dna, section_name, candidates)

    system, user = prompts.judge_triage_prompt(
        candidates, routing_signals, source_text, dna, section_name, room_memory, target_language
    )
    triage_data = client.complete_json(system, user, max_tokens=3000)

    specialists_invoked: list[str] = []
    specialist_critiques: list[Critique] = []

    if triage_data.get("ready_to_rule") and triage_data.get("ruling"):
        ruling = JudgeRuling(section=section_name, **triage_data["ruling"])
    else:
        requested = [
            a for a in triage_data.get("specialists_needed", []) if a in SPECIALIST_AGENTS
        ]
        for agent in requested:
            specialist_critiques.extend(
                _consult_specialist(
                    client, agent, candidates, source_text, dna, section_name, target_language
                )
            )
            specialists_invoked.append(agent)

        system, user = prompts.judge_final_prompt(
            candidates,
            specialist_critiques,
            routing_signals,
            source_text,
            dna,
            section_name,
            room_memory,
            target_language,
        )
        final_data = client.complete_json(system, user, max_tokens=3000)
        ruling = JudgeRuling(section=section_name, **final_data)

    ruling.specialists_invoked = specialists_invoked

    return SectionResultV1(
        section=section_name,
        candidates=candidates,
        routing_signals=routing_signals,
        specialists_invoked=specialists_invoked,
        specialist_critiques=specialist_critiques,
        ruling=ruling,
    )
