"""Runs the Writers' Room (docs/WRITERS_ROOM.md) for one section at a time:

Round 1 — independent generation (Translator, Poet, Songwriter)
Round 2 — independent diagnosis (Native Speaker, Cultural Historian,
          Film Critic, Psychologist), each reviewing all Round 1 candidates
Round 3 — one-pass cross-critique and rebuttal, everyone sees everything
Round 4 — recombination pass, producing revised candidates
Round 5 — the Judge renders a final, auditable ruling

Independence (§4 of the design doc) is enforced by construction: Round 1
agents never see each other's output before generating, and Round 2 agents
never see each other's critiques before diagnosing — each is a separate,
isolated model call.
"""
from __future__ import annotations

import uuid

from . import prompts
from .llm_client import LLMClient
from .models import (
    Candidate,
    Critique,
    DIAGNOSTIC_AGENTS,
    GENERATIVE_AGENTS,
    JudgeRuling,
    Rebuttal,
    RoomMemory,
    SectionResult,
    SongDNA,
)


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _round1_generate(
    client: LLMClient,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
) -> list[Candidate]:
    candidates = []
    for agent in GENERATIVE_AGENTS:
        system, user = prompts.generation_prompt(
            agent, source_text, dna, section_name, room_memory
        )
        data = client.complete_json(system, user)
        candidates.append(
            Candidate(
                id=_new_id(),
                agent=agent,
                text=data["text"],
                leans_into=data.get("leans_into", ""),
                round="generation",
            )
        )
    return candidates


def _round2_diagnose(
    client: LLMClient,
    candidates: list[Candidate],
    source_text: str,
    dna: SongDNA,
    section_name: str,
) -> list[Critique]:
    critiques: list[Critique] = []
    for agent in DIAGNOSTIC_AGENTS:
        system, user = prompts.diagnosis_prompt(
            agent, candidates, source_text, dna, section_name
        )
        data = client.complete_json(system, user)
        for item in data.get("critiques", []):
            critiques.append(
                Critique(
                    candidate_id=item["candidate_id"],
                    agent=agent,
                    verdict=item["verdict"],
                    strength=item.get("strength", ""),
                    failure=item.get("failure", ""),
                    suggested_fix=item.get("suggested_fix"),
                )
            )
    return critiques


def _round3_cross_critique(
    client: LLMClient,
    candidates: list[Candidate],
    critiques: list[Critique],
    dna: SongDNA,
    section_name: str,
) -> list[Rebuttal]:
    rebuttals: list[Rebuttal] = []
    all_agents = list(GENERATIVE_AGENTS) + list(DIAGNOSTIC_AGENTS)
    for agent in all_agents:
        system, user = prompts.cross_critique_prompt(
            agent, candidates, critiques, dna, section_name
        )
        data = client.complete_json(system, user)
        for item in data.get("rebuttals", []):
            rebuttals.append(
                Rebuttal(
                    responding_agent=agent,
                    target_agent=item["target_agent"],
                    about_candidate_id=item.get("about_candidate_id"),
                    text=item.get("text", ""),
                )
            )
    return rebuttals


def _round4_recombine(
    client: LLMClient,
    candidates: list[Candidate],
    critiques: list[Critique],
    rebuttals: list[Rebuttal],
    source_text: str,
    dna: SongDNA,
    section_name: str,
) -> list[Candidate]:
    system, user = prompts.recombination_prompt(
        candidates, critiques, rebuttals, source_text, dna, section_name
    )
    data = client.complete_json(system, user)
    recombined = []
    for item in data.get("candidates", []):
        recombined.append(
            Candidate(
                id=_new_id(),
                agent="songwriter_recombination",
                text=item["text"],
                leans_into=item.get("leans_into", ""),
                round="recombination",
            )
        )
    return recombined


def _round5_judge(
    client: LLMClient,
    all_candidates: list[Candidate],
    critiques: list[Critique],
    rebuttals: list[Rebuttal],
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
) -> JudgeRuling:
    system, user = prompts.judge_prompt(
        all_candidates,
        critiques,
        rebuttals,
        source_text,
        dna,
        section_name,
        room_memory,
    )
    data = client.complete_json(system, user, max_tokens=2000)
    return JudgeRuling(section=section_name, **data)


def run_section(
    client: LLMClient,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
) -> SectionResult:
    round1 = _round1_generate(client, source_text, dna, section_name, room_memory)
    critiques = _round2_diagnose(client, round1, source_text, dna, section_name)
    rebuttals = _round3_cross_critique(client, round1, critiques, dna, section_name)
    round4 = _round4_recombine(
        client, round1, critiques, rebuttals, source_text, dna, section_name
    )
    ruling = _round5_judge(
        client,
        round1 + round4,
        critiques,
        rebuttals,
        source_text,
        dna,
        section_name,
        room_memory,
    )
    return SectionResult(
        section=section_name,
        candidates_round1=round1,
        critiques=critiques,
        rebuttals=rebuttals,
        candidates_round4=round4,
        ruling=ruling,
    )
