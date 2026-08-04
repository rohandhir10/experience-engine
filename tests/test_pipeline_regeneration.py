"""Tests for engine.pipeline's escalation path: when every Creative
Adapter candidate already dropped a source repeat, the corrective pass
must regenerate a fresh candidate pool (writers_room_v1.
regenerate_creative_adapter_candidates + judge_candidates) rather than
re-judging the same, already-flawed pool
(writers_room_v1.retry_section_with_finding) — the specific limitation
flagged after the deterministic repeated-line-preservation check
(engine/verify.py) was added: re-judging can only pick among EXISTING
candidates, so if none of them has the repeat, no amount of re-judging
recovers it.

A fake client stands in for the LLM throughout, branching on the `stage`
argument every real call site already passes (see engine/writers_room_v1.py)
rather than parsing prompt text, so the two "creative_adapter" and
"creative_adapter_regeneration" calls — and the two "judge_triage" calls,
before and after regeneration — are each unambiguous.
"""
from __future__ import annotations

from engine.models import SectionInput, SongInput
from engine.pipeline import _all_creative_candidates_drop_a_repeat, run_engine

from .test_pipeline_mock import FAKE_SONG_DNA
from .test_writers_room_v1 import DIMENSION_SCORES

ANCHOR = "hold me now\nnever let go\nhold me now\nnever let go"
DROPPED_REPEAT_LINE = "hold me tight\nnever let me go"
PRESERVED_REPEAT_LINE = "hold me tight\nnever let me go\nhold on tight\ndon't let go now"

_PHILOSOPHIES = [
    "maximum_fidelity",
    "native_english_lyricist",
    "performance_first",
    "emotion_first",
    "genre_first",
]


def _candidates(text: str) -> list[dict]:
    return [
        {
            "text": text,
            "philosophy": philosophy,
            "leans_into": "insistence",
            "confidence": 0.9,
            "uncertainty_type": "none",
        }
        for philosophy in _PHILOSOPHIES
    ]


class FakeClientAllCandidatesDropTheRepeat:
    """Every one of the 5 initial Creative Adapter candidates drops the
    anchor's repeated couplet down to one occurrence; the Judge ships one
    of them as-is (a real Law 3 (repetition) violation). On corrective
    regeneration, the fake Creative Adapter call returns 5 candidates
    that all DO preserve the repeat, and the fake Judge picks a
    preserving one this time.
    """

    def __init__(self):
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append(stage)
        if stage == "song_dna":
            return FAKE_SONG_DNA
        if stage == "translator":
            return {
                "text": ANCHOR,
                "leans_into": "insistence",
                "confidence": 0.9,
                "uncertainty_type": "none",
            }
        if stage == "creative_adapter":
            return {"candidates": _candidates(DROPPED_REPEAT_LINE)}
        if stage == "creative_adapter_regeneration":
            return {"candidates": _candidates(PRESERVED_REPEAT_LINE)}
        if stage == "judge_triage":
            final_line = (
                PRESERVED_REPEAT_LINE if PRESERVED_REPEAT_LINE in user else DROPPED_REPEAT_LINE
            )
            return {
                "ready_to_rule": True,
                "ruling": {
                    "final_line": final_line,
                    "sources_used": [],
                    "vetoes_applied": [],
                    "deviations": [
                        {
                            "fragment_original": ANCHOR,
                            "fragment_adapted": final_line,
                            "justification": "reworded for natural phrasing",
                            "dimension": "artistic_fidelity",
                        }
                    ],
                    "dimension_scores": DIMENSION_SCORES,
                    "priority_tradeoffs_made": "test fixture ruling",
                    "disagreements_overruled": [],
                },
                "specialists_needed": [],
                "why": "test fixture: rules immediately",
            }
        raise AssertionError(f"Unexpected stage: {stage!r}")


def _make_song() -> SongInput:
    return SongInput(
        source_language="English (test)",
        sections=[SectionInput(name="verse_1", source_text="hold me now\nnever let go")],
    )


def test_all_candidates_dropping_the_repeat_triggers_regeneration_not_just_rejudge():
    client = FakeClientAllCandidatesDropTheRepeat()
    result = run_engine(
        _make_song(), client=client, room_version="v1", apply_corrective_pass=True
    )
    assert result.section_results[0].ruling.final_line == PRESERVED_REPEAT_LINE
    # A real fresh Creative Adapter call happened, not just a re-judge of
    # the stale pool - "corrective_retry" (the plain re-judge stage) must
    # NOT appear; "creative_adapter_regeneration" must.
    assert "creative_adapter_regeneration" in client.calls
    assert "corrective_retry" not in client.calls


def test_without_the_flag_the_dropped_repeat_ships_uncorrected():
    client = FakeClientAllCandidatesDropTheRepeat()
    result = run_engine(_make_song(), client=client, room_version="v1")
    assert result.section_results[0].ruling.final_line == DROPPED_REPEAT_LINE


def test_all_creative_candidates_drop_a_repeat_is_false_when_one_candidate_preserves_it():
    """If even one Creative Adapter candidate already preserves the
    repeat, re-judging (not regeneration) is the right fix - the Judge
    just needs to be pointed at the better existing option.
    """
    client = FakeClientAllCandidatesDropTheRepeat()
    result = run_engine(_make_song(), client=client, room_version="v1")
    section_result = result.section_results[0]
    # Swap one candidate's text for a repeat-preserving rendering.
    section_result.candidates[1].text = PRESERVED_REPEAT_LINE
    assert not _all_creative_candidates_drop_a_repeat(section_result)


def test_all_creative_candidates_drop_a_repeat_is_false_with_no_real_repetition():
    """No verbatim repetition in the anchor at all -> nothing for this
    check to escalate on, regardless of what the candidates say.
    """
    client = FakeClientAllCandidatesDropTheRepeat()
    result = run_engine(_make_song(), client=client, room_version="v1")
    section_result = result.section_results[0]
    for candidate in section_result.candidates:
        if candidate.agent == "translator":
            candidate.text = "one plain line\nanother plain line"
    assert not _all_creative_candidates_drop_a_repeat(section_result)
