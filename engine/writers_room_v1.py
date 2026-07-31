"""Runs the V1 minimal Writers' Room (docs/WRITERS_ROOM_V1.md) for one
section: Translator and Creative Adapter generate, the Judge triages using
free routing signals plus its own read of the two candidates, and only the
specialists the Judge actually asks for are invoked before a final ruling.

Best case: 3 LLM calls (2 generate + 1 judge-rules-immediately).
Worst case: ~6-7 calls (2 generate + 1 judge-triage + up to 3 specialists +
1 judge-final).
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
    V1_GENERATIVE_AGENTS,
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
) -> list[Candidate]:
    candidates = []
    for agent in V1_GENERATIVE_AGENTS:
        system, user = prompts.generation_prompt_v1(
            agent, source_text, dna, section_name, room_memory
        )
        data = client.complete_json(system, user)
        candidates.append(
            Candidate(
                id=_new_id(),
                agent=agent,
                text=data["text"],
                leans_into=data.get("leans_into", ""),
                confidence=float(data.get("confidence", 1.0)),
                uncertainty_type=data.get("uncertainty_type", "none"),
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
) -> list[Critique]:
    system, user = prompts.diagnosis_prompt(agent, candidates, source_text, dna, section_name)
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
) -> SectionResultV1:
    candidates = _generate(client, source_text, dna, section_name, room_memory)
    routing_signals = compute_routing_signals(dna, section_name, candidates)

    system, user = prompts.judge_triage_prompt(
        candidates, routing_signals, source_text, dna, section_name, room_memory
    )
    triage_data = client.complete_json(system, user, max_tokens=2000)

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
                _consult_specialist(client, agent, candidates, source_text, dna, section_name)
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
        )
        final_data = client.complete_json(system, user, max_tokens=2000)
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
