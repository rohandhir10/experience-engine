"""Tests for engine/comics_ocr.py (Google Cloud Vision-backed OCR).

No real network call is made — httpx.post is monkeypatched with a fake
response shaped like Cloud Vision's actual DOCUMENT_TEXT_DETECTION JSON,
built from a real sample of that response shape. _block_text/
_bounding_box are also tested directly against synthetic Vision-shaped
block dicts.
"""
from __future__ import annotations

import pytest

from engine import comics_ocr
from engine.comics_ocr import OcrError, _bounding_box, _block_text, extract_text_regions


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict, text: str = ""):
        self.status_code = status_code
        self._json_body = json_body
        self.text = text or str(json_body)

    def json(self) -> dict:
        return self._json_body


def _vision_success_response(blocks: list[dict], width: int = 500, height: int = 600) -> dict:
    return {
        "responses": [
            {
                "fullTextAnnotation": {
                    "pages": [{"width": width, "height": height, "blocks": blocks}],
                }
            }
        ]
    }


def _block(text_words: list[str], vertices: list[dict], confidence: float) -> dict:
    return {
        "boundingBox": {"vertices": vertices},
        "confidence": confidence,
        "paragraphs": [
            {
                "words": [
                    {"symbols": [{"text": ch} for ch in word]} for word in text_words
                ]
            }
        ],
    }


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_VISION_API_KEY", "test-key")


def test_block_text_joins_words_with_spaces_and_paragraphs_with_newlines():
    block = {
        "paragraphs": [
            {"words": [{"symbols": [{"text": "H"}, {"text": "i"}]}]},
            {"words": [{"symbols": [{"text": "b"}, {"text": "ye"}]}]},
        ]
    }
    assert _block_text(block) == "Hi\nbye"


def test_block_text_skips_empty_paragraphs():
    block = {"paragraphs": [{"words": []}, {"words": [{"symbols": [{"text": "ok"}]}]}]}
    assert _block_text(block) == "ok"


def test_bounding_box_collapses_quadrilateral_to_axis_aligned_rect():
    vertices = [{"x": 10, "y": 10}, {"x": 90, "y": 12}, {"x": 88, "y": 40}, {"x": 12, "y": 38}]
    box = _bounding_box(vertices)
    assert box == {"x": 10, "y": 10, "width": 80, "height": 30}


def test_bounding_box_handles_missing_vertices():
    assert _bounding_box([]) == {"x": 0, "y": 0, "width": 0, "height": 0}


def test_missing_api_key_raises_before_any_request(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_VISION_API_KEY", raising=False)
    with pytest.raises(OcrError, match="GOOGLE_CLOUD_VISION_API_KEY"):
        extract_text_regions(b"fake-image-bytes")


def test_extracts_real_looking_blocks_with_scaled_confidence(monkeypatch):
    blocks = [
        _block(
            ["HELLO", "THERE"],
            [{"x": 10, "y": 10}, {"x": 110, "y": 10}, {"x": 110, "y": 30}, {"x": 10, "y": 30}],
            0.95,
        ),
        _block(
            ["GOODBYE"],
            [{"x": 10, "y": 100}, {"x": 130, "y": 100}, {"x": 130, "y": 120}, {"x": 10, "y": 120}],
            0.9,
        ),
    ]
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(200, _vision_success_response(blocks)),
    )
    result = extract_text_regions(b"fake-image-bytes")
    assert result["image_width"] == 500
    assert result["image_height"] == 600
    assert len(result["regions"]) == 2
    assert result["regions"][0]["text"] == "HELLO THERE"
    assert result["regions"][0]["confidence"] == 95.0
    assert result["regions"][0]["bbox"] == {"x": 10, "y": 10, "width": 100, "height": 20}
    assert "HELLO THERE" in result["full_text"]
    assert result["warning"] is None


def test_majority_low_confidence_blocks_produce_a_warning(monkeypatch):
    blocks = [
        _block(["a"], [{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}], 0.3),
        _block(["b"], [{"x": 0, "y": 20}, {"x": 10, "y": 20}, {"x": 10, "y": 30}, {"x": 0, "y": 30}], 0.4),
    ]
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(200, _vision_success_response(blocks)),
    )
    result = extract_text_regions(b"fake-image-bytes")
    assert result["warning"] is not None
    assert "low" in result["warning"].lower()


def test_no_text_detected_returns_empty_regions_and_a_warning(monkeypatch):
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(200, {"responses": [{}]}),
    )
    result = extract_text_regions(b"fake-image-bytes")
    assert result["regions"] == []
    assert result["warning"] == "No text detected in this panel. Type it in by hand."


def test_http_error_status_raises_ocr_error(monkeypatch):
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(403, {}, text="Forbidden"),
    )
    with pytest.raises(OcrError, match="403"):
        extract_text_regions(b"fake-image-bytes")


def test_vision_error_in_response_raises_ocr_error(monkeypatch):
    monkeypatch.setattr(
        comics_ocr.httpx,
        "post",
        lambda *a, **k: _FakeResponse(
            200, {"responses": [{"error": {"message": "Bad image data."}}]}
        ),
    )
    with pytest.raises(OcrError, match="Bad image data"):
        extract_text_regions(b"fake-image-bytes")


def test_known_language_is_sent_as_a_hint(monkeypatch):
    captured = {}

    def fake_post(url, params=None, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResponse(200, {"responses": [{}]})

    monkeypatch.setattr(comics_ocr.httpx, "post", fake_post)
    extract_text_regions(b"fake-image-bytes", language="Korean")
    assert captured["payload"]["requests"][0]["imageContext"]["languageHints"] == ["ko"]


def test_unknown_or_missing_language_sends_no_hint(monkeypatch):
    captured = {}

    def fake_post(url, params=None, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResponse(200, {"responses": [{}]})

    monkeypatch.setattr(comics_ocr.httpx, "post", fake_post)
    extract_text_regions(b"fake-image-bytes", language="French")
    assert "imageContext" not in captured["payload"]["requests"][0]

    extract_text_regions(b"fake-image-bytes")
    assert "imageContext" not in captured["payload"]["requests"][0]
