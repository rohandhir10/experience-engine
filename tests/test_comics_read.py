"""Tests for the two-step panel read: detect, then recognise and direct
in parallel, aligned on node_id.

No models and no network. Detectors and recognisers are Protocols, so a
test can supply a two-line stand-in for either - which is the practical
payoff of putting a boundary there rather than calling Cloud Vision
inline.
"""
from __future__ import annotations

import threading
import time

import pytest

from engine import comics_read, comics_recognize, comics_vision
from engine.comics_align import Reading
from engine.comics_detect import DetectedBox, parse_detector_payload
from engine.comics_recognize import assign_by_overlap, parse_recognizer_payload


def _box(node_id: str, x: int = 0, y: int = 0, w: int = 100, h: int = 50, conf: float = 0.9):
    return DetectedBox(node_id=node_id, x=x, y=y, width=w, height=h, confidence=conf)


class _StubDetector:
    def __init__(self, boxes, error: Exception | None = None):
        self._boxes = boxes
        self._error = error

    def detect(self, image_bytes):
        if self._error:
            raise self._error
        return self._boxes


class _StubRecognizer:
    def __init__(self, texts=None, error: Exception | None = None, delay: float = 0.0):
        self._texts = texts or {}
        self._error = error
        self._delay = delay

    def recognize(self, image_bytes, boxes):
        if self._delay:
            time.sleep(self._delay)
        if self._error:
            raise self._error
        return self._texts


@pytest.fixture
def no_vision(monkeypatch):
    """Default: the narrative pass is off, so tests exercise the
    detect+recognise path alone unless they opt in."""
    monkeypatch.setattr(comics_vision, "read_panel", lambda *a, **k: [])


# --- the core contract ----------------------------------------------------


def test_boxes_come_from_the_detector_and_are_never_altered(no_vision):
    boxes = [_box("r0", x=11, y=22, w=33, h=44)]
    result = comics_read.read_panel_two_step(
        b"img", detector=_StubDetector(boxes), recognizer=_StubRecognizer({"r0": "HELLO"})
    )
    region = result["regions"][0]
    assert region["bbox"] == {"x": 11, "y": 22, "width": 33, "height": 44}
    assert region["node_id"] == "r0"
    assert region["text"] == "HELLO"


def test_recogniser_text_lands_on_the_matching_box_by_id(no_vision):
    boxes = [_box("r0"), _box("r1", y=100)]
    result = comics_read.read_panel_two_step(
        b"img",
        detector=_StubDetector(boxes),
        recognizer=_StubRecognizer({"r1": "SECOND", "r0": "FIRST"}),
    )
    assert [r["text"] for r in result["regions"]] == ["FIRST", "SECOND"]


def test_the_vision_reading_wins_on_a_shared_node_id(no_vision, monkeypatch):
    """The whole point of keying both readers to the detector's ids: a
    badly-garbled recogniser result is replaced with certainty, not by a
    similarity guess that could fail on exactly this input.
    """
    monkeypatch.setattr(
        comics_vision,
        "read_panel",
        lambda *a, **k: [Reading(text="I never wanted this", node_id="r0", kind="speech")],
    )
    result = comics_read.read_panel_two_step(
        b"img", detector=_StubDetector([_box("r0")]), recognizer=_StubRecognizer({"r0": "#@!%^"})
    )
    region = result["regions"][0]
    assert region["text"] == "I never wanted this"
    assert region["text_source"] == "llm"
    assert result["vision_corrected_count"] == 1


def test_narrative_fields_reach_the_result(no_vision, monkeypatch):
    monkeypatch.setattr(
        comics_vision,
        "read_panel",
        lambda *a, **k: [
            Reading(
                text="HOLD ON",
                node_id="r0",
                kind="shout",
                speaker="Character_A",
                speaker_confidence=0.85,
                speaker_appearance="tall, red jacket",
                tone="urgent",
                emphasis="large",
                reading_index=1,
            )
        ],
    )
    result = comics_read.read_panel_two_step(
        b"img", detector=_StubDetector([_box("r0")]), recognizer=_StubRecognizer({"r0": "H0LD"})
    )
    region = result["regions"][0]
    assert region["kind"] == "shout"
    assert region["speaker"] == "Character_A"
    assert region["speaker_confidence"] == 0.85
    assert region["speaker_appearance"] == "tall, red jacket"
    assert region["tone"] == "urgent"
    assert region["emphasis"] == "large"


def test_reading_order_follows_the_narrative_pass_not_geometry(no_vision, monkeypatch):
    """Right-to-left and Z-pattern layouts are why this exists: the boxes
    stay in detector order (downstream indexes them positionally), and
    reading order is expressed separately.
    """
    monkeypatch.setattr(
        comics_vision,
        "read_panel",
        lambda *a, **k: [
            Reading(text="SECOND", node_id="r0", reading_index=2),
            Reading(text="FIRST", node_id="r1", reading_index=1),
        ],
    )
    result = comics_read.read_panel_two_step(
        b"img",
        detector=_StubDetector([_box("r0"), _box("r1", y=100)]),
        recognizer=_StubRecognizer({}),
    )
    assert [r["node_id"] for r in result["regions"]] == ["r0", "r1"]
    assert result["reading_order"] == ["r1", "r0"]
    assert result["full_text"] == "FIRST\n\nSECOND"


# --- concurrency: the architectural claim ---------------------------------


def test_recognition_and_the_vision_pass_run_concurrently(no_vision, monkeypatch):
    """If these were ever serialized this barrier would never fill and
    the test would time out rather than quietly pass slowly.
    """
    both_started = threading.Barrier(2, timeout=5)

    def fake_read_panel(image_bytes, mime_type="image/jpeg", known_regions=None):
        both_started.wait()
        return [Reading(text="READ", node_id="r0")]

    class _BarrierRecognizer:
        def recognize(self, image_bytes, boxes):
            both_started.wait()
            return {"r0": "OCR"}

    monkeypatch.setattr(comics_vision, "read_panel", fake_read_panel)
    result = comics_read.read_panel_two_step(
        b"img", detector=_StubDetector([_box("r0")]), recognizer=_BarrierRecognizer()
    )
    assert result["regions"][0]["text"] == "READ"


def test_the_vision_pass_is_given_the_detector_ids_to_key_against(no_vision, monkeypatch):
    captured = {}

    def fake_read_panel(image_bytes, mime_type="image/jpeg", known_regions=None):
        captured["ids"] = [r["node_id"] for r in (known_regions or [])]
        return []

    monkeypatch.setattr(comics_vision, "read_panel", fake_read_panel)
    comics_read.read_panel_two_step(
        b"img",
        detector=_StubDetector([_box("r0"), _box("r1")]),
        recognizer=_StubRecognizer({}),
    )
    assert captured["ids"] == ["r0", "r1"]


# --- degradation ----------------------------------------------------------


def test_a_failed_detector_returns_nothing_so_the_caller_can_fall_back(no_vision):
    result = comics_read.read_panel_two_step(
        b"img",
        detector=_StubDetector([], error=RuntimeError("detector down")),
        recognizer=_StubRecognizer({"r0": "X"}),
    )
    assert result == {}


def test_no_boxes_returns_nothing_rather_than_an_invented_empty_result(no_vision):
    result = comics_read.read_panel_two_step(
        b"img", detector=_StubDetector([]), recognizer=_StubRecognizer({})
    )
    assert result == {}


def test_a_failed_recogniser_still_ships_the_vision_reading(monkeypatch):
    monkeypatch.setattr(
        comics_vision, "read_panel", lambda *a, **k: [Reading(text="SAVED", node_id="r0")]
    )
    result = comics_read.read_panel_two_step(
        b"img",
        detector=_StubDetector([_box("r0")]),
        recognizer=_StubRecognizer(error=RuntimeError("model down")),
    )
    assert result["regions"][0]["text"] == "SAVED"


def test_both_readers_failing_still_returns_the_boxes_with_a_warning(no_vision):
    result = comics_read.read_panel_two_step(
        b"img",
        detector=_StubDetector([_box("r0")]),
        recognizer=_StubRecognizer(error=RuntimeError("down")),
    )
    assert len(result["regions"]) == 1
    assert result["regions"][0]["text"] == ""
    assert "none could be read" in result["warning"]


def test_a_partially_empty_read_is_reported_honestly(no_vision):
    result = comics_read.read_panel_two_step(
        b"img",
        detector=_StubDetector([_box("r0"), _box("r1")]),
        recognizer=_StubRecognizer({"r0": "READ"}),
    )
    assert "1 of 2" in result["warning"]


def test_a_fully_read_panel_carries_no_warning(no_vision):
    result = comics_read.read_panel_two_step(
        b"img",
        detector=_StubDetector([_box("r0")]),
        recognizer=_StubRecognizer({"r0": "READ"}),
    )
    assert result["warning"] is None


# --- recogniser routing ---------------------------------------------------


def test_japanese_routes_to_a_specialist_only_when_one_is_configured(monkeypatch):
    """manga-ocr is Japanese-only, so it is registered per script rather
    than swapped in globally - otherwise the other five languages in the
    roster would regress to nothing.
    """
    from engine import config

    monkeypatch.setattr(config, "MANGA_OCR_URL", "")
    monkeypatch.setattr(config, "MANGA_OCR_ENABLED", False)
    registry = comics_recognize.build_registry()
    assert type(comics_recognize.select_recognizer(registry, "ja")).__name__ == (
        "CloudVisionRecognizer"
    )

    monkeypatch.setattr(config, "MANGA_OCR_URL", "http://manga-ocr.internal/read")
    registry = comics_recognize.build_registry()
    assert type(comics_recognize.select_recognizer(registry, "ja")).__name__ == (
        "RemoteRecognizer"
    )


def test_a_remote_url_takes_precedence_over_the_in_process_model(monkeypatch):
    """Out-of-process is preferred: it keeps torch out of the API image."""
    from engine import config

    monkeypatch.setattr(config, "MANGA_OCR_ENABLED", True)
    monkeypatch.setattr(config, "MANGA_OCR_URL", "http://manga-ocr.internal/read")
    registry = comics_recognize.build_registry()
    assert type(registry["ja"]).__name__ == "RemoteRecognizer"


@pytest.mark.parametrize("code", ["ko", "es", "hi", "ur", "en", None, "", "zz"])
def test_every_other_script_keeps_the_general_recogniser(monkeypatch, code):
    from engine import config

    monkeypatch.setattr(config, "MANGA_OCR_URL", "http://manga-ocr.internal/read")
    registry = comics_recognize.build_registry()
    assert type(comics_recognize.select_recognizer(registry, code)).__name__ == (
        "CloudVisionRecognizer"
    )


def test_a_regional_code_still_routes_to_its_base_script(monkeypatch):
    from engine import config

    monkeypatch.setattr(config, "MANGA_OCR_URL", "http://manga-ocr.internal/read")
    registry = comics_recognize.build_registry()
    assert type(comics_recognize.select_recognizer(registry, "ja-JP")).__name__ == (
        "RemoteRecognizer"
    )


# --- untrusted payloads from out-of-process components --------------------


def test_detector_payload_drops_boxes_with_missing_coordinates():
    """A silently zero-sized box at the origin would send redraw at the
    top-left corner of the artwork, so a broken box is dropped, never
    defaulted.
    """
    boxes = parse_detector_payload(
        {
            "boxes": [
                {"x": 1, "y": 2, "width": 3, "height": 4},
                {"x": 1, "y": 2, "width": 3},
                {"x": "nonsense", "y": 2, "width": 3, "height": 4},
                {"x": 1, "y": 2, "width": 0, "height": 4},
            ]
        }
    )
    assert len(boxes) == 1
    assert boxes[0].node_id == "r0"


def test_detector_payload_honours_supplied_ids_and_issues_missing_ones():
    boxes = parse_detector_payload(
        {
            "boxes": [
                {"node_id": "bubble-7", "x": 0, "y": 0, "width": 1, "height": 1},
                {"x": 0, "y": 0, "width": 1, "height": 1},
            ]
        }
    )
    assert [b.node_id for b in boxes] == ["bubble-7", "r1"]


@pytest.mark.parametrize("payload", [{}, {"boxes": None}, {"boxes": "no"}, {"boxes": [1]}])
def test_malformed_detector_payloads_yield_nothing(payload):
    assert parse_detector_payload(payload) == []


@pytest.mark.parametrize(
    "payload", [{}, {"texts": None}, {"texts": []}, {"texts": {"a": 1}}, {"texts": {"a": "  "}}]
)
def test_malformed_recogniser_payloads_yield_nothing(payload):
    assert parse_recognizer_payload(payload) == {}


# --- mapping a page-level recogniser onto detector boxes ------------------


def test_overlap_assignment_pairs_by_area_not_by_index():
    """A page-level recogniser segments the page itself and will not
    return the detector's boxes, so the two orderings legitimately
    differ - pairing by position would scramble them.
    """
    boxes = [_box("r0", x=0, y=0, w=100, h=50), _box("r1", x=0, y=200, w=100, h=50)]
    regions = [
        {"text": "LOWER", "bbox": {"x": 0, "y": 205, "width": 100, "height": 40}},
        {"text": "UPPER", "bbox": {"x": 0, "y": 5, "width": 100, "height": 40}},
    ]
    assert assign_by_overlap(boxes, regions) == {"r0": "UPPER", "r1": "LOWER"}


def test_overlap_assignment_uses_each_region_at_most_once():
    boxes = [_box("r0", x=0, y=0, w=100, h=50), _box("r1", x=0, y=0, w=100, h=50)]
    regions = [{"text": "ONLY", "bbox": {"x": 0, "y": 0, "width": 100, "height": 50}}]
    assert len(assign_by_overlap(boxes, regions)) == 1


def test_overlap_assignment_ignores_non_overlapping_regions():
    boxes = [_box("r0", x=0, y=0, w=10, h=10)]
    regions = [{"text": "ELSEWHERE", "bbox": {"x": 500, "y": 500, "width": 10, "height": 10}}]
    assert assign_by_overlap(boxes, regions) == {}
