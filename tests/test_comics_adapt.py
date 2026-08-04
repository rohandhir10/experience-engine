"""Tests for engine/comics_adapt.py — item #4 of the chapter-level-
context roadmap: wiring a real bubble through the existing V1 Writers'
Room (Translator -> Creative Adapter -> Judge), reusing ChapterDNA in
place of SongDNA via _bubble_song_dna's wrapping. A fake client stands
in for the LLM, branching on the real `stage=` argument every call site
already passes; no real API call is made.
"""
from __future__ import annotations

from engine.comics_adapt import _bubble_song_dna, adapt_bubble, adapt_chapter
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
    # The dict entry is overwritten, not appended - only the latest
    # register should appear in bubble 2's prompt.
    assert judge_calls[1].count("Guard Captain:") == 1


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
