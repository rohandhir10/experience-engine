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


def _content_max_tokens(
    source_text: str, num_outputs: int = 1, overhead_per_output: int = 250, floor: int = 1200
) -> int:
    """Scales an LLM call's max_tokens budget to the source section's
    length, instead of a flat constant that silently truncates long or
    highly repetitive sections. Found via a real production run: a
    qawwali refrain repeated ~14 times shipped a Japanese output that
    dropped ~95% of its content, including the entire sacred "Kun
    Fayakun" refrain - the flat max_tokens=4000 budget for 5 full
    candidates of a long section couldn't fit, and complete_json's
    retry-on-invalid-JSON mechanism quietly produced a shorter, still
    schema-valid response instead of raising anything.

    ~2 characters per token is a deliberately generous (i.e. token-heavy)
    estimate - roughly right for token-dense CJK output, safely oversized
    for Latin-script languages - since the failure mode being guarded
    against is truncation, not wasted budget.
    """
    chars = len(source_text)
    tokens_per_output = (chars // 2) + overhead_per_output
    return max(floor, tokens_per_output * num_outputs)


def _judge_max_tokens(source_text: str, num_candidates: int) -> int:
    """The Judge's output scales with both the source section's length
    (final_line must be able to carry as much content as the source) and
    the number of candidates it reasons about — more candidates means
    more Burden of Change ledger entries and dimension-score references,
    on top of the final_line's own content budget.
    """
    return _content_max_tokens(
        source_text,
        num_outputs=1,
        overhead_per_output=300 + 200 * max(1, num_candidates),
        floor=2048,
    )


def _ruling_with_retry(
    client: LLMClient,
    system: str,
    user: str,
    ruling_data: dict,
    section_name: str,
    max_tokens: int = 3000,
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
        retry_data = client.complete_json(
            system, corrective_user, max_tokens=max_tokens, stage="judge_schema_retry"
        )
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
    data = client.complete_json(
        system,
        user,
        max_tokens=_content_max_tokens(source_text, num_outputs=1, overhead_per_output=150),
        stage="translator",
    )
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
    data = client.complete_json(
        system,
        user,
        max_tokens=_content_max_tokens(source_text, num_outputs=5, overhead_per_output=200),
        stage="creative_adapter",
    )
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
    data = client.complete_json(system, user, stage=f"specialist_{agent}")
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
    emphasis_markup: bool = False,
) -> SectionResultV1:
    candidates, compensations = _generate(
        client, source_text, dna, section_name, room_memory, target_language, voice, profile
    )
    return judge_candidates(
        client,
        candidates,
        compensations,
        source_text,
        dna,
        section_name,
        room_memory,
        target_language,
        voice,
        profile,
        emphasis_markup,
    )


def judge_candidates(
    client: LLMClient,
    candidates: list[Candidate],
    compensations: list[Compensation],
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str = "English",
    voice: str | None = None,
    profile: LanguageProfile = NEUTRAL_PROFILE,
    emphasis_markup: bool = False,
) -> SectionResultV1:
    """The triage/specialist/final-ruling half of run_section, taking an
    already-built candidate pool instead of generating one itself.
    Factored out so engine/pipeline.py can re-judge a FRESH candidate
    pool (regenerate_creative_adapter_candidates below) without
    duplicating the triage/specialist/ruling logic — the specific path
    needed when every existing candidate already dropped a source
    repeat and re-judging the same pool (retry_section_with_finding)
    cannot recover it.

    `emphasis_markup`, comics-only (engine/comics_adapt.py passes True;
    every song call site leaves it False), tells the Judge it may wrap a
    word/short phrase in **double asterisks** within final_line to mark
    real vocal stress for a letterer to render bold - see prompts.py's
    _EMPHASIS_INSTRUCTION for the actual instruction text. False keeps
    every existing prompt byte-identical.
    """
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
        emphasis_markup,
    )
    judge_tokens = _judge_max_tokens(source_text, len(candidates))
    triage_data = client.complete_json(
        system, user, max_tokens=judge_tokens, stage="judge_triage"
    )

    specialists_invoked: list[str] = []
    specialist_critiques: list[Critique] = []

    ready = bool(triage_data.get("ready_to_rule"))
    if ready and triage_data.get("ruling"):
        ruling = _ruling_with_retry(
            client, system, user, triage_data["ruling"], section_name, max_tokens=judge_tokens
        )
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
            emphasis_markup,
        )
        final_data = client.complete_json(
            system, user, max_tokens=judge_tokens, stage="judge_final"
        )
        ruling = _ruling_with_retry(
            client, system, user, final_data, section_name, max_tokens=judge_tokens
        )

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
    emphasis_markup: bool = False,
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

    `emphasis_markup` - see judge_candidates' docstring.
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
        emphasis_markup,
    )
    corrective_user = (
        user
        + "\n\nA deterministic post-hoc check (engine/verify.py) found a "
        "problem with your PREVIOUS ruling for this section, described "
        "below — not a stylistic suggestion, a specific violation to fix. "
        "Produce a corrected ruling that resolves it without introducing a "
        "new violation elsewhere:\n\n" + finding_detail
    )
    judge_tokens = _judge_max_tokens(source_text, len(result.candidates))
    data = client.complete_json(
        system, corrective_user, max_tokens=judge_tokens, stage="corrective_retry"
    )
    ruling = _ruling_with_retry(
        client, system, corrective_user, data, section_name, max_tokens=judge_tokens
    )
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


def regenerate_creative_adapter_candidates(
    client: LLMClient,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    feedback: str,
    target_language: str = "English",
    voice: str | None = None,
    profile: LanguageProfile = NEUTRAL_PROFILE,
) -> list[Candidate]:
    """Re-runs ONLY the Creative Adapter's generation call, with explicit
    corrective feedback appended, for the one failure
    retry_section_with_finding cannot fix: every one of the existing 5
    candidates already dropped a repeat the source has, so re-judging
    the same pool (engine/verify.py::repeated_lines_preserved on each
    candidate all coming back False) can only choose among already-
    flawed options. The Translator is deliberately NOT re-run here — its
    anchor already preserves repeats correctly (generation_prompt_v1's
    own repetition instruction), so the problem is isolated to the
    Creative Adapter's candidates.

    Returns a fresh set of 5 candidates only; the caller (engine/
    pipeline.py) combines these with the existing Translator candidate
    and re-judges the combined pool via judge_candidates. Bounded to
    exactly one regeneration call per flagged section by the caller,
    same discipline as retry_section_with_finding.
    """
    system, user = prompts.creative_adapter_prompt(
        source_text, dna, section_name, room_memory, target_language, voice, profile
    )
    corrective_user = (
        user
        + "\n\nA deterministic post-hoc check (engine/verify.py) found that "
        "EVERY candidate from your previous attempt dropped a repeat the "
        "source actually has — not a stylistic note, a specific violation "
        "of constraint #7 above:\n\n"
        + feedback
        + "\n\nProduce a fresh set of 5 candidates that all preserve this "
        "repeat at the source's own count. This is not a request for more "
        "variety — every one of the 5 must fix this specific failure, not "
        "just one or two of them."
    )
    data = client.complete_json(
        system,
        corrective_user,
        max_tokens=_content_max_tokens(source_text, num_outputs=5, overhead_per_output=200),
        stage="creative_adapter_regeneration",
    )
    candidates: list[Candidate] = []
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
                syllable_count=count_syllables_text(candidate_text)
                if target_language == "English"
                else None,
            )
        )
    return candidates
