"""Tests for engine/chapter_dna.py and the Chapter DNA models/prompt
(engine/models.py, engine/prompts.py::chapter_dna_prompt) - item #3 of
the chapter-level-context roadmap. A fake client stands in for the LLM;
no real API call is made.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from engine.chapter_dna import generate_chapter_dna
from engine.models import BubbleInput, ChapterDNA, ChapterInput
from engine.prompts import chapter_dna_prompt

FAKE_CHAPTER_DNA = {
    "artistic_thesis": "Loyalty gets tested the moment it becomes costly.",
    "genre_feel": "royal-court drama",
    "tone": "tense, restrained fear",
    "ongoing_plot_context": (
        "A guard has failed to stop the princess from leaving and is bracing "
        "to be punished for it in front of the king."
    ),
    "characters": [
        {
            "name": "Guard Captain",
            "voice_description": "Terse, deferential, speaks in short clipped sentences under stress.",
            "honorific_register": "formal, deferential (하십시오체)",
            "relationships": ["reports directly to the king", "responsible for the princess's safety"],
        }
    ],
}


class FakeClientReturnsChapterDna:
    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        if stage == "chapter_dna":
            return FAKE_CHAPTER_DNA
        raise AssertionError(f"Unexpected stage: {stage!r}")


def _chapter(**overrides) -> ChapterInput:
    defaults = dict(
        source_language="Korean",
        bubbles=[
            BubbleInput(id="panel_1_bubble_1", source_text="공주님을 막지 못하고"),
            BubbleInput(id="panel_1_bubble_2", source_text="전하께 보인다면 저희가 매를 맞을 겁니다."),
        ],
    )
    defaults.update(overrides)
    return ChapterInput(**defaults)


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------


def test_chapter_requires_at_least_one_bubble():
    with pytest.raises(ValidationError, match="at least one bubble"):
        ChapterInput(source_language="Korean", bubbles=[])


def test_chapter_rejects_duplicate_bubble_ids():
    with pytest.raises(ValidationError, match="Duplicate bubble id"):
        ChapterInput(
            source_language="Korean",
            bubbles=[
                BubbleInput(id="b1", source_text="hello"),
                BubbleInput(id="b1", source_text="bye"),
            ],
        )


def test_chapter_rejects_an_empty_bubble_id():
    with pytest.raises(ValidationError, match="non-empty id"):
        ChapterInput(source_language="Korean", bubbles=[BubbleInput(id="  ", source_text="hello")])


def test_bubble_voice_defaults_to_unattributed():
    bubble = BubbleInput(id="b1", source_text="hello")
    assert bubble.voice is None


# ---------------------------------------------------------------------------
# chapter_dna_prompt
# ---------------------------------------------------------------------------


def test_prompt_includes_every_bubble_in_order():
    chapter = _chapter()
    _, user = chapter_dna_prompt(chapter)
    first_pos = user.index("panel_1_bubble_1")
    second_pos = user.index("panel_1_bubble_2")
    assert first_pos < second_pos
    assert "공주님을 막지 못하고" in user
    assert "전하께 보인다면" in user


def test_prompt_substitutes_target_language():
    chapter = _chapter(target_language="Spanish")
    system, _ = chapter_dna_prompt(chapter)
    assert "Never propose Spanish wording" in system
    assert "{target_language}" not in system


def test_prompt_covers_honorific_register_and_characters():
    system, _ = chapter_dna_prompt(_chapter())
    assert "honorific_register" in system
    assert "voice_description" in system
    assert "does not actually support" in system or "does not support" in system


def test_prompt_includes_context_note_when_given():
    chapter = _chapter(context_note="A palace guard scene.")
    _, user = chapter_dna_prompt(chapter)
    assert "A palace guard scene." in user


# ---------------------------------------------------------------------------
# generate_chapter_dna
# ---------------------------------------------------------------------------


def test_generate_chapter_dna_parses_a_valid_response():
    dna = generate_chapter_dna(_chapter(), FakeClientReturnsChapterDna())
    assert isinstance(dna, ChapterDNA)
    assert dna.genre_feel == "royal-court drama"
    assert len(dna.characters) == 1
    assert dna.characters[0].name == "Guard Captain"
    assert dna.characters[0].honorific_register == "formal, deferential (하십시오체)"


def test_generate_chapter_dna_allows_zero_characters():
    """A caption-only chapter with no identifiable speaker is valid -
    the prompt explicitly allows an empty characters list rather than
    forcing a fabricated profile."""

    class FakeClientNoCharacters:
        def complete_json(self, system, user, max_tokens=None, stage="unknown") -> dict:
            return {**FAKE_CHAPTER_DNA, "characters": []}

    dna = generate_chapter_dna(_chapter(), FakeClientNoCharacters())
    assert dna.characters == []
