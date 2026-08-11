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
A section may instead set `varies_from` when it's a NEAR-repeat (same
lines, a small number changed, e.g. a final chorus with one "lifted"
line) — the room still runs, but is given the earlier section's ruling as
an explicit consistency anchor (RoomMemory.variation_note) so the
unchanged lines come out worded the same way twice. Both are normally
auto-detected by engine/text_ingest.py::split_into_sections
(engine/recurrence.py::detect_section_repeats), not hand-set.
"""
from __future__ import annotations

import logging
import time
from typing import Callable, Literal

from .language_profile import LanguageProfile, resolve_profile
from .llm_client import LLMClient, create_default_client
from .models import RoomMemory, SectionInput, SectionResult, SectionResultV1, SongDNA, SongInput
from .recurrence import diff_line_indices
from .song_dna import generate_song_dna
from .verify import (
    Finding,
    VerificationReport,
    line_structure_preserved,
    repeated_lines_preserved,
    verify_result,
)
from .writers_room import run_section as run_section_full
from .writers_room_v1 import (
    judge_candidates,
    regenerate_creative_adapter_candidates,
    retry_section_with_finding,
)
from .writers_room_v1 import run_section as run_section_v1

# verify.py's law tag for a dropped source-side repeat (engine/
# verify.py::_check_repeated_line_preservation) — the one error class
# where re-judging the existing candidate pool may not be enough; see
# _all_creative_candidates_drop_a_repeat below.
_REPEATED_LINE_LAW = "Law 3 — Compression Floor (repetition)"

# verify.py's law tag for a section whose lyric lines were merged into
# running prose. The same tag is also used by two Compression Floor
# WARNINGS (function-word ratio, explanatory connectives), but only the
# line-collapse check raises it at error severity, and only errors reach
# the corrective pass — so among the findings routed here it is
# unambiguous. See _all_creative_candidates_collapse_structure below.
_LINE_COLLAPSE_LAW = "Law 3 — Compression Floor"

RoomVersion = Literal["v1", "full"]

logger = logging.getLogger(__name__)


class EngineTimeoutError(RuntimeError):
    """Raised by run_engine when `deadline` passes mid-song. A
    RuntimeError subclass so it's caught, reported to the caller, and
    (for the background job path) refunded by server/main.py's existing
    `except RuntimeError` handling in _run_job / _adapt_or_serve_cached -
    no new except clause needed there. Same idea as engine/comics_adapt.py's
    ChapterTimeoutError, for the song pipeline.
    """


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


def _variation_note(
    repeated_from: str,
    prior_source: str,
    current_source: str,
    prior_final_line: str,
) -> str:
    """Builds the RoomMemory.variation_note instruction for a section
    whose `varies_from` points at `repeated_from` — see SectionInput.
    varies_from's docstring for why this exists instead of just reusing
    the ruling outright the way `repeats` does.
    """
    diff = diff_line_indices(prior_source, current_source)
    current_lines = [line for line in current_source.splitlines() if line.strip()]
    if diff:
        changed_desc = "; ".join(
            f"line {i + 1} (now: {current_lines[i]!r})" for i in diff if i < len(current_lines)
        )
    else:
        # detect_section_repeats only ever sets varies_from when at least
        # one line differs, so this shouldn't happen from auto-detected
        # input - but a caller can build SongInput by hand, so stay
        # honest about the fallback rather than assume diff is non-empty.
        changed_desc = "the line(s) that differ from that section's source text"
    return (
        f"This section is a NEAR-repeat of section {repeated_from!r} — same "
        f"source lines except {changed_desc}. Section {repeated_from!r}'s "
        f'final adapted wording was: "{prior_final_line}". Keep every '
        "UNCHANGED line's wording IDENTICAL to that earlier ruling — this "
        "is consistency, not a re-adaptation of lines that already have a "
        "correct answer. Only the changed line(s) need genuine, fresh "
        "adaptation."
    )


def _extract_correctable_section_errors(report: VerificationReport) -> dict[str, list[Finding]]:
    """Maps section name -> verify.py Findings worth a corrective retry.
    Only severity=='error' findings are used, deliberately: warnings
    (Structural recurrence, the singability check, the connective-ratio
    signal) were designed with disclosed false-positive risk precisely so
    they would NOT auto-trigger a rewrite of a section that may well be
    fine — see their docstrings/comments in verify.py. Auto-retrying on a
    warning would reintroduce exactly the risk those checks were
    deliberately kept non-blocking to avoid. This scoping is a judgment
    call, not something measured.

    Returns the Finding objects themselves, not just their `.detail`
    text, so the caller can tell WHICH law fired (needed to route a
    dropped-repeat finding to regeneration instead of a plain re-judge —
    see _all_creative_candidates_drop_a_repeat below).
    """
    by_section: dict[str, list[Finding]] = {}
    for section in report.sections:
        for finding in section.errors:
            by_section.setdefault(section.section, []).append(finding)
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
            by_section.setdefault(later.strip(), []).append(finding)
    return by_section


def _all_creative_candidates_drop_a_repeat(result: SectionResultV1) -> bool:
    """True only when the Translator's anchor has a verbatim-repeated
    line/block that NONE of the Creative Adapter's own candidates
    preserved — the specific case retry_section_with_finding cannot fix,
    since it only ever re-judges the existing pool; if every option in
    that pool already dropped the repeat, no amount of re-judging can
    produce a ruling that keeps it.

    False (re-judging can still work) when the anchor has no repetition
    verify.py's check would flag in the first place, or when at least
    one Creative Adapter candidate already preserved it — meaning the
    Judge simply picked the wrong candidate, which retry_section_with_
    finding CAN fix by pointing it at a better existing option.
    """
    anchor = next((c.text for c in result.candidates if c.agent == "translator"), None)
    creative_candidates = [c for c in result.candidates if c.agent == "creative_adapter"]
    if not anchor or not creative_candidates:
        return False
    return all(not repeated_lines_preserved(anchor, c.text) for c in creative_candidates)


def _all_creative_candidates_collapse_structure(result: SectionResultV1) -> bool:
    """True only when the Translator's anchor is a multi-line lyric that
    NONE of the Creative Adapter's candidates kept the line structure of
    — every option in the pool already flattened the verse into running
    prose.

    Exactly the same escalation logic as _all_creative_candidates_drop_a_
    repeat above, for the other Compression Floor failure. Re-judging a
    pool in which every candidate is already prose cannot produce a
    ruling that isn't; the pool has to be regenerated with feedback.

    This matters because a source with short, repetitive, partly
    untranslatable lines is precisely the kind of text that tempts every
    candidate toward smooth English prose at once — the failure mode is
    correlated across candidates, not independent, so "some other
    candidate will be fine" is not a safe assumption.
    """
    anchor = next((c.text for c in result.candidates if c.agent == "translator"), None)
    creative_candidates = [c for c in result.candidates if c.agent == "creative_adapter"]
    if not anchor or not creative_candidates:
        return False
    return all(not line_structure_preserved(anchor, c.text) for c in creative_candidates)


def _regenerate_and_rejudge_section(
    client: LLMClient,
    original: SectionResultV1,
    section_input: SectionInput,
    dna: SongDNA,
    room_memory: RoomMemory,
    feedback: str,
    target_language: str,
    profile: LanguageProfile,
) -> SectionResultV1:
    """The escalation retry_section_with_finding cannot perform: keeps the
    Translator's own anchor (already correct — generation_prompt_v1's own
    repetition instruction), gets a genuinely fresh set of Creative
    Adapter candidates with explicit feedback about what was dropped
    (writers_room_v1.regenerate_creative_adapter_candidates), then
    re-judges the combined pool from scratch (writers_room_v1.
    judge_candidates) rather than re-judging the stale, already-flawed
    one. Bounded to exactly one regeneration + one re-judge per flagged
    section by the caller (_apply_corrective_pass), same discipline as
    the plain re-judge path.
    """
    translator_candidate = next(c for c in original.candidates if c.agent == "translator")
    fresh_creative_candidates = regenerate_creative_adapter_candidates(
        client,
        section_input.source_text,
        dna,
        original.section,
        room_memory,
        feedback,
        target_language,
        section_input.voice,
        profile,
    )
    new_candidates = [translator_candidate] + fresh_creative_candidates
    return judge_candidates(
        client,
        new_candidates,
        original.compensations,
        section_input.source_text,
        dna,
        original.section,
        room_memory,
        target_language,
        section_input.voice,
        profile,
    )


def _apply_corrective_pass(
    result: "EngineResult",
    client: LLMClient,
    room_memory: RoomMemory,
) -> "EngineResult":
    """One bounded corrective pass: verify the finished song, and for
    every error-severity finding that names a single correctable section,
    fix just that section. Two routes, chosen per section:

      - The usual case: re-judge the section with the finding as
        corrective context (writers_room_v1.retry_section_with_finding).
        This covers most error findings, which are almost always about
        the RULING (an uncovered deviation, a fabricated ledger entry) —
        the candidates themselves are fine, the Judge's pick wasn't.
      - The escalation: when the finding is a dropped source repeat
        AND every existing Creative Adapter candidate already dropped it
        (_all_creative_candidates_drop_a_repeat), re-judging the same
        pool cannot recover the repeat — there is nothing left to pick
        that has it. _regenerate_and_rejudge_section gets a fresh
        candidate pool with explicit feedback instead.

    Runs at most once — it does not loop and does not re-verify its own
    output, so anything a correction fails to fully resolve, or newly
    introduces, is left for the next explicit `--verify` run to surface
    to a human rather than being silently retried again. That cap is
    deliberate: an uncapped loop risks oscillation (a fix reintroducing a
    different violation) with no guaranteed termination.
    """
    report = verify_result(result.to_dict())
    correctable = _extract_correctable_section_errors(report)
    if not correctable:
        return result

    profile = resolve_profile(result.song.source_language_code, result.song.source_language)
    sections_by_name = {s.name: s for s in result.song.sections}
    results_by_name = {r.section: r for r in result.section_results}

    for section_name, findings in correctable.items():
        if section_name not in sections_by_name or section_name not in results_by_name:
            continue
        section_input = sections_by_name[section_name]
        original = results_by_name[section_name]
        finding_text = "\n".join(f"- {f.detail}" for f in findings)

        # Two failures where the whole candidate pool can already be
        # unsalvageable, so re-judging it is guaranteed not to help: a
        # dropped source repeat, and a verse flattened into prose.
        dropped_repeat = any(f.law == _REPEATED_LINE_LAW for f in findings)
        collapsed = any(f.law == _LINE_COLLAPSE_LAW for f in findings)
        needs_fresh_candidates = (
            dropped_repeat and _all_creative_candidates_drop_a_repeat(original)
        ) or (collapsed and _all_creative_candidates_collapse_structure(original))

        if needs_fresh_candidates:
            logger.warning(
                "Corrective pass: every Creative Adapter candidate for %r "
                "already lost the structure the finding is about - "
                "regenerating a fresh candidate pool with feedback instead "
                "of re-judging the stale one.",
                section_name,
            )
            results_by_name[section_name] = _regenerate_and_rejudge_section(
                client,
                original,
                section_input,
                result.dna,
                room_memory,
                finding_text,
                result.song.target_language,
                profile,
            )
        else:
            logger.warning(
                "Corrective pass: re-judging %r for %d verify.py error(s).",
                section_name,
                len(findings),
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
    on_stage: Callable[[str, int, int], None] | None = None,
    on_section_done: Callable[[str, "SectionResult | SectionResultV1", int, int], None] | None = None,
    deadline: float | None = None,
) -> EngineResult:
    """`on_stage(section_name, index, total)` fires right before a
    section starts (index is 1-based) and `on_section_done(section_name,
    result, index, total)` right after it finishes - real, already-
    happening progress, the song-side equivalent of engine/
    comics_adapt.py::adapt_chapter's on_stage/on_bubble_done. Unlike that
    function, there is only one stage reported per section here (no
    separate "verifying" step in this loop) - a v1-room section already
    runs Translator -> Creative Adapter -> Judge as one `run_section`
    call, and per-song verification/correction happens once, after this
    whole loop, via `apply_corrective_pass` below, not interleaved
    section by section. A repeated section (`section.repeats`) still
    fires both callbacks despite doing no LLM call - it's real, instant
    progress, not a call worth hiding from a poller. Neither callback
    changes this function's behavior or return value when omitted.

    `deadline` (a time.monotonic() cutoff, not a duration) is an overall
    safety ceiling for the whole song, checked between sections - not a
    replacement for engine/llm_client.py's per-call timeout, which
    already bounds any single stuck request. This covers what that
    doesn't: sustained rate-limiting whose per-call retries each
    individually succeed but whose delays add up past a reasonable total
    for the whole song. Raises EngineTimeoutError; None (the default)
    means no ceiling.
    """
    client = client or create_default_client()
    # Resolved once per song. Neutral (pre-V2 behavior) unless the song
    # names a language with a profile — docs/MULTILINGUAL_V2.md §7.
    profile = resolve_profile(song.source_language_code, song.source_language)
    dna = generate_song_dna(song, client, profile)
    room_memory = RoomMemory()
    section_results: list[SectionResult | SectionResultV1] = []
    results_by_name: dict[str, SectionResult | SectionResultV1] = {}
    sections_by_name: dict[str, SectionInput] = {s.name: s for s in song.sections}

    run_section = run_section_v1 if room_version == "v1" else run_section_full
    total = len(song.sections)

    for index, section in enumerate(song.sections, start=1):
        if deadline is not None and time.monotonic() > deadline:
            raise EngineTimeoutError(
                f"This song is taking longer than the configured time limit "
                f"({index - 1}/{total} sections finished). Try again, or with fewer sections."
            )
        if on_stage:
            on_stage(section.name, index, total)
        if section.repeats:
            result = _reuse_repeated_section(section.name, section.repeats, results_by_name)
        else:
            # A `varies_from` section still runs the room (unlike
            # `repeats`, which skips it entirely) - it just gets an extra,
            # transient instruction telling it which earlier section this
            # nearly repeats, cleared again right after so it doesn't leak
            # into later sections that have nothing to do with it.
            if section.varies_from:
                if section.varies_from not in results_by_name:
                    raise ValueError(
                        f"Section {section.name!r} sets varies_from={section.varies_from!r}, "
                        f"but {section.varies_from!r} hasn't been processed yet — "
                        "varies_from must reference an earlier section in the song."
                    )
                room_memory.variation_note = _variation_note(
                    section.varies_from,
                    sections_by_name[section.varies_from].source_text,
                    section.source_text,
                    results_by_name[section.varies_from].ruling.final_line,
                )
            try:
                if room_version == "v1":
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
                    # The full seven-agent room predates per-voice
                    # threading and does not use it — say so rather than
                    # silently dropping data.
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
            finally:
                room_memory.variation_note = None

        section_results.append(result)
        results_by_name[section.name] = result
        if on_section_done:
            on_section_done(section.name, result, index, total)
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
