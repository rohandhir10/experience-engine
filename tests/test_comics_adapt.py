"""Tests for engine/comics_adapt.py — item #4 of the chapter-level-
context roadmap: wiring a real bubble through the existing V1 Writers'
Room (Translator -> Creative Adapter -> Judge), reusing ChapterDNA in
place of SongDNA via _bubble_song_dna's wrapping. A fake client stands
in for the LLM, branching on the real `stage=` argument every call site
already passes; no real API call is made.
"""
from __future__ import annotations

import time

import pytest

from engine.comics_adapt import ChapterTimeoutError, _bubble_song_dna, adapt_bubble, adapt_chapter
from engine.models import BubbleInput, ChapterDNA, ChapterInput, CharacterVoice, RoomMemory

CHAPTER_DNA = ChapterDNA(
    artistic_thesis="Loyalty gets tested the moment it becomes costly.",
    genre_feel="royal-court drama",
    tone="tense, restrained fear",
    ongoing_plot_context="A guard braces to be punished for failing to stop the princess.",
    characters=[],
)

_PHILOSOPHIES = [
    "maximum_fidelity",
    "native_english_lyricist",
    "performance_first",
    "emotion_first",
    "genre_first",
]

DIMENSION_SCORES = [
    {"dimension": d, "score": 0.9, "note": "test"}
    for d in (
        "artistic_fidelity",
        "genre_authenticity",
        "natural_target_language",
        "voice_consistency",
        "singability_rhythm",
    )
]


def _candidates(text: str) -> list[dict]:
    return [
        {
            "text": text,
            "philosophy": philosophy,
            "leans_into": "restrained fear",
            "confidence": 0.9,
            "uncertainty_type": "none",
        }
        for philosophy in _PHILOSOPHIES
    ]


def _ruling(final_line: str) -> dict:
    return {
        "ready_to_rule": True,
        "ruling": {
            "final_line": final_line,
            "sources_used": [],
            "vetoes_applied": [],
            "deviations": [],
            "dimension_scores": DIMENSION_SCORES,
            "priority_tradeoffs_made": "test fixture ruling",
            "disagreements_overruled": [],
        },
        "specialists_needed": [],
        "why": "test fixture: rules immediately",
    }


class FakeClientRulesImmediately:
    """One fixed adapted line for every bubble, regardless of source
    text — enough to prove the wiring works without needing per-bubble
    fixture data.
    """

    def __init__(self, adapted_line: str = "We will be beaten if she is seen."):
        self.adapted_line = adapted_line
        self.calls: list[tuple[str, str]] = []  # (stage, user) for inspection

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append((stage, user))
        if stage == "translator":
            return {
                "text": "We failed to stop the princess.",
                "leans_into": "fear",
                "confidence": 0.9,
                "uncertainty_type": "none",
            }
        if stage == "creative_adapter":
            return {"candidates": _candidates(self.adapted_line)}
        if stage == "judge_triage":
            return _ruling(self.adapted_line)
        raise AssertionError(f"Unexpected stage: {stage!r}")


def _chapter(**overrides) -> ChapterInput:
    defaults = dict(
        source_language="Korean",
        bubbles=[
            BubbleInput(id="panel_1_bubble_1", source_text="공주님을 막지 못하고", voice="Guard Captain"),
        ],
    )
    defaults.update(overrides)
    return ChapterInput(**defaults)


def test_bubble_song_dna_maps_chapter_fields_onto_a_single_section():
    bubble = BubbleInput(id="b1", source_text="hello")
    wrapped = _bubble_song_dna(CHAPTER_DNA, bubble)

    assert wrapped.artistic_thesis == CHAPTER_DNA.artistic_thesis
    assert wrapped.genre_feel == CHAPTER_DNA.genre_feel
    assert wrapped.poetic_register == CHAPTER_DNA.tone
    assert wrapped.arc_shape == CHAPTER_DNA.ongoing_plot_context
    assert wrapped.songwriter_intention == CHAPTER_DNA.ongoing_plot_context
    assert len(wrapped.sections) == 1
    assert wrapped.sections[0].name == "b1"
    assert wrapped.sections[0].emotional_arc_point.dominant_feeling == CHAPTER_DNA.tone
    # No fabricated per-bubble analysis - motifs/ambiguities/symbols stay empty.
    assert wrapped.motifs == []
    assert wrapped.ambiguities == []
    assert wrapped.symbols == []


def test_adapt_bubble_runs_the_full_room_and_returns_a_real_ruling():
    client = FakeClientRulesImmediately()
    bubble = BubbleInput(id="panel_1_bubble_1", source_text="공주님을 막지 못하고", voice="Guard Captain")

    result = adapt_bubble(_chapter(), CHAPTER_DNA, bubble, RoomMemory(), client)

    assert result.section == "panel_1_bubble_1"
    assert result.ruling.final_line == client.adapted_line
    assert result.ruling.voice == "Guard Captain"
    # 1 translator + 5 creative_adapter candidates.
    assert len(result.candidates) == 6
    stages_called = [stage for stage, _ in client.calls]
    assert stages_called == ["translator", "creative_adapter", "judge_triage"]


def test_adapt_chapter_processes_every_bubble_in_order():
    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one", voice="Guard Captain"),
            BubbleInput(id="b2", source_text="line two", voice="Guard Captain"),
            BubbleInput(id="b3", source_text="line three", voice="Princess"),
        ]
    )
    client = FakeClientRulesImmediately()

    results = adapt_chapter(chapter, CHAPTER_DNA, client)

    assert [r.section for r in results] == ["b1", "b2", "b3"]
    assert results[2].ruling.voice == "Princess"


def test_adapt_chapter_reports_on_stage_for_each_bubble_in_order():
    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one", voice="Guard Captain"),
            BubbleInput(id="b2", source_text="line two", voice="Princess"),
        ]
    )
    client = FakeClientRulesImmediately()
    events: list[tuple[str, str, int, int]] = []

    adapt_chapter(chapter, CHAPTER_DNA, client, on_stage=lambda *args: events.append(args))

    assert events == [
        ("b1", "adapting", 1, 2),
        ("b1", "verifying", 1, 2),
        ("b2", "adapting", 2, 2),
        ("b2", "verifying", 2, 2),
    ]


def test_adapt_chapter_reports_on_bubble_done_once_per_bubble_with_the_real_result():
    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one", voice="Guard Captain"),
            BubbleInput(id="b2", source_text="line two", voice="Princess"),
        ]
    )
    client = FakeClientRulesImmediately()
    completed: list[tuple[str, int, int]] = []

    def on_bubble_done(bubble_id, result, index, total):
        assert result.ruling.final_line == client.adapted_line
        completed.append((bubble_id, index, total))

    results = adapt_chapter(chapter, CHAPTER_DNA, client, on_bubble_done=on_bubble_done)

    assert completed == [("b1", 1, 2), ("b2", 2, 2)]
    # The callback must not change what the function actually returns.
    assert [r.section for r in results] == ["b1", "b2"]


def test_adapt_chapter_works_unchanged_with_no_callbacks_given():
    chapter = _chapter(
        bubbles=[BubbleInput(id="b1", source_text="line one", voice="Guard Captain")]
    )
    client = FakeClientRulesImmediately()
    results = adapt_chapter(chapter, CHAPTER_DNA, client)
    assert [r.section for r in results] == ["b1"]


def test_adapt_chapter_completes_normally_with_a_deadline_far_in_the_future():
    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one", voice="Guard Captain"),
            BubbleInput(id="b2", source_text="line two", voice="Princess"),
        ]
    )
    client = FakeClientRulesImmediately()

    results = adapt_chapter(chapter, CHAPTER_DNA, client, deadline=time.monotonic() + 3600)

    assert [r.section for r in results] == ["b1", "b2"]


def test_adapt_chapter_deadline_check_runs_between_bubbles_not_mid_flight():
    """A deadline that passes DURING b1's own processing must not cut b1
    short, and must let b1 finish for real before stopping the chapter -
    the check only runs between bubbles (see adapt_chapter's docstring on
    why: engine/llm_client.py's own per-call timeout is what bounds a
    single stuck request; this deadline is a coarser, chapter-wide
    ceiling on top of that, not a replacement for it)."""

    class SlowFakeClient(FakeClientRulesImmediately):
        def complete_json(self, system, user, max_tokens=None, stage="unknown") -> dict:
            time.sleep(0.05)
            return super().complete_json(system, user, max_tokens, stage)

    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one", voice="Guard Captain"),
            BubbleInput(id="b2", source_text="line two", voice="Princess"),
            BubbleInput(id="b3", source_text="line three", voice="Princess"),
        ]
    )
    client = SlowFakeClient()

    # b1 alone takes >0.1s (several 0.05s calls); this deadline is
    # already gone by the time b1 finishes, but still in the future when
    # adapt_chapter starts - so b1 must complete intact and only b2 must
    # never start.
    deadline = time.monotonic() + 0.1

    with pytest.raises(ChapterTimeoutError) as exc_info:
        adapt_chapter(chapter, CHAPTER_DNA, client, deadline=deadline)

    assert "1/3" in str(exc_info.value)


def test_adapt_chapter_raises_immediately_if_the_deadline_has_already_passed():
    chapter = _chapter(
        bubbles=[BubbleInput(id="b1", source_text="line one", voice="Guard Captain")]
    )
    client = FakeClientRulesImmediately()

    with pytest.raises(ChapterTimeoutError) as exc_info:
        adapt_chapter(chapter, CHAPTER_DNA, client, deadline=time.monotonic() - 1)

    assert "0/1" in str(exc_info.value)
    assert client.calls == []  # no work started at all, not even for b1


def test_adapt_chapter_carries_room_memory_across_bubbles():
    """The second bubble's Judge call should see the first bubble's
    ruling in its prompt - real cross-bubble continuity, not just N
    independent calls that happen to run in sequence.
    """
    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one", voice="Guard Captain"),
            BubbleInput(id="b2", source_text="line two", voice="Guard Captain"),
        ]
    )
    client = FakeClientRulesImmediately()

    adapt_chapter(chapter, CHAPTER_DNA, client)

    judge_calls = [user for stage, user in client.calls if stage == "judge_triage"]
    assert len(judge_calls) == 2
    assert "No prior sections" in judge_calls[0]
    assert "Decisions already made earlier" in judge_calls[1]
    assert "b1" in judge_calls[1]


def test_adapt_chapter_carries_compensations_across_bubbles():
    class FakeClientWithCompensation(FakeClientRulesImmediately):
        def complete_json(self, system, user, max_tokens=None, stage="unknown") -> dict:
            if stage == "translator":
                return {
                    "text": "We failed to stop the princess.",
                    "leans_into": "fear",
                    "confidence": 0.9,
                    "uncertainty_type": "none",
                    "compensations": [
                        {
                            "source_feature": "반말/존댓말 speech level",
                            "what_it_encodes": "the speaker's deference to the king",
                            "english_carrier": "formal, clipped diction",
                            "carried": True,
                        }
                    ],
                }
            return super().complete_json(system, user, max_tokens, stage)

    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one"),
            BubbleInput(id="b2", source_text="line two"),
        ]
    )
    client = FakeClientWithCompensation()

    results = adapt_chapter(chapter, CHAPTER_DNA, client)

    assert len(results[0].compensations) == 1
    judge_calls = [user for stage, user in client.calls if stage == "judge_triage"]
    assert "speaker's deference to the king" in judge_calls[1]


# ---------------------------------------------------------------------------
# Honorific/speech-register tracking — item #6 of the chapter-level-
# context roadmap.
# ---------------------------------------------------------------------------

CHAPTER_DNA_WITH_CHARACTER = ChapterDNA(
    artistic_thesis=CHAPTER_DNA.artistic_thesis,
    genre_feel=CHAPTER_DNA.genre_feel,
    tone=CHAPTER_DNA.tone,
    ongoing_plot_context=CHAPTER_DNA.ongoing_plot_context,
    characters=[
        CharacterVoice(
            name="Guard Captain",
            voice_description="Terse, deferential, speaks in short clipped sentences under stress.",
            honorific_register="formal, deferential (하십시오체)",
            relationships=[],
        )
    ],
)


def test_adapt_chapter_seeds_honorific_state_from_chapter_dna():
    chapter = _chapter(
        bubbles=[BubbleInput(id="b1", source_text="line one", voice="Guard Captain")]
    )
    client = FakeClientRulesImmediately()

    adapt_chapter(chapter, CHAPTER_DNA_WITH_CHARACTER, client)

    judge_calls = [user for stage, user in client.calls if stage == "judge_triage"]
    assert "Guard Captain: formal, deferential (하십시오체)" in judge_calls[0]


def test_adapt_chapter_seeds_character_voices_from_chapter_dna():
    """Chapter DNA's per-character voice_description/relationships must
    actually reach the prompt, not just get computed and discarded (the
    bug this field was added to fix - see RoomMemory.character_voices'
    docstring)."""
    chapter = _chapter(
        bubbles=[BubbleInput(id="b1", source_text="line one", voice="Guard Captain")]
    )
    client = FakeClientRulesImmediately()

    adapt_chapter(chapter, CHAPTER_DNA_WITH_CHARACTER, client)

    judge_calls = [user for stage, user in client.calls if stage == "judge_triage"]
    assert (
        "Guard Captain: Terse, deferential, speaks in short clipped sentences under stress."
        in judge_calls[0]
    )


def test_adapt_chapter_includes_relationships_in_the_character_voice_summary():
    dna = ChapterDNA(
        artistic_thesis=CHAPTER_DNA.artistic_thesis,
        genre_feel=CHAPTER_DNA.genre_feel,
        tone=CHAPTER_DNA.tone,
        ongoing_plot_context=CHAPTER_DNA.ongoing_plot_context,
        characters=[
            CharacterVoice(
                name="Guard Captain",
                voice_description="Terse, deferential.",
                honorific_register="formal",
                relationships=["reports to the Princess", "distrusts the Advisor"],
            )
        ],
    )
    chapter = _chapter(
        bubbles=[BubbleInput(id="b1", source_text="line one", voice="Guard Captain")]
    )
    client = FakeClientRulesImmediately()

    adapt_chapter(chapter, dna, client)

    judge_calls = [user for stage, user in client.calls if stage == "judge_triage"]
    assert "reports to the Princess" in judge_calls[0]
    assert "distrusts the Advisor" in judge_calls[0]


def test_adapt_chapter_updates_honorific_state_after_a_reported_shift():
    class FakeClientReportsShift(FakeClientRulesImmediately):
        def complete_json(self, system, user, max_tokens=None, stage="unknown") -> dict:
            self.calls.append((stage, user))
            if stage == "judge_triage":
                data = _ruling(self.adapted_line)
                data["ruling"]["honorific_note"] = (
                    "shifted to casual banmal - anger breaking through formality"
                )
                return data
            if stage == "translator":
                return {
                    "text": "We failed to stop the princess.",
                    "leans_into": "fear",
                    "confidence": 0.9,
                    "uncertainty_type": "none",
                }
            if stage == "creative_adapter":
                return {"candidates": _candidates(self.adapted_line)}
            raise AssertionError(f"Unexpected stage: {stage!r}")

    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one", voice="Guard Captain"),
            BubbleInput(id="b2", source_text="line two", voice="Guard Captain"),
        ]
    )
    client = FakeClientReportsShift()

    results = adapt_chapter(chapter, CHAPTER_DNA_WITH_CHARACTER, client)

    assert results[0].ruling.honorific_note == (
        "shifted to casual banmal - anger breaking through formality"
    )
    judge_calls = [user for stage, user in client.calls if stage == "judge_triage"]
    assert "Guard Captain: formal, deferential (하십시오체)" in judge_calls[0]
    assert "Guard Captain: shifted to casual banmal" in judge_calls[1]
    # The honorific dict entry is overwritten, not appended - the OLD
    # register must not still be lingering anywhere in bubble 2's prompt
    # (a second "Guard Captain:" line from RoomMemory.character_voices'
    # separate, fixed-for-the-chapter voice-description block is
    # expected and correct - that's not what this assertion is about).
    assert "formal, deferential (하십시오체)" not in judge_calls[1]


def test_adapt_chapter_does_not_update_honorific_state_for_an_unattributed_bubble():
    chapter = _chapter(
        bubbles=[
            BubbleInput(id="b1", source_text="line one"),  # no voice
            BubbleInput(id="b2", source_text="line two", voice="Guard Captain"),
        ]
    )
    client = FakeClientRulesImmediately()

    adapt_chapter(chapter, CHAPTER_DNA_WITH_CHARACTER, client)

    judge_calls = [user for stage, user in client.calls if stage == "judge_triage"]
    # The chapter-seeded register is still what bubble 2 sees - an
    # unattributed bubble 1 has nothing to update it with.
    assert "Guard Captain: formal, deferential (하십시오체)" in judge_calls[1]


# ---------------------------------------------------------------------------
# Verification on the comics path.
#
# engine/verify.py's constitution checks existed for songs and were never
# wired into comics, so every one of them was dead code here. Found from a
# real Korean panel whose shipped "why" cited wording absent from the
# literal anchor AND justified itself as "to maintain a formal tone" -
# a ledger-integrity error and a vacuous justification respectively, both
# of which verify.py already detects.
# ---------------------------------------------------------------------------


class FakeClientWithRetry(FakeClientRulesImmediately):
    """Adds the corrective_retry stage the base fake rejects, so a test
    can let the retry actually complete instead of only proving it was
    attempted."""

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        if stage == "corrective_retry":
            self.calls.append((stage, user))
            # retry_section_with_finding expects a bare ruling, not the
            # triage envelope _ruling() wraps it in.
            return _ruling("We will be caned if the King sees her.")["ruling"]
        return super().complete_json(system, user, max_tokens=max_tokens, stage=stage)


def _stages(client) -> list[str]:
    """client.calls holds (stage, user) tuples - counting the raw list for
    a stage name silently never matches, which made an earlier version of
    these tests pass vacuously."""
    return [stage for stage, _user in client.calls]


def test_a_bubble_that_ships_the_anchor_with_an_empty_ledger_is_not_re_judged():
    """Verification must not cost a retry on every panel.

    The line shipped here IS the Translator's anchor, with an empty
    deviation ledger - nothing changed, so there is nothing to log and no
    finding to raise. That is the Judge's documented behaviour when no
    candidate earns a real improvement.

    Worth noting what this test replaced: the module's default fixture
    ships a completely different line with an empty ledger, which the
    verifier correctly reports as a Law 1 error ("every change is
    unaudited"). Wiring verification into this path immediately flagged
    the project's own test fixture - which is the check doing its job,
    not a false positive.
    """
    anchor = "We failed to stop the princess."
    client = FakeClientWithRetry(adapted_line=anchor)
    adapt_chapter(_chapter(), CHAPTER_DNA, client)
    assert "corrective_retry" not in _stages(client)


def test_an_unaudited_change_is_caught_on_the_comics_path():
    """The regression that matters: before verification was wired in
    here, a bubble could ship any rewrite with an empty ledger and
    nothing would notice."""
    client = FakeClientWithRetry(adapted_line="Something else entirely, unlogged.")
    adapt_chapter(_chapter(), CHAPTER_DNA, client)
    assert "corrective_retry" in _stages(client)


def test_an_error_finding_triggers_exactly_one_corrective_retry(monkeypatch):
    from engine import comics_adapt
    from engine.verify import Finding, SectionVerification

    def fake_verify(result, target_language="English"):
        return SectionVerification(
            section=result.section,
            findings=[
                Finding(
                    law="ledger integrity",
                    severity="error",
                    section=result.section,
                    detail="A deviation claims the final line says this, but it does not.",
                )
            ],
            ledger_coverage=0.0,
            computed_invention_penalty=0.0,
            reported_invention_penalty=0.0,
            changed_word_count=0,
        )

    monkeypatch.setattr(comics_adapt, "verify_section", fake_verify)
    client = FakeClientWithRetry()
    results = adapt_chapter(_chapter(), CHAPTER_DNA, client)

    # Exactly one - bounded, so a stubborn finding can't loop even though
    # fake_verify would keep reporting the same error forever.
    assert _stages(client).count("corrective_retry") == 1
    # And the corrected ruling is what ships, not the original.
    assert results[0].ruling.final_line == "We will be caned if the King sees her."


def test_a_failing_verifier_does_not_lose_the_adaptation(monkeypatch):
    """Verification is a quality gate, not a correctness precondition."""
    from engine import comics_adapt

    monkeypatch.setattr(
        comics_adapt,
        "verify_section",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("verifier blew up")),
    )
    results = adapt_chapter(_chapter(), CHAPTER_DNA, FakeClientRulesImmediately())
    assert len(results) == 1
    assert results[0].ruling.final_line


def test_a_failing_retry_keeps_the_original_ruling(monkeypatch):
    from engine import comics_adapt
    from engine.verify import Finding, SectionVerification

    monkeypatch.setattr(
        comics_adapt,
        "verify_section",
        lambda result, target_language="English": SectionVerification(
            section=result.section,
            findings=[
                Finding(law="ledger integrity", severity="error",
                        section=result.section, detail="broken")
            ],
            ledger_coverage=0.0,
            computed_invention_penalty=0.0,
            reported_invention_penalty=0.0,
            changed_word_count=0,
        ),
    )
    monkeypatch.setattr(
        comics_adapt,
        "retry_section_with_finding",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("retry failed")),
    )
    results = adapt_chapter(_chapter(), CHAPTER_DNA, FakeClientRulesImmediately())
    assert len(results) == 1
    assert results[0].ruling.final_line


def test_adapt_bubble_enables_emphasis_markup_for_the_judge():
    """Comics-only Judge instruction (engine/prompts.py's
    _EMPHASIS_INSTRUCTION) - adapt_bubble must actually pass
    emphasis_markup=True through to the Judge's real prompt, not just
    accept it as a parameter nobody reads. FakeClientRulesImmediately
    only records (stage, user); this captures `system` too since the
    instruction lives there."""

    class SystemCapturingClient(FakeClientRulesImmediately):
        def __init__(self):
            super().__init__()
            self.systems: list[tuple[str, str]] = []

        def complete_json(self, system, user, max_tokens=None, stage="unknown"):
            self.systems.append((stage, system))
            return super().complete_json(system, user, max_tokens, stage)

    chapter = _chapter(
        bubbles=[BubbleInput(id="b1", source_text="line one", voice="Guard Captain")]
    )
    client = SystemCapturingClient()

    adapt_chapter(chapter, CHAPTER_DNA, client)

    judge_system = next(system for stage, system in client.systems if stage == "judge_triage")
    assert "lettered into a comic speech bubble" in judge_system
    assert "double asterisks" in judge_system
