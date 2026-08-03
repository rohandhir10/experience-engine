"""Runs the whole engine end to end for one song: Song DNA once, then the
Writers' Room section by section, carrying room memory forward
(docs/WRITERS_ROOM.md §8 / docs/WRITERS_ROOM_V1.md).

Two room implementations are available:
  - "v1"   (default) — minimal room, docs/WRITERS_ROOM_V1.md. 3 agents by
            default (Translator, Creative Adapter, Judge), specialists
            invoked only when the Judge asks for them.
  - "full" — the original seven-agent room, docs/WRITERS_ROOM.md. Higher
            cost/latency, higher blanket-coverage ceiling; opt in for
            songs where that redundancy is worth paying for.

A section may set `repeats` to an earlier section's name (e.g. a chorus
that recurs verbatim later in the song) — its ruling is reused directly at
zero extra LLM cost instead of re-running the whole room on identical text.
"""
from __future__ import annotations

import logging
from typing import Literal

from .language_profile import resolve_profile
from .llm_client import LLMClient, create_default_client
from .models import RoomMemory, SectionResult, SectionResultV1, SongDNA, SongInput
from .song_dna import generate_song_dna
from .verify import VerificationReport, verify_result
from .writers_room import run_section as run_section_full
from .writers_room_v1 import retry_section_with_finding
from .writers_room_v1 import run_section as run_section_v1

RoomVersion = Literal["v1", "full"]

logger = logging.getLogger(__name__)


class EngineResult:
    def __init__(
        self,
        song: SongInput,
        dna: SongDNA,
        section_results: list[SectionResult | SectionResultV1],
        room_version: RoomVersion,
        call_log: list | None = None,
    ):
        self.song = song
        self.dna = dna
        self.section_results = section_results
        self.room_version = room_version
        # Measured, not estimated (engine/models.py::LLMCallRecord) — every
        # real API call made while producing this result, in order. None
        # only for a result built without a client in hand (shouldn't
        # happen via run_engine, but this class doesn't require one).
        self.call_log = call_log or []

    def final_lyrics(self) -> str:
        return "\n\n".join(
            f"[{r.section}]\n{r.ruling.final_line}" for r in self.section_results
        )

    def to_dict(self) -> dict:
        return {
            "title": self.song.title,
            "source_language": self.song.source_language,
            # Read by verify.py to gate the English-only rhythm/rhyme checks
            # (CMU-dictionary-backed - see engine/rhythm.py's module
            # docstring) - meaningless, or silently wrong, against shipped
            # text in any other language.
            "target_language": self.song.target_language,
            "room_version": self.room_version,
            "song_dna": self.dna.model_dump(by_alias=True),
            "sections": [r.model_dump() for r in self.section_results],
            # Original source text per section, kept alongside the
            # generated results so verify.py can run source-side checks
            # (engine/recurrence.py) that need the source language text —
            # nothing else in a stored result carries it.
            "source_sections": [
                {"name": s.name, "source_text": s.source_text} for s in self.song.sections
            ],
            "final_lyrics": self.final_lyrics(),
            # Real, measured cost/latency data for this run — see
            # engine/models.py::LLMCallRecord. One entry per actual API
            # call, in order; empty if this result was built without a
            # client that tracked one.
            "llm_calls": [record.model_dump() for record in self.call_log],
        }


def _reuse_repeated_section(
    section_name: str,
    repeated_from: str,
    results_by_name: dict[str, SectionResult | SectionResultV1],
) -> SectionResult | SectionResultV1:
    if repeated_from not in results_by_name:
        raise ValueError(
            f"Section {section_name!r} sets repeats={repeated_from!r}, but "
            f"{repeated_from!r} hasn't been processed yet — repeats must "
            "reference an earlier section in the song."
        )
    source_result = results_by_name[repeated_from]
    reused = source_result.model_copy(deep=True)
    reused.section = section_name
    reused.ruling.section = section_name
    return reused


def _extract_correctable_section_errors(report: VerificationReport) -> dict[str, list[str]]:
    """Maps section name -> verify.py finding details worth a corrective
    retry. Only severity=='error' findings are used, deliberately:
    warnings (Structural recurrence, the singability check, the
    connective-ratio signal) were designed with disclosed false-positive
    risk precisely so they would NOT auto-trigger a rewrite of a section
    that may well be fine — see their docstrings/comments in verify.py.
    Auto-retrying on a warning would reintroduce exactly the risk those
    checks were deliberately kept non-blocking to avoid. This scoping is a
    judgment call, not something measured.
    """
    by_section: dict[str, list[str]] = {}
    for section in report.sections:
        for finding in section.errors:
            by_section.setdefault(section.section, []).append(finding.detail)
    for finding in report.cross_section_findings:
        if finding.severity != "error":
            continue
        if " vs " in finding.section:
            # These findings (Ambiguity Lock, cultural-anchor/compensation
            # consistency) already treat the FIRST occurrence as the
            # binding decision and the later one as the thing that must
            # conform — the same forward-carry rule RoomMemory applies
            # everywhere else. Fix the later section, not the earlier one.
            _, later = finding.section.split(" vs ", 1)
            by_section.setdefault(later.strip(), []).append(finding.detail)
    return by_section


def _apply_corrective_pass(
    result: "EngineResult",
    client: LLMClient,
    room_memory: RoomMemory,
) -> "EngineResult":
    """One bounded corrective pass: verify the finished song, and for
    every error-severity finding that names a single correctable section,
    re-judge just that section with the finding as corrective context
    (writers_room_v1.retry_section_with_finding). Runs at most once — it
    does not loop and does not re-verify its own output, so anything a
    correction fails to fully resolve, or newly introduces, is left for
    the next explicit `--verify` run to surface to a human rather than
    being silently retried again. That cap is deliberate: an uncapped loop
    risks oscillation (a fix reintroducing a different violation) with no
    guaranteed termination.
    """
    report = verify_result(result.to_dict())
    correctable = _extract_correctable_section_errors(report)
    if not correctable:
        return result

    profile = resolve_profile(result.song.source_language_code, result.song.source_language)
    sections_by_name = {s.name: s for s in result.song.sections}
    results_by_name = {r.section: r for r in result.section_results}

    for section_name, details in correctable.items():
        if section_name not in sections_by_name or section_name not in results_by_name:
            continue
        section_input = sections_by_name[section_name]
        original = results_by_name[section_name]
        finding_text = "\n".join(f"- {detail}" for detail in details)
        logger.warning(
            "Corrective pass: re-judging %r for %d verify.py error(s).",
            section_name,
            len(details),
        )
        results_by_name[section_name] = retry_section_with_finding(
            client,
            original,
            section_input.source_text,
            result.dna,
            section_name,
            room_memory,
            finding_text,
            result.song.target_language,
            section_input.voice,
            profile,
        )

    new_section_results = [results_by_name[r.section] for r in result.section_results]
    # Same client as the first pass, so its call_log already includes
    # every call made so far; the corrective retries above extend it
    # further before this line runs.
    return EngineResult(
        result.song,
        result.dna,
        new_section_results,
        result.room_version,
        getattr(client, "call_log", []),
    )


def run_engine(
    song: SongInput,
    client: LLMClient | None = None,
    room_version: RoomVersion = "v1",
    apply_corrective_pass: bool = False,
) -> EngineResult:
    client = client or create_default_client()
    # Resolved once per song. Neutral (pre-V2 behavior) unless the song
    # names a language with a profile — docs/MULTILINGUAL_V2.md §7.
    profile = resolve_profile(song.source_language_code, song.source_language)
    dna = generate_song_dna(song, client, profile)
    room_memory = RoomMemory()
    section_results: list[SectionResult | SectionResultV1] = []
    results_by_name: dict[str, SectionResult | SectionResultV1] = {}

    run_section = run_section_v1 if room_version == "v1" else run_section_full

    for section in song.sections:
        if section.repeats:
            result = _reuse_repeated_section(section.name, section.repeats, results_by_name)
        elif room_version == "v1":
            result = run_section(
                client,
                section.source_text,
                dna,
                section.name,
                room_memory,
                song.target_language,
                section.voice,
                profile,
            )
        else:
            # The full seven-agent room predates per-voice threading and
            # does not use it — say so rather than silently dropping data.
            if section.voice:
                logger.warning(
                    "Section %r sets voice=%r, but the full room does not "
                    "thread voice into its prompts — only the v1 room does.",
                    section.name,
                    section.voice,
                )
            result = run_section(
                client, section.source_text, dna, section.name, room_memory, song.target_language
            )

        section_results.append(result)
        results_by_name[section.name] = result
        room_memory.prior_rulings.append(result.ruling)
        # A compensation is decided once and binds the rest of the song —
        # the speaker's register cannot change between verses. First
        # declaration for a given source feature wins.
        known = {c.source_feature for c in room_memory.compensations}
        for compensation in getattr(result, "compensations", []):
            if compensation.source_feature not in known:
                room_memory.compensations.append(compensation)
                known.add(compensation.source_feature)
        # Prefer the Judge's own phrase-level motif renderings (the exact
        # wording used for each motif, which is what the Ambiguity Lock
        # needs); fall back to the whole final_line only when the ruling
        # didn't report renderings, preserving the old coarse behavior.
        reported = dict(result.ruling.motif_renderings)
        for motif in dna.motifs:
            if motif.motif in reported:
                room_memory.motif_decisions[motif.motif] = reported[motif.motif]
                continue
            touches_section = motif.first_occurrence == section.name or any(
                o.section == section.name for o in motif.occurrences
            )
            if touches_section and motif.motif not in room_memory.motif_decisions:
                room_memory.motif_decisions[motif.motif] = result.ruling.final_line

    engine_result = EngineResult(
        song, dna, section_results, room_version, getattr(client, "call_log", [])
    )
    if apply_corrective_pass:
        if room_version != "v1":
            logger.warning(
                "apply_corrective_pass=True is only supported for room_version="
                "'v1' — the full room's SectionResult has no "
                "source_syllable_count and predates this retry path. Skipping."
            )
        else:
            engine_result = _apply_corrective_pass(engine_result, client, room_memory)
    return engine_result
