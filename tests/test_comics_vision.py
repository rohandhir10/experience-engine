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


def test_parse_readings_reads_a_well_formed_reply():
    readings = comics_vision._parse_readings(
        {"readings": [{"text": "HOLD ON", "kind": "dialogue", "speaker": "Mira"}]}
    )
    assert readings == [Reading(text="HOLD ON", kind="dialogue", speaker="Mira")]


def test_parse_readings_downgrades_an_unrecognised_kind():
    # Downstream filtering (e.g. "leave sfx out of the script") can only
    # rely on the vocabulary if unknown values never pass through.
    readings = comics_vision._parse_readings(
        {"readings": [{"text": "HI", "kind": "shouting-in-a-cave"}]}
    )
    assert readings[0].kind == "unknown"


def test_parse_readings_treats_a_blank_speaker_as_no_speaker():
    readings = comics_vision._parse_readings(
        {"readings": [{"text": "HI", "kind": "dialogue", "speaker": "   "}]}
    )
    assert readings[0].speaker is None


def test_parse_readings_drops_entries_with_no_usable_text():
    readings = comics_vision._parse_readings(
        {"readings": [{"text": ""}, {"text": "   "}, {"kind": "sfx"}, {"text": "REAL"}]}
    )
    assert [r.text for r in readings] == ["REAL"]


@pytest.mark.parametrize(
    "payload", [{}, {"readings": None}, {"readings": "not a list"}, {"readings": [1, 2]}]
)
def test_parse_readings_survives_malformed_replies(payload):
    assert comics_vision._parse_readings(payload) == []


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
            return {"readings": [{"text": "HI", "kind": "dialogue"}]}

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
