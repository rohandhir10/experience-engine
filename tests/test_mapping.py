"""server/mapping.py's job is turning an EngineResult into the frontend's
ExperienceResult contract (web/lib/types.ts) - these lock in that the
language fields actually pass through, since the frontend needs
targetLanguage to know which direction a result is in.
"""
from __future__ import annotations

from engine.models import (
    Candidate,
    JudgeRuling,
    SectionInput,
    SectionResultV1,
    SongDNA,
    SongInput,
)
from engine.pipeline import EngineResult
from server.mapping import _explain_why, to_experience_result
from tests.test_pipeline_mock import FAKE_SONG_DNA


class _FakeClient:
    def complete_json(self, *args, **kwargs):
        return {"why": "It lands softer this way."}


class _AssertNotCalledClient:
    def complete_json(self, *args, **kwargs):
        raise AssertionError("the model must not be called when literal == aura")


def _engine_result(
    target_language: str,
    final_line: str = "Reste, juste pour ce soir.",
    source_syllable_count: int | None = None,
    deviations: list[dict] | None = None,
) -> EngineResult:
    song = SongInput(
        source_language="English",
        target_language=target_language,
        sections=[SectionInput(name="verse_1", source_text="Stay, just for tonight.")],
    )
    dna = SongDNA.model_validate(FAKE_SONG_DNA)
    section = SectionResultV1(
        section="verse_1",
        candidates=[
            Candidate(id="a1", agent="translator", text="Stay, just for tonight.", round="generation"),
        ],
        routing_signals={},
        ruling=JudgeRuling(
            section="verse_1",
            final_line=final_line,
            priority_tradeoffs_made="test",
            deviations=deviations or [],
            invention_penalty=0.0,
        ),
        source_syllable_count=source_syllable_count,
    )
    return EngineResult(song=song, dna=dna, section_results=[section], room_version="v1")


def test_target_language_passes_through_to_the_frontend_contract():
    result = to_experience_result(_FakeClient(), _engine_result("Hindi"), "abc123")
    assert result["targetLanguage"] == "Hindi"
    assert result["sourceLanguage"] == "English"


def test_default_target_language_is_still_english():
    result = to_experience_result(_FakeClient(), _engine_result("English"), "abc123")
    assert result["targetLanguage"] == "English"


def test_singability_is_surfaced_for_english_targets_with_a_source_count():
    result = to_experience_result(
        _FakeClient(),
        _engine_result("English", final_line="Stay with me tonight", source_syllable_count=5),
        "abc123",
    )
    singability = result["sections"][0]["singability"]
    assert singability is not None
    assert singability["sourceCount"] == 5
    assert singability["closeMatch"] is True


def test_singability_is_none_without_a_source_count():
    result = to_experience_result(
        _FakeClient(),
        _engine_result("English", source_syllable_count=None),
        "abc123",
    )
    assert result["sections"][0]["singability"] is None


def test_singability_is_none_for_non_english_targets():
    """count_syllables_text is CMU-dictionary-backed (English only) - it
    would silently mismeasure a Hindi/Korean/Japanese/Spanish shipped line
    rather than report nothing, so this must stay off for those targets."""
    result = to_experience_result(
        _FakeClient(),
        _engine_result("Hindi", source_syllable_count=5),
        "abc123",
    )
    assert result["sections"][0]["singability"] is None


def test_poetic_register_passes_through_at_song_level():
    result = to_experience_result(_FakeClient(), _engine_result("English"), "abc123")
    assert result["poeticRegister"] == "melodramatic-romantic"


def test_dominant_feeling_passes_through_per_section():
    result = to_experience_result(_FakeClient(), _engine_result("English"), "abc123")
    assert result["sections"][0]["dominantFeeling"] == "guarded grief"


def test_deviations_are_empty_when_the_ruling_has_none():
    result = to_experience_result(_FakeClient(), _engine_result("English"), "abc123")
    assert result["sections"][0]["deviations"] == []


def test_deviations_pass_through_at_fragment_level():
    """justification is real data, included for the Enterprise/audit
    surface - the consumer popup must not render it directly (see
    server/mapping.py's _deviations_payload docstring), but this just
    checks the payload carries it through unmodified."""
    result = to_experience_result(
        _FakeClient(),
        _engine_result(
            "English",
            deviations=[
                {
                    "fragment_original": "stay with me",
                    "fragment_adapted": "don't go",
                    "justification": "matches the chorus's repeated hook phrasing",
                    "dimension": "genre_authenticity",
                }
            ],
        ),
        "abc123",
    )
    deviations = result["sections"][0]["deviations"]
    assert deviations == [
        {
            "fragmentOriginal": "stay with me",
            "fragmentAdapted": "don't go",
            "justification": "matches the chorus's repeated hook phrasing",
        }
    ]


def test_explain_why_skips_the_model_when_literal_and_aura_are_identical():
    """Forcing the model to always cite a real phrase-level diff means it
    must have a real diff to cite - a section with none should never
    reach the model at all, or it'll either invent a difference or pad a
    non-answer with generic praise, the exact failure this guards."""
    result = _explain_why(
        _AssertNotCalledClient(), "thesis", "Stay with me.", "Stay with me.", "no changes"
    )
    assert result == "This line stays exactly as the literal reading - no rewrite was needed here."


def test_to_experience_result_skips_the_model_for_an_unchanged_section():
    result = to_experience_result(
        _AssertNotCalledClient(),
        # final_line matches _engine_result's translator candidate text
        # ("Stay, just for tonight.") exactly - a genuinely unchanged line.
        _engine_result("English", final_line="Stay, just for tonight."),
        "abc123",
    )
    assert "no rewrite was needed" in result["sections"][0]["why"]
