"""Tests for engine/comics_ocr.py. Region-grouping is tested against
synthetic Tesseract-shaped data (no binary needed); extract_text_regions
itself is skipped unless tesseract-ocr is actually installed, since it
shells out to the real binary - see the module docstring for why a real
OCR run, not a mock, is what this project treats as trustworthy here.
"""
from __future__ import annotations

import io
import shutil

import pytest
from PIL import Image, ImageDraw

from engine.comics_ocr import OcrError, _group_words_into_regions, extract_text_regions

TESSERACT_INSTALLED = shutil.which("tesseract") is not None


def _fake_ocr_data(rows: list[tuple[int, int, str, int, int, int, int, int]]) -> dict:
    """Builds a dict shaped like pytesseract.image_to_data's DICT output
    from (block_num, par_num, text, left, top, width, height, conf) rows.
    """
    data: dict[str, list] = {
        "block_num": [],
        "par_num": [],
        "text": [],
        "left": [],
        "top": [],
        "width": [],
        "height": [],
        "conf": [],
    }
    for block_num, par_num, text, left, top, width, height, conf in rows:
        data["block_num"].append(block_num)
        data["par_num"].append(par_num)
        data["text"].append(text)
        data["left"].append(left)
        data["top"].append(top)
        data["width"].append(width)
        data["height"].append(height)
        data["conf"].append(conf)
    return data


def test_groups_words_in_the_same_block_and_paragraph_into_one_region():
    data = _fake_ocr_data(
        [
            (1, 1, "Hello", 10, 10, 40, 15, 92),
            (1, 1, "there", 55, 10, 35, 15, 88),
            (2, 1, "Goodbye", 10, 100, 60, 15, 90),
        ]
    )
    regions = _group_words_into_regions(data)
    assert len(regions) == 2
    assert regions[0].text == "Hello there"
    assert regions[0].x == 10
    assert regions[0].y == 10
    # width spans from the first word's left edge to the second word's right edge
    assert regions[0].width == 80
    assert regions[1].text == "Goodbye"


def test_ignores_blank_and_whitespace_only_words():
    data = _fake_ocr_data(
        [
            (1, 1, "  ", 0, 0, 5, 5, -1),
            (1, 1, "Real", 10, 10, 30, 15, 95),
        ]
    )
    regions = _group_words_into_regions(data)
    assert len(regions) == 1
    assert regions[0].text == "Real"


def test_confidence_averages_only_non_negative_word_confidences():
    data = _fake_ocr_data(
        [
            (1, 1, "A", 0, 0, 10, 10, 80),
            (1, 1, "B", 10, 0, 10, 10, 60),
            (1, 1, "C", 20, 0, 10, 10, -1),  # -1 marks "no confidence", excluded
        ]
    )
    regions = _group_words_into_regions(data)
    assert regions[0].confidence == 70.0


def test_unsupported_language_raises_before_any_ocr_runs():
    with pytest.raises(OcrError, match="not configured for 'French'"):
        extract_text_regions(b"not even a real image", language="French")


def test_undecodable_image_raises_ocr_error():
    with pytest.raises(OcrError, match="Could not decode"):
        extract_text_regions(b"this is not an image", language="English")


@pytest.mark.skipif(not TESSERACT_INSTALLED, reason="tesseract-ocr binary not installed")
def test_extract_text_regions_finds_real_printed_text():
    image = Image.new("RGB", (400, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 40), "HELLO WORLD", fill="black")
    buf = io.BytesIO()
    image.save(buf, format="PNG")

    result = extract_text_regions(buf.getvalue(), language="English")
    assert "HELLO" in result["full_text"].upper()
    assert result["image_width"] == 400
    assert result["image_height"] == 120
    assert all("bbox" in r for r in result["regions"])
