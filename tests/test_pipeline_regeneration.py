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
from engine.pipeline import (
    _all_creative_candidates_collapse_structure,
    _all_creative_candidates_drop_a_repeat,
    run_engine,
)

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


# ---------------------------------------------------------------------------
# The same escalation, for the OTHER Compression Floor failure: a verse
# flattened into running prose. Reproduces the shape of a real production
# failure on "Jiya Jale", where a short repetitive source came back as one
# continuous paragraph with commas standing in for the line breaks.
# ---------------------------------------------------------------------------

_LYRIC_ANCHOR = (
    "The heart burns, life burns\n"
    "Smoke rises, smoke rises\n"
    "Your bud-like body\n"
    "Your lips like a pearl\n"
    "Golden anklets\n"
    "Small cuckoos"
)
_PROSE_COLLAPSE = (
    "The heart burns, life burns. Smoke rises, smoke rises. Your bud-like "
    "body, your lips like a pearl. Golden anklets, small cuckoos."
)


def _section_with(anchor: str, creative_texts: list[str]):
    client = FakeClientAllCandidatesDropTheRepeat()
    result = run_engine(_make_song(), client=client, room_version="v1")
    section_result = result.section_results[0]
    for candidate in section_result.candidates:
        if candidate.agent == "translator":
            candidate.text = anchor
    creatives = [c for c in section_result.candidates if c.agent == "creative_adapter"]
    for candidate, text in zip(creatives, creative_texts):
        candidate.text = text
    return section_result


def test_collapse_escalation_fires_when_every_candidate_is_prose():
    section = _section_with(_LYRIC_ANCHOR, [_PROSE_COLLAPSE] * 5)
    assert _all_creative_candidates_collapse_structure(section)


def test_collapse_escalation_does_not_fire_when_one_candidate_keeps_the_lines():
    """One line-preserving candidate in the pool means re-judging can fix
    this - the Judge just picked the wrong option. Regenerating would be
    wasted spend.
    """
    section = _section_with(
        _LYRIC_ANCHOR, [_PROSE_COLLAPSE] * 4 + [_LYRIC_ANCHOR]
    )
    assert not _all_creative_candidates_collapse_structure(section)


def test_collapse_escalation_does_not_fire_on_a_short_anchor():
    """Below verify.py's MIN_LINES_FOR_COLLAPSE_CHECK there is no line
    structure worth calling collapsed, so nothing should escalate.
    """
    section = _section_with("one line\nanother", ["one line and another"] * 5)
    assert not _all_creative_candidates_collapse_structure(section)


def test_collapse_escalation_needs_a_translator_anchor():
    section = _section_with(_LYRIC_ANCHOR, [_PROSE_COLLAPSE] * 5)
    section.candidates = [c for c in section.candidates if c.agent != "translator"]
    assert not _all_creative_candidates_collapse_structure(section)


def test_line_structure_preserved_matches_the_verifier_error_it_mirrors():
    """The predicate pipeline.py routes on must agree with the finding
    verify.py actually raises, or the escalation fires on sections the
    verifier never flagged (or misses ones it did).
    """
    from engine.verify import line_structure_preserved

    assert not line_structure_preserved(_LYRIC_ANCHOR, _PROSE_COLLAPSE)
    assert line_structure_preserved(_LYRIC_ANCHOR, _LYRIC_ANCHOR)


class FakeClientAllCandidatesCollapseStructure:
    """Every initial Creative Adapter candidate flattens the anchor's six
    lyric lines into one running prose sentence (a real Law 3 Compression
    Floor violation, error severity). On corrective regeneration the fake
    Creative Adapter returns line-preserving candidates instead, and the
    Judge picks one.

    Same shape as FakeClientAllCandidatesDropTheRepeat above, for the
    other Compression Floor failure — it exists to prove the ROUTING
    decision (regenerate vs. plain re-judge), which testing the
    _all_creative_candidates_collapse_structure predicate alone does not.
    """

    def __init__(self):
        self.calls: list[str] = []

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append(stage)
        if stage == "song_dna":
            return FAKE_SONG_DNA
        if stage == "translator":
            return {
                "text": _LYRIC_ANCHOR,
                "leans_into": "yearning",
                "confidence": 0.9,
                "uncertainty_type": "none",
            }
        if stage == "creative_adapter":
            return {"candidates": _candidates(_PROSE_COLLAPSE)}
        if stage == "creative_adapter_regeneration":
            return {"candidates": _candidates(_LINE_PRESERVING_ADAPTATION)}
        if stage in ("judge_triage", "corrective_retry"):
            final_line = (
                _LINE_PRESERVING_ADAPTATION
                if _LINE_PRESERVING_ADAPTATION in user
                else _PROSE_COLLAPSE
            )
            return {
                "ready_to_rule": True,
                "ruling": {
                    "final_line": final_line,
                    "sources_used": [],
                    "vetoes_applied": [],
                    "deviations": [
                        {
                            "fragment_original": "The heart burns",
                            "fragment_adapted": final_line.split("\n")[0][:30],
                            "justification": (
                                "the source names the burning twice and the "
                                "English has to carry both"
                            ),
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


_LINE_PRESERVING_ADAPTATION = (
    "My heart is burning, my life is burning\n"
    "The smoke keeps rising, keeps rising\n"
    "Your body like a bud\n"
    "Your lips like a pearl\n"
    "Anklets of gold\n"
    "Little cuckoos calling"
)


def _lyric_song() -> SongInput:
    return SongInput(
        title="collapse fixture",
        source_language="Hindi",
        sections=[SectionInput(name="verse_1", source_text="जिया जले जाँ जले\nधुआँ चले")],
    )


def test_a_verse_collapsed_into_prose_triggers_regeneration_not_just_rejudge():
    client = FakeClientAllCandidatesCollapseStructure()
    result = run_engine(
        _lyric_song(), client=client, room_version="v1", apply_corrective_pass=True
    )
    # The whole point: a fresh Creative Adapter call happened. Re-judging
    # the prose-only pool could never have produced line-broken output.
    assert "creative_adapter_regeneration" in client.calls
    assert result.section_results[0].ruling.final_line == _LINE_PRESERVING_ADAPTATION


def test_without_the_corrective_pass_the_collapsed_verse_ships_as_prose():
    client = FakeClientAllCandidatesCollapseStructure()
    result = run_engine(_lyric_song(), client=client, room_version="v1")
    assert result.section_results[0].ruling.final_line == _PROSE_COLLAPSE
    assert "creative_adapter_regeneration" not in client.calls
