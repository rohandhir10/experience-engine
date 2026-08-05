"""Tests for engine/comics_vision.py and server/main.py's merge of a
vision-LLM reading into the Cloud Vision OCR result.

No model and no network: the vision client is stubbed. The behavior that
actually matters here is what happens when things go WRONG - the OCR
result the user asked for must survive every failure mode of the
enrichment layered on top of it.
"""
from __future__ import annotations

import pytest

from engine import comics_vision, config
from engine.comics_align import Reading
from server.main import _merge_vision_readings


@pytest.fixture
def vision_enabled(monkeypatch):
    monkeypatch.setattr(config, "VISION_READING_ENABLED", True)


def _ocr_result(*texts: str) -> dict:
    return {
        "regions": [
            {"text": t, "bbox": {"x": i, "y": 0, "width": 10, "height": 5}, "confidence": 80.0}
            for i, t in enumerate(texts)
        ],
        "full_text": "\n\n".join(texts),
        "warning": None,
        "image_width": 100,
        "image_height": 100,
        "detected_languages": [],
    }


# --- _parse_readings: never trust the shape of model output ---------------


def test_parse_reads_a_well_formed_narrative_node():
    readings = comics_vision._parse_readings(
        {
            "text_nodes": [
                {
                    "node_id": "r1",
                    "text": "HOLD ON",
                    "kind": "shout",
                    "reading_index": 2,
                    "speaker": "Character_A",
                    "speaker_confidence": 0.9,
                    "speaker_appearance": "tall, dark bob, red jacket",
                    "speaker_visible": True,
                    "tone": "urgent",
                    "tone_note": "shouted across a gap",
                    "emphasis": "large",
                }
            ]
        }
    )
    node = readings[0]
    assert node.text == "HOLD ON"
    assert node.kind == "shout"
    assert node.speaker == "Character_A"
    assert node.speaker_confidence == 0.9
    assert node.speaker_appearance == "tall, dark bob, red jacket"
    assert node.tone == "urgent"
    assert node.tone_note == "shouted across a gap"
    assert node.emphasis == "large"
    assert node.reading_index == 2
    assert node.node_id == "r1"


@pytest.mark.parametrize(
    "field,bad_value,attr,expected",
    [
        ("kind", "shouting-in-a-cave", "kind", "unknown"),
        ("tone", "wistful-but-hungry", "tone", "neutral"),
        ("emphasis", "sparkly", "emphasis", "normal"),
    ],
)
def test_values_outside_the_vocabulary_are_downgraded(field, bad_value, attr, expected):
    """Downstream code groups and filters on these, so it can only rely
    on the vocabulary if out-of-set values never pass through.
    """
    readings = comics_vision._parse_readings(
        {"text_nodes": [{"text": "HI", field: bad_value}]}
    )
    assert getattr(readings[0], attr) == expected


@pytest.mark.parametrize(
    "bad", ["high", None, True, float("nan"), float("inf"), float("-inf"), {}, []]
)
def test_a_malformed_confidence_never_reads_as_certain(bad):
    """The field exists to let a guess be distrusted. A broken value
    must land at 0, never at something a threshold would wave through.
    """
    readings = comics_vision._parse_readings(
        {"text_nodes": [{"text": "HI", "speaker": "Character_A", "speaker_confidence": bad}]}
    )
    # Asserting only the RANGE here was not enough: NaN slipped through
    # min/max clamping as 1.0 and the weaker assertion passed. Every
    # malformed value must land at exactly 0.
    assert readings[0].speaker_confidence == 0.0


def test_an_out_of_range_numeric_confidence_is_clamped_not_zeroed():
    """A real number outside 0-1 is a scale mistake, not corruption -
    clamp it. Distinct from the malformed cases above, which must zero.
    """
    high = comics_vision._parse_readings(
        {"text_nodes": [{"text": "HI", "speaker": "Character_A", "speaker_confidence": 42}]}
    )
    assert high[0].speaker_confidence == 1.0
    low = comics_vision._parse_readings(
        {"text_nodes": [{"text": "HI", "speaker": "Character_A", "speaker_confidence": -5}]}
    )
    assert low[0].speaker_confidence == 0.0


def test_no_speaker_forces_confidence_to_zero():
    readings = comics_vision._parse_readings(
        {"text_nodes": [{"text": "KRAKOOM", "kind": "sfx", "speaker_confidence": 0.99}]}
    )
    assert readings[0].speaker is None
    assert readings[0].speaker_confidence == 0.0


def test_a_blank_speaker_is_no_speaker():
    readings = comics_vision._parse_readings(
        {"text_nodes": [{"text": "HI", "kind": "speech", "speaker": "   "}]}
    )
    assert readings[0].speaker is None


def test_speaker_visible_defaults_true_and_honours_an_explicit_false():
    off_panel = comics_vision._parse_readings(
        {"text_nodes": [{"text": "HI", "speaker_visible": False}]}
    )
    assert off_panel[0].speaker_visible is False
    default = comics_vision._parse_readings({"text_nodes": [{"text": "HI"}]})
    assert default[0].speaker_visible is True


def test_a_missing_reading_index_falls_back_to_listed_order():
    readings = comics_vision._parse_readings(
        {"text_nodes": [{"text": "FIRST"}, {"text": "SECOND"}]}
    )
    assert [r.reading_index for r in readings] == [1, 2]


def test_nodes_with_no_usable_text_are_dropped():
    readings = comics_vision._parse_readings(
        {"text_nodes": [{"text": ""}, {"text": "   "}, {"kind": "sfx"}, {"text": "REAL"}]}
    )
    assert [r.text for r in readings] == ["REAL"]


@pytest.mark.parametrize(
    "payload",
    [{}, {"text_nodes": None}, {"text_nodes": "not a list"}, {"text_nodes": [1, 2]},
     {"readings": [{"text": "old schema key"}]}],
)
def test_malformed_replies_yield_nothing(payload):
    assert comics_vision._parse_readings(payload) == []


# --- grounding: the optional node_id path --------------------------------


def test_known_regions_are_offered_to_the_model_with_their_ids():
    block = comics_vision._known_regions_block(
        [{"node_id": "r0", "text": "H0LD 0N"}, {"node_id": "r1", "text": ""}]
    )
    assert "r0: H0LD 0N" in block
    assert "r1: (no OCR text)" in block
    # The OCR text is a hint to correct, never an answer to trust.
    assert "do not trust it" in block


def test_no_known_regions_adds_nothing_to_the_prompt():
    assert comics_vision._known_regions_block(None) == ""
    assert comics_vision._known_regions_block([]) == ""


def test_a_grounded_reply_keeps_the_node_id_for_exact_alignment():
    readings = comics_vision._parse_readings(
        {"text_nodes": [{"node_id": "r7", "text": "HI"}]}
    )
    assert readings[0].node_id == "r7"


# --- read_panel: every failure degrades to OCR-only, never raises ---------


def test_read_panel_returns_nothing_when_the_feature_is_disabled(monkeypatch):
    monkeypatch.setattr(config, "VISION_READING_ENABLED", False)

    def _explode():
        raise AssertionError("must not build a client when disabled")

    monkeypatch.setattr("engine.llm_client.create_vision_client", _explode)
    assert comics_vision.read_panel(b"bytes") == []


def test_read_panel_degrades_when_no_client_can_be_built(monkeypatch, vision_enabled):
    # The realistic case: no API key configured on this deployment.
    monkeypatch.setattr(
        "engine.llm_client.create_vision_client",
        lambda: (_ for _ in ()).throw(RuntimeError("no api key")),
    )
    assert comics_vision.read_panel(b"bytes") == []


def test_read_panel_degrades_when_the_model_call_fails(monkeypatch, vision_enabled):
    class _Failing:
        def complete_json_with_image(self, *a, **k):
            raise RuntimeError("upstream 500")

    monkeypatch.setattr("engine.llm_client.create_vision_client", lambda: _Failing())
    assert comics_vision.read_panel(b"bytes") == []


def test_read_panel_sends_the_image_as_a_data_url(monkeypatch, vision_enabled):
    captured = {}

    class _Recording:
        def complete_json_with_image(self, system, user, image_data_url, **kwargs):
            captured["url"] = image_data_url
            captured["stage"] = kwargs.get("stage")
            return {"text_nodes": [{"text": "HI", "kind": "speech"}]}

    monkeypatch.setattr("engine.llm_client.create_vision_client", lambda: _Recording())
    readings = comics_vision.read_panel(b"abc", mime_type="image/png")

    assert captured["url"].startswith("data:image/png;base64,")
    assert captured["stage"] == "comics_vision_read"
    assert readings[0].text == "HI"


# --- _merge_vision_readings: the OCR result must survive intact -----------


def test_merge_is_a_no_op_without_readings():
    original = _ocr_result("A", "B")
    assert _merge_vision_readings(original, []) is original


def test_merge_replaces_text_but_never_the_bounding_box():
    """The single most important invariant here. Boxes come from Cloud
    Vision because the redraw path needs real geometry; a vision model's
    idea of coordinates must never reach them.
    """
    result = _ocr_result("H0LD 0N TlGHT")
    box_before = dict(result["regions"][0]["bbox"])

    merged = _merge_vision_readings(
        result, [Reading(text="HOLD ON TIGHT", kind="dialogue", speaker="Mira")]
    )
    region = merged["regions"][0]

    assert region["text"] == "HOLD ON TIGHT"
    assert region["bbox"] == box_before
    assert region["text_source"] == "llm"
    assert region["speaker"] == "Mira"


def test_merge_keeps_ocr_text_for_a_region_the_model_did_not_match():
    merged = _merge_vision_readings(
        _ocr_result("SOMETHING ELSE ENTIRELY"), [Reading(text="HOLD ON TIGHT")]
    )
    assert merged["regions"][0]["text"] == "SOMETHING ELSE ENTIRELY"
    assert merged["regions"][0]["text_source"] == "vision"
    assert merged["vision_corrected_count"] == 0


def test_merge_rebuilds_full_text_from_the_corrected_regions():
    merged = _merge_vision_readings(
        _ocr_result("HELL0", "W0RLD"),
        [Reading(text="HELLO"), Reading(text="WORLD")],
    )
    assert merged["full_text"] == "HELLO\n\nWORLD"
    assert merged["vision_corrected_count"] == 2


def test_merge_reports_readings_that_had_no_box_separately():
    """A bubble Cloud Vision missed has no geometry, so it can't be
    placed or redrawn - but dropping it silently would hide a real gap.
    """
    merged = _merge_vision_readings(
        _ocr_result("HELL0"),
        [Reading(text="HELLO"), Reading(text="A MISSED BUBBLE", kind="dialogue")],
    )
    assert len(merged["regions"]) == 1
    assert merged["unplaced_readings"] == [
        {"text": "A MISSED BUBBLE", "kind": "dialogue", "speaker": None}
    ]
    # Unplaced text must NOT leak into full_text, which is positional.
    assert "A MISSED BUBBLE" not in merged["full_text"]


def test_merge_preserves_region_count_and_order():
    merged = _merge_vision_readings(
        _ocr_result("A", "B", "C"), [Reading(text="B")]
    )
    assert len(merged["regions"]) == 3
    assert merged["regions"][1]["text_source"] == "llm"
    assert [r["bbox"]["x"] for r in merged["regions"]] == [0, 1, 2]
