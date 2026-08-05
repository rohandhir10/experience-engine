"""Tests for engine/comics_align.py — matching a vision-LLM's reading of
a panel back to Cloud Vision's boxes.

No model involved: every test hands the aligner fixed strings. This is
the part of the vision-LLM pass that has to be right (a mis-pairing puts
one bubble's dialogue in another bubble's box, and the redraw path would
then erase and re-letter the wrong artwork), so it's deliberately the
part built as pure logic.
"""
from __future__ import annotations

from engine.comics_align import (
    DEFAULT_MIN_SIMILARITY,
    Reading,
    align_readings,
    normalize,
    similarity,
)


def test_similarity_is_high_for_a_garbled_ocr_read_of_the_same_line():
    # The everyday case this whole module exists for: Cloud Vision
    # misreading stylized lettering, but recognisably the same text.
    assert similarity("H0LD 0N TlGHT", "HOLD ON TIGHT") > DEFAULT_MIN_SIMILARITY


def test_similarity_is_low_for_genuinely_different_lines():
    assert similarity("I never wanted this", "Get out of my house") < DEFAULT_MIN_SIMILARITY


def test_similarity_ignores_punctuation_and_case():
    assert similarity("hold on, tight!", "HOLD ON TIGHT") > 0.95


def test_empty_text_is_never_a_match():
    # Two empty strings are no information, not a perfect pairing.
    assert similarity("", "") == 0.0
    assert similarity("", "anything") == 0.0


def test_normalize_keeps_non_latin_script():
    # Stripping to ASCII would collapse a Japanese panel to "" and make
    # every bubble match every other one equally.
    assert normalize("こんにちは！") == "こんにちは"
    assert normalize("안녕하세요") == "안녕하세요"


def test_a_confident_match_replaces_vision_text_with_the_llm_reading():
    result = align_readings(
        ["H0LD 0N TlGHT"], [Reading(text="HOLD ON TIGHT", kind="dialogue", speaker="Mira")]
    )
    region = result.regions[0]
    assert region.text == "HOLD ON TIGHT"
    assert region.source == "llm"
    assert region.speaker == "Mira"
    assert region.kind == "dialogue"
    assert result.corrected_count == 1


def test_an_unmatched_region_keeps_the_ocr_text_rather_than_guessing():
    result = align_readings(
        ["SOMETHING ENTIRELY DIFFERENT"], [Reading(text="HOLD ON TIGHT")]
    )
    region = result.regions[0]
    assert region.text == "SOMETHING ENTIRELY DIFFERENT"
    assert region.source == "vision"
    assert region.similarity == 0.0
    assert result.corrected_count == 0


def test_matching_is_by_content_not_position():
    """Reading order in comics is not solved - manga runs right-to-left,
    and bubbles can be laid out in a Z. Pairing nth-to-nth would be
    wrong exactly where this feature matters.
    """
    result = align_readings(
        ["G0DBYE F0REVER", "HELL0 THERE"],
        [Reading(text="HELLO THERE"), Reading(text="GOODBYE FOREVER")],
    )
    assert result.regions[0].text == "GOODBYE FOREVER"
    assert result.regions[1].text == "HELLO THERE"
    assert all(r.source == "llm" for r in result.regions)


def test_each_reading_is_used_at_most_once():
    """Two similar-looking bubbles must not both claim the same reading -
    the weaker match keeps its OCR text instead.
    """
    result = align_readings(
        ["HOLD ON TIGHT", "HOLD ON TIGHT!!"], [Reading(text="HOLD ON TIGHT")]
    )
    sources = [r.source for r in result.regions]
    assert sources.count("llm") == 1
    assert sources.count("vision") == 1


def test_the_better_of_two_competing_regions_wins_the_reading():
    result = align_readings(
        ["COMPLETELY UNRELATED LINE", "H0LD 0N TIGHT"],
        [Reading(text="HOLD ON TIGHT")],
    )
    assert result.regions[1].source == "llm"
    assert result.regions[0].source == "vision"


def test_readings_with_no_matching_region_are_reported_not_dropped():
    """Usually means Cloud Vision missed a bubble outright. There's no
    box for it, so it can't be placed or redrawn - but silently
    discarding text the LLM genuinely read would hide a real gap.
    """
    result = align_readings(
        ["HELL0 THERE"],
        [Reading(text="HELLO THERE"), Reading(text="A BUBBLE VISION MISSED")],
    )
    assert len(result.unplaced) == 1
    assert result.unplaced[0].text == "A BUBBLE VISION MISSED"


def test_no_readings_at_all_leaves_every_region_on_ocr_text():
    # The degraded path: the vision call failed or returned nothing.
    # Every region must still come back, carrying its OCR draft.
    result = align_readings(["ONE", "TWO"], [])
    assert [r.text for r in result.regions] == ["ONE", "TWO"]
    assert all(r.source == "vision" for r in result.regions)


def test_no_regions_at_all_returns_nothing_placed():
    result = align_readings([], [Reading(text="HELLO")])
    assert result.regions == []
    assert len(result.unplaced) == 1


def test_sfx_classification_is_carried_through():
    result = align_readings(["KRAK00M"], [Reading(text="KRAKOOM", kind="sfx")])
    assert result.regions[0].kind == "sfx"


def test_speaker_stays_none_when_the_model_would_not_commit():
    result = align_readings(
        ["HELL0"], [Reading(text="HELLO", kind="dialogue", speaker=None)]
    )
    assert result.regions[0].speaker is None


def test_alignment_is_deterministic_for_identical_input():
    """Equal scores must resolve the same way every run, or the same
    panel produces different scripts on re-OCR.
    """
    args = (
        ["SAME TEXT", "SAME TEXT"],
        [Reading(text="SAME TEXT"), Reading(text="SAME TEXT")],
    )
    first = [(r.index, r.text, r.source) for r in align_readings(*args).regions]
    for _ in range(5):
        assert [(r.index, r.text, r.source) for r in align_readings(*args).regions] == first


def test_raising_the_threshold_makes_matching_stricter():
    garbled = ["H0LD 0N TlGHT"]
    readings = [Reading(text="HOLD ON TIGHT")]
    assert align_readings(garbled, readings, min_similarity=0.3).corrected_count == 1
    assert align_readings(garbled, readings, min_similarity=0.99).corrected_count == 0


def test_region_order_and_count_are_always_preserved():
    """Downstream code indexes regions positionally against their
    bounding boxes (engine/comics_redraw.py, PanelWorkspace.tsx), so
    this function must never reorder, add, or drop one.
    """
    vision = ["A", "B", "C", "D"]
    result = align_readings(vision, [Reading(text="B")])
    assert [r.index for r in result.regions] == [0, 1, 2, 3]
    assert len(result.regions) == len(vision)


# ---------------------------------------------------------------------------
# Exact alignment by node_id — the payoff of detecting boxes BEFORE
# reading them. When the detector supplies ids and the model keys its
# answer to them, no similarity guessing is involved at all.
# ---------------------------------------------------------------------------


def test_node_ids_pair_exactly_even_when_the_text_looks_nothing_alike():
    """The case fuzzy matching cannot handle: a bubble so badly garbled
    by the recogniser that no similarity score would ever pair it. The
    id settles it outright.
    """
    result = align_readings(
        ["#@!%^&*"],
        [Reading(text="I never wanted any of this", node_id="r0")],
        node_ids=["r0"],
    )
    assert result.regions[0].text == "I never wanted any of this"
    assert result.regions[0].source == "llm"
    assert result.regions[0].similarity == 1.0


def test_node_ids_win_over_a_better_looking_fuzzy_match():
    """An id is stated identity; similarity is only ever an inference.
    A high-scoring lookalike must not be able to steal a keyed reading.
    """
    result = align_readings(
        ["HELLO THERE", "GOODBYE"],
        [Reading(text="HELLO THERE", node_id="r1")],
        node_ids=["r0", "r1"],
    )
    # Reading is keyed to r1, so region 1 takes it despite region 0 being
    # a perfect textual match.
    assert result.regions[1].source == "llm"
    assert result.regions[0].source == "vision"


def test_unkeyed_readings_still_fall_back_to_fuzzy_matching():
    """A mixed reply: one node keyed, one not. Both should land."""
    result = align_readings(
        ["G0DBYE F0REVER", "ANYTHING AT ALL"],
        [
            Reading(text="GOODBYE FOREVER"),
            Reading(text="KEYED LINE", node_id="r1"),
        ],
        node_ids=["r0", "r1"],
    )
    assert result.regions[1].text == "KEYED LINE"
    assert result.regions[1].similarity == 1.0
    assert result.regions[0].text == "GOODBYE FOREVER"
    assert 0 < result.regions[0].similarity < 1.0


def test_an_unknown_node_id_does_not_crash_or_mispair():
    """The model inventing an id the detector never issued must not
    place that reading anywhere.
    """
    result = align_readings(
        ["REAL REGION"],
        [Reading(text="INVENTED", node_id="r99")],
        node_ids=["r0"],
    )
    assert result.regions[0].source == "vision"
    assert len(result.unplaced) == 1


def test_two_readings_claiming_one_node_id_only_place_the_first():
    result = align_readings(
        ["REGION"],
        [Reading(text="FIRST", node_id="r0"), Reading(text="SECOND", node_id="r0")],
        node_ids=["r0"],
    )
    assert result.regions[0].text == "FIRST"
    assert [r.text for r in result.unplaced] == ["SECOND"]


def test_the_matched_reading_is_carried_through_whole():
    """Narrative fields (tone, emphasis, confidence, appearance) have to
    reach the caller, or Phase 1's schema was pointless.
    """
    reading = Reading(
        text="HOLD ON",
        kind="shout",
        speaker="Character_A",
        speaker_confidence=0.9,
        speaker_appearance="tall, red jacket",
        tone="urgent",
        emphasis="large",
        node_id="r0",
    )
    result = align_readings(["H0LD 0N"], [reading], node_ids=["r0"])
    carried = result.regions[0].reading
    assert carried is not None
    assert carried.tone == "urgent"
    assert carried.emphasis == "large"
    assert carried.speaker_confidence == 0.9
    assert carried.speaker_appearance == "tall, red jacket"


def test_node_ids_are_ignored_when_none_are_supplied():
    # Cold-read path: ids on the readings but no detector list to key
    # against. Must fall through to fuzzy rather than silently drop.
    result = align_readings(
        ["HELL0 THERE"], [Reading(text="HELLO THERE", node_id="r0")], node_ids=None
    )
    assert result.regions[0].source == "llm"
