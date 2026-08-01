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

import logging
import uuid

from pydantic import ValidationError

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
from .rhythm import count_syllables_text, source_syllable_estimate
from .routing import compute_routing_signals


logger = logging.getLogger(__name__)


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


def _ruling_with_retry(
    client: LLMClient,
    system: str,
    user: str,
    ruling_data: dict,
    section_name: str,
) -> JudgeRuling:
    """Parses a ruling dict, retrying the call once with a corrective
    message if validation fails. The Judge occasionally invents a label
    outside a closed enum (it has happened in production: the old
    violation_type enum crashed on "modified_original") — the enums are
    worth keeping as quality gates, so convert that crash into one guided
    retry instead of relaxing the schema.
    """
    try:
        return JudgeRuling(section=section_name, **ruling_data)
    except ValidationError as exc:
        logger.warning(
            "Ruling for %s failed schema validation, retrying once: %s",
            section_name,
            exc,
        )
        corrective_user = (
            user
            + "\n\nYour previous ruling did not validate against the required "
            f"schema. The specific errors were:\n{exc}\n\n"
            "Reply again with ONLY the corrected JSON object, using ONLY the "
            "exact field names and enum values the schema specifies."
        )
        retry_data = client.complete_json(system, corrective_user, max_tokens=3000)
        ruling = retry_data.get("ruling") if isinstance(retry_data.get("ruling"), dict) else retry_data
        return JudgeRuling(section=section_name, **ruling)


def _generate(
    client: LLMClient,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str,
    voice: str | None = None,
) -> list[Candidate]:
    candidates: list[Candidate] = []

    system, user = prompts.generation_prompt_v1(
        "translator", source_text, dna, section_name, room_memory, target_language, voice
    )
    data = client.complete_json(system, user)
    translator_text = data["text"]
    candidates.append(
        Candidate(
            id=_new_id(),
            agent="translator",
            text=translator_text,
            leans_into=data.get("leans_into", ""),
            confidence=float(data.get("confidence", 1.0)),
            uncertainty_type=data.get("uncertainty_type", "none"),
            round="generation",
            syllable_count=count_syllables_text(translator_text) if target_language == "English" else None,
        )
    )

    system, user = prompts.creative_adapter_prompt(
        source_text, dna, section_name, room_memory, target_language, voice
    )
    data = client.complete_json(system, user, max_tokens=4000)
    for item in data.get("candidates", []):
        candidate_text = item["text"]
        candidates.append(
            Candidate(
                id=_new_id(),
                agent="creative_adapter",
                text=candidate_text,
                leans_into=item.get("leans_into", ""),
                confidence=float(item.get("confidence", 1.0)),
                uncertainty_type=item.get("uncertainty_type", "none"),
                philosophy=item.get("philosophy", ""),
                round="generation",
                syllable_count=count_syllables_text(candidate_text) if target_language == "English" else None,
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
    voice: str | None = None,
) -> SectionResultV1:
    candidates = _generate(
        client, source_text, dna, section_name, room_memory, target_language, voice
    )
    routing_signals = compute_routing_signals(dna, section_name, candidates)
    source_syllables = source_syllable_estimate(source_text)

    system, user = prompts.judge_triage_prompt(
        candidates,
        routing_signals,
        source_text,
        dna,
        section_name,
        room_memory,
        target_language,
        source_syllables,
        voice,
    )
    triage_data = client.complete_json(system, user, max_tokens=3000)

    specialists_invoked: list[str] = []
    specialist_critiques: list[Critique] = []

    ready = bool(triage_data.get("ready_to_rule"))
    if ready and triage_data.get("ruling"):
        ruling = _ruling_with_retry(client, system, user, triage_data["ruling"], section_name)
    else:
        if ready:
            # The Judge said it was ready but the ruling was missing/empty —
            # falling through to the specialist path costs up to 4 extra LLM
            # calls, so never let that happen silently.
            logger.warning(
                "Judge set ready_to_rule for %s but supplied no usable ruling; "
                "falling back to the specialist path (extra cost).",
                section_name,
            )
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
            source_syllables,
            voice,
        )
        final_data = client.complete_json(system, user, max_tokens=3000)
        ruling = _ruling_with_retry(client, system, user, final_data, section_name)

    ruling.specialists_invoked = specialists_invoked
    ruling.voice = voice

    return SectionResultV1(
        section=section_name,
        candidates=candidates,
        routing_signals=routing_signals,
        specialists_invoked=specialists_invoked,
        specialist_critiques=specialist_critiques,
        ruling=ruling,
    )
