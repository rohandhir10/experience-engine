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
from .language_profile import NEUTRAL_PROFILE, LanguageProfile
from .llm_client import LLMClient
from .models import (
    Candidate,
    Compensation,
    Critique,
    JudgeRuling,
    RoomMemory,
    SectionResultV1,
    SPECIALIST_AGENTS,
    SongDNA,
)
from .grounding import count_source_units
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
    profile: LanguageProfile = NEUTRAL_PROFILE,
) -> tuple[list[Candidate], list[Compensation]]:
    candidates: list[Candidate] = []

    system, user = prompts.generation_prompt_v1(
        "translator", source_text, dna, section_name, room_memory, target_language, voice,
        profile,
    )
    data = client.complete_json(system, user)
    translator_text = data["text"]
    # Things the source encodes that English has no channel for. Decided
    # once, here, then binding for the whole song via RoomMemory.
    compensations = [
        Compensation.model_validate(c) for c in data.get("compensations", [])
    ]
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
        source_text, dna, section_name, room_memory, target_language, voice, profile
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
    return candidates, compensations


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
    profile: LanguageProfile = NEUTRAL_PROFILE,
) -> SectionResultV1:
    candidates, compensations = _generate(
        client, source_text, dna, section_name, room_memory, target_language, voice, profile
    )
    routing_signals = compute_routing_signals(dna, section_name, candidates)
    # Per-language source grounding first (Devanagari, Hangul, ...);
    # fall back to the Latin-script estimate. None stays None — the
    # engine never fabricates a count it cannot justify.
    grounded = count_source_units(source_text, profile.grounding_language_code)
    source_syllables = grounded.value if grounded else source_syllable_estimate(source_text)

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
        profile,
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
            profile,
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
        compensations=compensations,
        source_syllable_count=source_syllables,
    )


def retry_section_with_finding(
    client: LLMClient,
    result: SectionResultV1,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    finding_detail: str,
    target_language: str = "English",
    voice: str | None = None,
    profile: LanguageProfile = NEUTRAL_PROFILE,
) -> SectionResultV1:
    """Re-runs only the Judge step for one already-ruled section, informed
    by a specific verify.py finding, and returns a new SectionResultV1 with
    the same candidates/specialists but a corrected ruling.

    Deliberately narrow: verify.py's error-severity findings are almost
    always about the RULING (an uncovered deviation, a fabricated ledger
    entry, a broken motif/anchor/compensation rendering) rather than about
    the candidates themselves, so re-judging the existing candidates is
    the right-sized fix — regenerating the Translator/Creative Adapter
    candidates too would cost more and address a problem that likely
    isn't theirs. Bounded to exactly one call per flagged section by the
    caller (engine/pipeline.py); this function does not loop, retry
    itself, or re-verify — that discipline lives in the caller.
    """
    system, user = prompts.judge_final_prompt(
        result.candidates,
        result.specialist_critiques,
        result.routing_signals,
        source_text,
        dna,
        section_name,
        room_memory,
        target_language,
        result.source_syllable_count,
        voice,
        profile,
    )
    corrective_user = (
        user
        + "\n\nA deterministic post-hoc check (engine/verify.py) found a "
        "problem with your PREVIOUS ruling for this section, described "
        "below — not a stylistic suggestion, a specific violation to fix. "
        "Produce a corrected ruling that resolves it without introducing a "
        "new violation elsewhere:\n\n" + finding_detail
    )
    data = client.complete_json(system, corrective_user, max_tokens=3000)
    ruling = _ruling_with_retry(client, system, corrective_user, data, section_name)
    ruling.specialists_invoked = result.specialists_invoked
    ruling.voice = voice

    return SectionResultV1(
        section=section_name,
        candidates=result.candidates,
        routing_signals=result.routing_signals,
        specialists_invoked=result.specialists_invoked,
        specialist_critiques=result.specialist_critiques,
        ruling=ruling,
        compensations=result.compensations,
        source_syllable_count=result.source_syllable_count,
    )
