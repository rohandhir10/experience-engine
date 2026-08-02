"""Tests for the deterministic constitution verifier. No LLM involved —
these construct rulings by hand and assert the verifier catches exactly
the failures the constitution names, and stays quiet when it should.
"""
from __future__ import annotations

from engine.models import (
    AnchorDecision,
    Candidate,
    Deviation,
    JudgeRuling,
    SectionResultV1,
)
from engine.verify import verify_result, verify_section

ANCHOR = "I keep the drawer locked and I never open it"


def _section(
    final_line: str,
    deviations: list[Deviation] | None = None,
    *,
    anchor: str = ANCHOR,
    with_anchor: bool = True,
    invention_penalty: float = 0.0,
    motif_renderings: dict[str, str] | None = None,
    cultural_anchors: list[AnchorDecision] | None = None,
    name: str = "verse_1",
) -> SectionResultV1:
    candidates = []
    if with_anchor:
        candidates.append(
            Candidate(id="a1", agent="translator", text=anchor, round="generation")
        )
    candidates.append(
        Candidate(
            id="c1",
            agent="creative_adapter",
            text=final_line,
            round="generation",
            philosophy="maximum_fidelity",
        )
    )
    return SectionResultV1(
        section=name,
        candidates=candidates,
        routing_signals={},
        ruling=JudgeRuling(
            section=name,
            final_line=final_line,
            priority_tradeoffs_made="test",
            deviations=deviations or [],
            invention_penalty=invention_penalty,
            motif_renderings=motif_renderings or {},
            cultural_anchors=cultural_anchors or [],
        ),
    )


def _laws(findings) -> set[str]:
    return {f.law for f in findings}


# ---------------------------------------------------------------------------
# The clean case must stay silent
# ---------------------------------------------------------------------------


def test_identical_line_is_fully_covered_and_clean():
    v = verify_section(_section(ANCHOR))
    assert v.ledger_coverage == 1.0
    assert v.changed_word_count == 0
    assert v.computed_invention_penalty == 0.0
    assert v.findings == []


def test_change_with_a_real_logged_justification_passes():
    final = "I keep the drawer shut and I never open it"
    v = verify_section(
        _section(
            final,
            [
                Deviation(
                    fragment_original="locked",
                    fragment_adapted="shut",
                    justification=(
                        "The source uses an everyday word here, and 'locked' "
                        "reads as more deliberate than the original register."
                    ),
                    dimension="natural_target_language",
                )
            ],
        )
    )
    assert v.ledger_coverage == 1.0
    assert v.errors == []


# ---------------------------------------------------------------------------
# Law 1 — unlogged change is unaudited change
# ---------------------------------------------------------------------------


def test_rewritten_line_with_empty_ledger_is_an_error():
    v = verify_section(_section("The drawer stays shut forever, silent and cold"))
    assert "Law 1 — No Invention" in _laws(v.errors)
    assert v.ledger_coverage < 0.5
    assert v.computed_invention_penalty > 0.3


def test_partially_logged_change_reports_the_uncovered_remainder():
    # Two changes ("locked"->"shut", "never"->"rarely"); only one logged.
    final = "I keep the drawer shut and I rarely open it"
    v = verify_section(
        _section(
            final,
            [
                Deviation(
                    fragment_original="locked",
                    fragment_adapted="shut",
                    justification="A specific and detailed reason that is long enough.",
                    dimension="natural_target_language",
                )
            ],
        )
    )
    assert v.changed_word_count == 2
    assert v.ledger_coverage == 0.5
    assert any("unlogged" in f.detail for f in v.findings)
    assert any(f.fragment == "rarely" for f in v.findings)


def test_computed_penalty_can_exceed_self_reported():
    # The Judge claims a clean run while having rewritten the line.
    v = verify_section(
        _section("Something entirely different was written here", invention_penalty=0.0)
    )
    assert v.reported_invention_penalty == 0.0
    assert v.computed_invention_penalty > v.reported_invention_penalty


# ---------------------------------------------------------------------------
# Ledger integrity — a fabricated audit trail is worse than none
# ---------------------------------------------------------------------------


def test_deviation_citing_text_not_in_final_line_is_an_error():
    v = verify_section(
        _section(
            ANCHOR,
            [
                Deviation(
                    fragment_original="locked",
                    fragment_adapted="hermetically sealed",
                    justification="A specific and detailed reason that is long enough.",
                    dimension="artistic_fidelity",
                )
            ],
        )
    )
    assert "ledger integrity" in _laws(v.errors)


def test_deviation_citing_anchor_text_that_does_not_exist_warns():
    final = "I keep the drawer locked and I never open it"
    v = verify_section(
        _section(
            final,
            [
                Deviation(
                    fragment_original="bolted the cupboard",
                    fragment_adapted="keep the drawer locked",
                    justification="A specific and detailed reason that is long enough.",
                    dimension="artistic_fidelity",
                )
            ],
        )
    )
    assert "ledger integrity" in _laws(v.findings)


def test_tautological_justifications_are_flagged():
    final = "I keep the drawer shut and I never open it"
    for weak in ("sounds better", "it flows better here", "more natural", "just"):
        v = verify_section(
            _section(
                final,
                [
                    Deviation(
                        fragment_original="locked",
                        fragment_adapted="shut",
                        justification=weak,
                        dimension="natural_target_language",
                    )
                ],
            )
        )
        assert "Law 1 — justification quality" in _laws(v.findings), weak


# ---------------------------------------------------------------------------
# Law 4 / Law 3 — restraint and compression
# ---------------------------------------------------------------------------


def test_added_emotion_word_is_flagged():
    v = verify_section(_section("I keep the drawer locked and I never open it, heartbroken"))
    assert "Law 4 — Restraint Ceiling" in _laws(v.findings)
    assert any(f.fragment == "heartbroken" for f in v.findings)


def test_added_intensifier_is_flagged():
    v = verify_section(_section("I keep the drawer completely locked and I never open it"))
    assert any(
        f.law == "Law 4 — Restraint Ceiling" and f.fragment == "completely"
        for f in v.findings
    )


def test_added_explanatory_connective_is_flagged():
    v = verify_section(
        _section("I keep the drawer locked because I never open it")
    )
    assert any(
        f.law == "Law 3 — Compression Floor" and f.fragment == "because"
        for f in v.findings
    )


def test_emotion_word_already_in_the_anchor_is_not_flagged():
    anchor = "the pain stays with me"
    v = verify_section(_section("the pain stays with me", anchor=anchor))
    assert "Law 4 — Restraint Ceiling" not in _laws(v.findings)


# ---------------------------------------------------------------------------
# Law 5 — Ambiguity Lock, across sections
# ---------------------------------------------------------------------------


def test_inconsistent_motif_rendering_across_sections_is_an_error():
    result = {
        "sections": [
            _section(
                ANCHOR, name="verse_1", motif_renderings={"saath ho": "If you're here."}
            ).model_dump(),
            _section(
                ANCHOR, name="chorus", motif_renderings={"saath ho": "If you stay with me."}
            ).model_dump(),
        ]
    }
    report = verify_result(result)
    assert not report.passed
    assert "Law 5 — Ambiguity Lock" in _laws(report.cross_section_findings)


def test_consistent_motif_rendering_passes():
    result = {
        "sections": [
            _section(
                ANCHOR, name="verse_1", motif_renderings={"saath ho": "If you're here."}
            ).model_dump(),
            _section(
                ANCHOR, name="chorus", motif_renderings={"saath ho": "If you're here."}
            ).model_dump(),
        ]
    }
    report = verify_result(result)
    assert report.cross_section_findings == []
    assert report.passed


# ---------------------------------------------------------------------------
# Cultural anchors — one disposition per term, song-wide
# ---------------------------------------------------------------------------


def _anchor(term: str, disposition: str) -> AnchorDecision:
    return AnchorDecision(term=term, disposition=disposition, rationale="test")


def test_inconsistent_anchor_disposition_is_an_error():
    result = {
        "sections": [
            _section(
                ANCHOR, name="verse_1", cultural_anchors=[_anchor("ishq", "preserve")]
            ).model_dump(),
            _section(
                ANCHOR, name="chorus", cultural_anchors=[_anchor("ishq", "adapt")]
            ).model_dump(),
        ]
    }
    report = verify_result(result)
    assert not report.passed
    assert "Cultural anchor consistency" in _laws(report.cross_section_findings)


def test_consistent_anchor_disposition_passes():
    result = {
        "sections": [
            _section(
                ANCHOR, name="verse_1", cultural_anchors=[_anchor("ishq", "preserve")]
            ).model_dump(),
            _section(
                ANCHOR, name="chorus", cultural_anchors=[_anchor("Ishq", "preserve")]
            ).model_dump(),
        ]
    }
    report = verify_result(result)
    assert report.cross_section_findings == []
    assert report.passed


def test_songs_without_anchors_are_unaffected():
    result = {"sections": [_section(ANCHOR).model_dump()]}
    assert verify_result(result).passed


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


def test_missing_translator_anchor_is_unverifiable_not_a_crash():
    v = verify_section(_section("anything at all", with_anchor=False))
    assert v.verifiable is False
    assert v.findings[0].law == "verifiability"


def test_report_summary_renders_and_flags_lenient_self_grading():
    result = {
        "sections": [
            _section(
                "A completely different line with new words entirely",
                invention_penalty=0.0,
            ).model_dump()
        ]
    }
    report = verify_result(result)
    summary = report.summary()
    assert "VERDICT: FAIL" in summary
    assert "graded itself more leniently" in summary
