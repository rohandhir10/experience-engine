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


def _adapted_section(name: str = "verse_1", **kwargs) -> SectionResultV1:
    """A section that is genuinely adapted AND fully audited — the shape a
    healthy ruling has. Used by tests about cross-section consistency,
    which need a fixture that clears every other check so the thing under
    test is the only thing that can fail.

    Note these tests originally reused the literal anchor as their "clean"
    fixture. That stopped being clean when the adaptation floor landed:
    a song identical to its anchor is a translation, which is now an
    error — so the fixture had to become a real adaptation.
    """
    return _section(
        "The drawer stays shut. I never open it.",
        [
            Deviation(
                fragment_original="I keep the drawer locked",
                fragment_adapted="The drawer stays shut",
                justification=(
                    "The source states this as a standing fact about the "
                    "drawer rather than an action she performs; 'I keep' "
                    "puts her agency in the foreground where the source "
                    "keeps it out."
                ),
                dimension="artistic_fidelity",
            )
        ],
        name=name,
        **kwargs,
    )


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
    source_syllable_count: int | None = None,
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
        source_syllable_count=source_syllable_count,
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
    # ANCHOR ends in "it" - a real stop consonant, so the phrase-end
    # sustainability check correctly fires here; it's an orthogonal signal
    # about the line's ending sound, not about ledger/invention-penalty
    # cleanliness, which is what this test is actually checking.
    assert _laws(v.findings) == {"Phrase-end sustainability check"}


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
    for weak in (
        "sounds better",
        "it flows better here",
        "more natural",
        "just",
        # Regression cases: the exact phrasing a real production run used
        # to justify dropping a source's triple-repeated phrase down to
        # one occurrence.
        "feels smoother",
        "more relatable",
        "more natural and engaging",
        "more accessible",
    ):
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
            _adapted_section(
                "verse_1", motif_renderings={"saath ho": "If you're here."}
            ).model_dump(),
            _adapted_section(
                "chorus", motif_renderings={"saath ho": "If you stay with me."}
            ).model_dump(),
        ]
    }
    report = verify_result(result)
    assert not report.passed
    assert "Law 5 — Ambiguity Lock" in _laws(report.cross_section_findings)


def test_consistent_motif_rendering_passes():
    result = {
        "sections": [
            _adapted_section(
                "verse_1", motif_renderings={"saath ho": "If you're here."}
            ).model_dump(),
            _adapted_section(
                "chorus", motif_renderings={"saath ho": "If you're here."}
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
            _adapted_section(
                "verse_1", cultural_anchors=[_anchor("ishq", "preserve")]
            ).model_dump(),
            _adapted_section(
                "chorus", cultural_anchors=[_anchor("ishq", "adapt")]
            ).model_dump(),
        ]
    }
    report = verify_result(result)
    assert not report.passed
    assert "Cultural anchor consistency" in _laws(report.cross_section_findings)


def test_consistent_anchor_disposition_passes():
    result = {
        "sections": [
            _adapted_section(
                "verse_1", cultural_anchors=[_anchor("ishq", "preserve")]
            ).model_dump(),
            _adapted_section(
                "chorus", cultural_anchors=[_anchor("Ishq", "preserve")]
            ).model_dump(),
        ]
    }
    report = verify_result(result)
    assert report.cross_section_findings == []
    assert report.passed


def test_songs_without_anchors_are_unaffected():
    result = {"sections": [_adapted_section().model_dump()]}
    assert verify_result(result).passed


# ---------------------------------------------------------------------------
# The counterweight — a translation must not score as a localization
# ---------------------------------------------------------------------------


def test_verbatim_translation_fails_even_though_every_other_check_passes():
    """The bug this exists to fix: a song shipped as the Translator's
    literal anchor scored 100% coverage, 0.0 invention penalty, zero
    findings, PASS — a perfect grade for the one thing AURA is not.
    """
    report = verify_result({"sections": [_section(ANCHOR).model_dump()]})
    section = report.sections[0]

    # Every pre-existing signal still says "clean"...
    assert section.ledger_coverage == 1.0
    assert section.computed_invention_penalty == 0.0
    # ANCHOR ends in "it" (a real stop consonant) - orthogonal to ledger/
    # invention-penalty cleanliness, so it's the one finding still allowed.
    assert {f.law for f in section.findings} == {"Phrase-end sustainability check"}

    # ...and the run still fails, on the new signal alone.
    assert section.adaptation_distance == 0.0
    assert not report.passed
    assert "Adaptation floor" in _laws(report.cross_section_findings)


def test_a_genuine_adaptation_clears_the_floor():
    report = verify_result({"sections": [_adapted_section().model_dump()]})
    assert report.passed
    assert report.sections[0].adaptation_distance > 0.08


def test_one_literal_section_among_adapted_ones_is_fine():
    """Per-section literalness is legitimate — the constitution says an
    empty deviation ledger is a GOOD sign. The floor is deliberately a
    song-level check so it never becomes a per-line change quota the
    engine could game by manufacturing deviations.
    """
    report = verify_result(
        {
            "sections": [
                _section(ANCHOR, name="verse_1").model_dump(),
                _adapted_section("chorus").model_dump(),
                _adapted_section("verse_2").model_dump(),
            ]
        }
    )
    assert "Adaptation floor" not in _laws(report.cross_section_findings)


def test_adaptation_distance_rises_with_real_departure():
    identical = verify_section(_section(ANCHOR)).adaptation_distance
    small = verify_section(
        _section("I keep the drawer shut and I never open it")
    ).adaptation_distance
    large = verify_section(
        _section("The drawer stays shut. Nothing in it moves.")
    ).adaptation_distance
    assert identical == 0.0
    assert identical < small < large


def test_summary_reports_adaptation_distance_beside_invention_penalty():
    report = verify_result({"sections": [_section(ANCHOR).model_dump()]})
    summary = report.summary()
    assert "Invention penalty" in summary
    assert "Adaptation distance" in summary
    assert "Effectively a translation" in summary


# ---------------------------------------------------------------------------
# Compression Floor — lyric collapsing into prose
# ---------------------------------------------------------------------------


def test_line_collapse_into_prose_is_an_error():
    """The real failure from the Agar Tum Saath Ho run: six lyric lines
    rendered as one running sentence.
    """
    multiline_anchor = (
        "Stay a moment\nlet this heart settle\nhow do I stop you\n"
        "every sorrow slips away\nI fill my eyes with you\nif you are here"
    )
    v = verify_section(
        _section(
            "Stay a moment and let this heart settle, and how do I stop you, "
            "for every sorrow slips away as I fill my eyes with you if you are here.",
            anchor=multiline_anchor,
        )
    )
    collapse = [f for f in v.errors if "lines" in f.detail]
    assert collapse, "six lines merged into one sentence should be an error"


def test_preserved_line_structure_does_not_trigger_collapse():
    multiline_anchor = "Stay a moment\nlet this heart settle\nhow do I stop you"
    v = verify_section(
        _section(
            "Stay — one breath\nsteady this heart\nhow do I hold you here",
            anchor=multiline_anchor,
        )
    )
    assert not [f for f in v.findings if "lines" in f.detail]


def test_added_connective_tissue_is_flagged():
    v = verify_section(
        _section(
            "It is the drawer that I have kept, and it is the one that I do "
            "not open",
            anchor="Drawer locked, never opened",
        )
    )
    assert any("Function words rose" in f.detail for f in v.findings)


# ---------------------------------------------------------------------------
# Singability — checking the Judge's dimension score against a real count
# ---------------------------------------------------------------------------


def test_large_syllable_gap_from_source_is_flagged():
    v = verify_section(_section("Yes", source_syllable_count=20))
    assert any(f.law == "Singability check" for f in v.findings)


def test_matching_syllable_count_is_not_flagged():
    from engine.rhythm import count_syllables_text

    final = "I keep the drawer locked and I never open it"
    v = verify_section(_section(final, source_syllable_count=count_syllables_text(final)))
    assert "Singability check" not in _laws(v.findings)


def test_no_source_count_means_no_singability_check():
    """None means grounding never produced a count (e.g. no source
    language support yet) — absence of a number, not a claim of zero
    gap, so the check must stay silent rather than compare against 0.
    """
    v = verify_section(_section("Yes", source_syllable_count=None))
    assert "Singability check" not in _laws(v.findings)


def test_older_results_without_the_field_are_unaffected():
    """Backwards compatibility: a stored result.json from before this
    field existed defaults to source_syllable_count=None on load.
    """
    v = verify_section(_section("Yes"))
    assert "Singability check" not in _laws(v.findings)


# ---------------------------------------------------------------------------
# Stress — clash/lapse in the shipped line (Phase 3A)
# ---------------------------------------------------------------------------


def test_stress_clash_is_flagged():
    # true(1) love(1) burns(1) bright(1) -> 4 consecutive stressed syllables.
    v = verify_section(_section("True love burns bright and clear tonight"))
    assert any(f.law == "Stress check" and "stress clash" in f.detail for f in v.findings)


def test_stress_lapse_is_flagged():
    # the(0) a(0) in(0) and(0) the(0) -> 5 consecutive unstressed syllables.
    v = verify_section(_section("The a in and the story of it all"))
    assert any(f.law == "Stress check" and "lapse" in f.detail for f in v.findings)


def test_ordinary_line_has_no_stress_finding():
    v = verify_section(_section(ANCHOR))
    assert "Stress check" not in _laws(v.findings)


def test_function_words_do_not_manufacture_a_false_clash():
    """Regression test for a real bug found by testing against real
    output: the CMU dictionary marks isolated monosyllabic function words
    ("is", "of", "for", "to", "this", "that"...) as stressed, because a
    citation-form single syllable always carries its own primary stress.
    Read naively, a line dense with ordinary function words looked like a
    7-11-syllable stress clash. None of these words is stressed in real
    speech (function-word reduction), so a sentence built almost entirely
    from them must NOT trip the clash check.
    """
    v = verify_section(
        _section("Is this for you, or is it for this, of that, to this?")
    )
    assert not any(
        f.law == "Stress check" and "consecutive stressed" in f.detail
        for f in v.findings
    )


# ---------------------------------------------------------------------------
# target_language gating — the CMU-dictionary-backed checks above only
# understand English; a non-English target must skip them rather than
# silently mismeasuring a script they were never built for.
# ---------------------------------------------------------------------------


def test_english_target_still_runs_stress_and_singability_checks():
    v = verify_section(
        _section("True love burns bright and clear tonight"), target_language="English"
    )
    assert any(f.law == "Stress check" for f in v.findings)


def test_non_english_target_skips_stress_and_singability_checks():
    """A line that would trip the stress-clash heuristic if read as English
    must not, once it's understood to be a different target language —
    the CMU dictionary has no opinion about non-English text, and running
    it anyway would silently fabricate a measurement, not report one."""
    v = verify_section(
        _section("True love burns bright and clear tonight", source_syllable_count=4),
        target_language="Hindi",
    )
    assert "Stress check" not in _laws(v.findings)
    assert "Singability check" not in _laws(v.findings)
    assert v.rhyme_density is None


def test_verify_result_reads_target_language_from_the_stored_dict():
    section = _section("True love burns bright and clear tonight")
    result_dict = {
        "target_language": "Korean",
        "sections": [section.model_dump()],
        "source_sections": [],
    }
    report = verify_result(result_dict)
    assert "Stress check" not in _laws(report.sections[0].findings)


def test_verify_result_defaults_to_english_when_target_language_is_absent():
    """Older stored results predate this field entirely — must behave
    exactly as before rather than silently going quiet."""
    section = _section("True love burns bright and clear tonight")
    result_dict = {"sections": [section.model_dump()], "source_sections": []}
    report = verify_result(result_dict)
    assert any(f.law == "Stress check" for f in report.sections[0].findings)


def test_urdu_target_skips_every_cmu_backed_check():
    """No CMU dictionary for Urdu — same gate as Hindi/Korean above, and
    the song-level Sim_pho correlation must stay unset too, not just the
    per-section checks."""
    section = _section("دل", source_syllable_count=1)
    result_dict = {
        "target_language": "Urdu",
        "sections": [section.model_dump()],
        "source_sections": [],
    }
    report = verify_result(result_dict)
    v = report.sections[0]
    assert "Stress check" not in _laws(v.findings)
    assert "Singability check" not in _laws(v.findings)
    assert v.rhyme_density is None
    assert report.phoneme_repetition_similarity is None


def test_urdu_target_computes_phrase_end_sustainability_when_unambiguous():
    """دل ends in ل, a liquid — not a stop, so it's answerable even
    without a diacritic (see engine/g2p_ur.py: both possible readings,
    bare-consonant-final or vowel-final via an unwritten ending, agree)."""
    v = verify_section(_section("دل"), target_language="Urdu")
    assert v.phrase_end_sustainability == "sustainable"


def test_urdu_target_declines_phrase_end_sustainability_for_ambiguous_ending():
    """کتاب ends in ب, a bare stop with no diacritic — genuinely
    ambiguous (an unwritten izafat vowel could make this word actually
    end open), so it must report None rather than assert "closed"."""
    v = verify_section(_section("کتاب"), target_language="Urdu")
    assert v.phrase_end_sustainability is None


# ---------------------------------------------------------------------------
# Phoneme repetition similarity — adapted from Kim et al. 2023 (ISMIR),
# song-level (a correlation across sections), not per-section.
# ---------------------------------------------------------------------------


def test_verify_result_computes_phoneme_repetition_similarity_for_english():
    repetitive = "la la la la la la"
    varied = "the quick brown fox jumps over the lazy dog"
    sections = [
        _section(repetitive, anchor=repetitive, name="verse_1"),
        _section(varied, anchor=varied, name="verse_2"),
        _section(repetitive, anchor=repetitive, name="chorus"),
        _section(varied, anchor=varied, name="bridge"),
    ]
    result_dict = {
        "target_language": "English",
        "sections": [s.model_dump() for s in sections],
        "source_sections": [],
    }
    report = verify_result(result_dict)
    assert report.phoneme_repetition_similarity == 1.0


def test_verify_result_skips_phoneme_repetition_similarity_for_non_english():
    """No CMU dictionary for Korean text - same gate as Stress/Singability."""
    section = _section("True love burns bright and clear tonight")
    result_dict = {
        "target_language": "Korean",
        "sections": [section.model_dump()],
        "source_sections": [],
    }
    report = verify_result(result_dict)
    assert report.phoneme_repetition_similarity is None


def test_verify_result_phoneme_repetition_similarity_is_none_with_too_few_sections():
    section = _section("True love burns bright and clear tonight")
    result_dict = {
        "target_language": "English",
        "sections": [section.model_dump()],
        "source_sections": [],
    }
    report = verify_result(result_dict)
    assert report.phoneme_repetition_similarity is None


# ---------------------------------------------------------------------------
# Rhyme density — measured, never judged (Phase 3B)
# ---------------------------------------------------------------------------


def test_rhyme_density_is_computed_and_reported():
    final = (
        "I wonder why it's true\n"
        "the sky is always blue\n"
        "nothing here is new\n"
        "the old and something though"
    )
    v = verify_section(_section(final))
    assert v.rhyme_density == 0.75
    # Measured, but never turned into a Finding — no threshold exists.
    assert "Rhyme" not in _laws(v.findings)


def test_rhyme_density_is_none_when_unresolvable():
    v = verify_section(_section("one single line only"))
    assert v.rhyme_density is None


def test_summary_reports_rhyme_density_as_measured_not_judged():
    final = (
        "I wonder why it's true\n"
        "the sky is always blue\n"
        "nothing here is new\n"
        "the old and something though"
    )
    report = verify_result({"sections": [_section(final).model_dump()]})
    summary = report.summary()
    assert "Rhyme density" in summary
    assert "NOT judged" in summary


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


def test_missing_translator_anchor_is_unverifiable_not_a_crash():
    v = verify_section(_section("anything at all", with_anchor=False))
    assert v.verifiable is False
    assert v.findings[0].law == "verifiability"


# ---------------------------------------------------------------------------
# Completeness — the shipped line compared against its own siblings, not
# the (usually English) anchor
# ---------------------------------------------------------------------------


def _section_with_candidates(final_line: str, sibling_lengths: list[int]) -> SectionResultV1:
    """Like _section, but with several creative_adapter siblings of the
    given char lengths (instead of just one, whose text always equals
    final_line and would make the completeness ratio trivially 1.0)."""
    candidates = [Candidate(id="a1", agent="translator", text=ANCHOR, round="generation")]
    for i, length in enumerate(sibling_lengths):
        candidates.append(
            Candidate(
                id=f"c{i}",
                agent="creative_adapter",
                text="x" * length,
                round="generation",
                philosophy="maximum_fidelity",
            )
        )
    return SectionResultV1(
        section="verse_1",
        candidates=candidates,
        routing_signals={},
        ruling=JudgeRuling(
            section="verse_1",
            final_line=final_line,
            priority_tradeoffs_made="test",
            deviations=[],
            invention_penalty=0.0,
        ),
    )


def test_severely_truncated_final_line_is_flagged():
    # Reproduces the real Japanese-target failure: a ~20-character shipped
    # line against ~300-character creative_adapter siblings.
    result = _section_with_candidates("x" * 20, [300, 310, 295])
    v = verify_section(result)
    findings = [f for f in v.findings if f.law == "completeness"]
    assert len(findings) == 1
    assert findings[0].severity == "error"


def test_final_line_close_to_sibling_length_is_not_flagged():
    result = _section_with_candidates("x" * 90, [100, 95, 105])
    v = verify_section(result)
    assert not [f for f in v.findings if f.law == "completeness"]


def test_short_siblings_do_not_trigger_the_completeness_check():
    # Median well under _COMPLETENESS_MIN_MEDIAN — too small to mean
    # anything, so the check should stay quiet rather than flag noise.
    result = _section_with_candidates("x" * 5, [20, 22, 18])
    v = verify_section(result)
    assert not [f for f in v.findings if f.law == "completeness"]


def test_no_creative_adapter_candidates_skips_completeness_check():
    result = _section("x" * 5, with_anchor=True)
    v = verify_section(result)
    # The default _section fixture has exactly one creative_adapter
    # candidate whose text equals final_line, so ratio is always 1.0 —
    # this asserts that shape stays quiet, not that the check is skipped.
    assert not [f for f in v.findings if f.law == "completeness"]


# ---------------------------------------------------------------------------
# Structural recurrence — a formal device Song DNA never tagged as a motif
# ---------------------------------------------------------------------------


def test_structural_recurrence_break_is_flagged():
    """Reproduces the real failure from the Ghalib ghazal run: three
    couplets share a radif ("kya hai") that Song DNA never tagged as a
    motif, so Law 5 had nothing to check. Two final lines close on a
    copular "what is X" question; the third breaks the pattern with a
    non-copular "why does X" question — the actual sher_3 failure.
    """
    result = {
        "sections": [
            _section(
                "So tell me, what is this way of conversing?", name="sher_1"
            ).model_dump(),
            _section(
                "Just tell me, what is that fierce, enchanting charm?", name="sher_2"
            ).model_dump(),
            _section(
                "Else, why fear a corrupting rival?", name="sher_3"
            ).model_dump(),
        ],
        "source_sections": [
            {"name": "sher_1", "source_text": "line one\nतुम्हीं कहो कि ये अंदाज़-ए-गुफ़्तुगू क्या है"},
            {"name": "sher_2", "source_text": "line one\nकोई बताओ कि वो शोख़-ए-तुंद-ख़ू क्या है"},
            {"name": "sher_3", "source_text": "line one\nवगर्ना ख़ौफ़-ए-बद-आमोज़ी-ए-अदू क्या है"},
        ],
    }
    report = verify_result(result)
    findings = [f for f in report.cross_section_findings if f.law == "Structural recurrence"]
    assert len(findings) == 1
    assert findings[0].section == "sher_3"
    assert "copula" in findings[0].detail


def test_structural_recurrence_stays_quiet_when_the_pattern_holds():
    result = {
        "sections": [
            _section(
                "So tell me, what is this way of conversing?", name="sher_1"
            ).model_dump(),
            _section(
                "Just tell me, what is that fierce, enchanting charm?", name="sher_2"
            ).model_dump(),
            _section(
                "Tell me plainly, what is this rival's charm?", name="sher_3"
            ).model_dump(),
        ],
        "source_sections": [
            {"name": "sher_1", "source_text": "line one\nतुम्हीं कहो कि ये अंदाज़-ए-गुफ़्तुगू क्या है"},
            {"name": "sher_2", "source_text": "line one\nकोई बताओ कि वो शोख़-ए-तुंद-ख़ू क्या है"},
            {"name": "sher_3", "source_text": "line one\nवगर्ना ख़ौफ़-ए-बद-आमोज़ी-ए-अदू क्या है"},
        ],
    }
    report = verify_result(result)
    assert [f for f in report.cross_section_findings if f.law == "Structural recurrence"] == []


def test_structural_recurrence_check_is_a_noop_without_source_sections():
    """Backwards compatibility: older result.json files with no
    "source_sections" key must verify exactly as they did before this
    check existed.
    """
    result = {
        "sections": [
            _adapted_section("sher_1").model_dump(),
            _adapted_section("sher_2").model_dump(),
            _adapted_section("sher_3").model_dump(),
        ]
    }
    report = verify_result(result)
    assert [f for f in report.cross_section_findings if f.law == "Structural recurrence"] == []


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
