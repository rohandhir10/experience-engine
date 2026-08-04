"""Phase 2: the bounded, single-pass corrective retry
(engine.pipeline._apply_corrective_pass / writers_room_v1.retry_section_with_finding).

A fake client stands in for the LLM throughout — no real API calls. The
scenario: the Judge ships a rewrite with an empty deviation ledger (a real
Law 1 violation, unaudited change), verify.py catches it, and the
corrective pass re-judges just that section with the finding as context.
The fake client's response to the corrective retry ships a proper ledger
entry, so the retried result should clear the violation the first pass had.
"""
from __future__ import annotations

from engine.models import SectionInput, SongInput
from engine.pipeline import _extract_correctable_section_errors, run_engine
from engine.verify import Finding, SectionVerification, VerificationReport, verify_result

from .test_pipeline_mock import FAKE_SONG_DNA
from .test_writers_room_v1 import DIMENSION_SCORES, FIVE_PHILOSOPHY_CANDIDATES

ANCHOR_LINE = "I keep the drawer locked, just like you kept your hurt."
UNAUDITED_LINE = "The drawer stays shut, and I never open it."
CORRECTED_LINE = "The drawer stays shut — a habit, not a wound, I keep in place."


class FakeClientShipsUnauditedRewrite:
    """First pass: Judge rules immediately with a rewritten final_line but
    an EMPTY deviation ledger — a real, unaudited Law 1 violation. The
    corrective retry (same system prompt as any judge_final_prompt call,
    "You previously requested specialist input") ships a version with the
    change properly logged.
    """

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
                "text": ANCHOR_LINE,
                "leans_into": "guarded attachment",
                "confidence": 0.9,
                "uncertainty_type": "none",
            }
        if "You previously requested specialist input" in system:
            # The corrective pass's re-judge call.
            return {
                "final_line": CORRECTED_LINE,
                "sources_used": [],
                "vetoes_applied": [],
                "deviations": [
                    {
                        "fragment_original": ANCHOR_LINE,
                        "fragment_adapted": CORRECTED_LINE,
                        "justification": (
                            "verify.py flagged the previous rewrite as "
                            "unaudited; logging it here as a genre-authentic "
                            "rephrasing of the same guardedness."
                        ),
                        "dimension": "artistic_fidelity",
                    }
                ],
                "dimension_scores": DIMENSION_SCORES,
                "priority_tradeoffs_made": "corrected to log the previously-unaudited change",
                "disagreements_overruled": [],
            }
        if "running the minimal V1 room" in system:
            return {
                "ready_to_rule": True,
                "ruling": {
                    "final_line": UNAUDITED_LINE,
                    "sources_used": [],
                    "vetoes_applied": [],
                    "deviations": [],  # empty — the bug under test
                    "dimension_scores": DIMENSION_SCORES,
                    "priority_tradeoffs_made": "rewrote without logging (fixture)",
                    "disagreements_overruled": [],
                },
                "specialists_needed": [],
                "why": "test fixture: ships an unaudited rewrite",
            }
        raise AssertionError(f"Unexpected prompt: {system[:80]!r}")


def _make_song() -> SongInput:
    return SongInput(
        source_language="English (test)",
        sections=[SectionInput(name="verse_1", source_text="line one")],
    )


def test_without_the_flag_the_unaudited_rewrite_ships_uncorrected():
    client = FakeClientShipsUnauditedRewrite()
    result = run_engine(_make_song(), client=client, room_version="v1")
    assert result.section_results[0].ruling.final_line == UNAUDITED_LINE

    report = verify_result(result.to_dict())
    assert not report.passed
    assert any(
        f.law == "Law 1 — No Invention" for f in report.sections[0].errors
    )


def test_corrective_pass_fixes_the_flagged_section():
    client = FakeClientShipsUnauditedRewrite()
    result = run_engine(
        _make_song(), client=client, room_version="v1", apply_corrective_pass=True
    )
    assert result.section_results[0].ruling.final_line == CORRECTED_LINE

    report = verify_result(result.to_dict())
    assert report.passed
    assert report.sections[0].errors == []


def test_corrective_pass_is_a_bounded_single_retry_not_a_loop():
    """Exactly one extra call for the one flagged section — not zero
    (it must actually fire) and not more than one (it must not loop).
    """
    client = FakeClientShipsUnauditedRewrite()
    run_engine(_make_song(), client=client, room_version="v1", apply_corrective_pass=False)
    baseline_calls = len(client.calls)

    client2 = FakeClientShipsUnauditedRewrite()
    run_engine(_make_song(), client=client2, room_version="v1", apply_corrective_pass=True)
    assert len(client2.calls) == baseline_calls + 1


def test_clean_run_triggers_no_corrective_calls():
    """A section with no error-severity finding must not be re-judged —
    the corrective pass should be a true no-op when nothing is broken.
    """
    from .test_writers_room_v1 import FakeClientRulesImmediately

    client = FakeClientRulesImmediately()
    run_engine(_make_song(), client=client, room_version="v1", apply_corrective_pass=False)
    baseline_calls = len(client.calls)

    client2 = FakeClientRulesImmediately()
    run_engine(_make_song(), client=client2, room_version="v1", apply_corrective_pass=True)
    assert len(client2.calls) == baseline_calls  # no extra retry call


def test_full_room_skips_the_corrective_pass_rather_than_crashing():
    """apply_corrective_pass relies on v1-only fields (source_syllable_count,
    the v1 SectionResultV1 shape) — requesting it on the full room must
    degrade gracefully (identical output to apply_corrective_pass=False,
    just a logged warning), not crash.
    """
    from .test_pipeline_mock import FakeLLMClient

    song = SongInput(
        title="Test Song",
        source_language="English (test)",
        sections=[SectionInput(name="verse_1", source_text="line one")],
    )
    without_flag = run_engine(song, client=FakeLLMClient(), room_version="full")
    with_flag = run_engine(
        song, client=FakeLLMClient(), room_version="full", apply_corrective_pass=True
    )
    assert (
        with_flag.section_results[0].ruling.final_line
        == without_flag.section_results[0].ruling.final_line
    )


def test_extract_correctable_errors_maps_section_findings():
    report = VerificationReport(
        sections=[
            SectionVerification(
                section="verse_1",
                findings=[
                    Finding(
                        law="Law 1 — No Invention",
                        severity="error",
                        section="verse_1",
                        detail="unaudited change",
                    ),
                    Finding(
                        law="Singability check",
                        severity="warning",
                        section="verse_1",
                        detail="a warning, must be excluded",
                    ),
                ],
                ledger_coverage=0.0,
                computed_invention_penalty=0.5,
                reported_invention_penalty=0.0,
                changed_word_count=3,
            )
        ],
        cross_section_findings=[
            Finding(
                law="Law 5 — Ambiguity Lock",
                severity="error",
                section="verse_1 vs chorus",
                detail="inconsistent motif rendering",
            ),
            Finding(
                law="Structural recurrence",
                severity="warning",
                section="sher_3",
                detail="a warning, must be excluded",
            ),
        ],
    )
    correctable = _extract_correctable_section_errors(report)
    assert [f.detail for f in correctable["verse_1"]] == ["unaudited change"]
    assert [f.detail for f in correctable["chorus"]] == ["inconsistent motif rendering"]
    assert "sher_3" not in correctable
