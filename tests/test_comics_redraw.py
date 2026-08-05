"""Tests for engine/comics_redraw.py. Real PIL/OpenCV calls (no network,
no LLM) against small synthetic images built in-test - no real webtoon
panel images exist in this repo to test against, which is itself a
disclosed limitation of this feature's coverage (see the module's own
docstring and docs/CAPABILITY_MATRIX.md).
"""
from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from engine.comics_redraw import (
    _FONT_REGULAR,
    RedrawError,
    _clamp_bbox,
    _estimate_text_color,
    _fit_text,
    _wrap_text,
    redraw_panel,
)


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _bubble_image(width=300, height=150, bubble_color=(255, 255, 255)) -> Image.Image:
    """A plain colored background with a solid-color 'bubble' rectangle
    drawn in the middle - a deliberately simple stand-in for a real
    speech bubble, since no real comic panel images are available here."""
    image = Image.new("RGB", (width, height), (40, 60, 90))
    draw = ImageDraw.Draw(image)
    draw.rectangle([40, 30, width - 40, height - 30], fill=bubble_color, outline=(0, 0, 0))
    return image


def _draw_black_text(image: Image.Image, bbox: dict, text: str) -> Image.Image:
    draw = ImageDraw.Draw(image)
    draw.text((bbox["x"] + 5, bbox["y"] + 5), text, fill=(10, 10, 10))
    return image


# ---------------------------------------------------------------------------
# _clamp_bbox
# ---------------------------------------------------------------------------


def test_clamp_bbox_clamps_to_image_bounds():
    left, top, right, bottom = _clamp_bbox(
        {"x": -5, "y": -5, "width": 20, "height": 20}, image_size=(10, 10)
    )
    assert (left, top, right, bottom) == (0, 0, 10, 10)


def test_clamp_bbox_applies_padding():
    left, top, right, bottom = _clamp_bbox(
        {"x": 10, "y": 10, "width": 20, "height": 20}, image_size=(100, 100), padding=3
    )
    assert (left, top, right, bottom) == (7, 7, 33, 33)


def test_clamp_bbox_rejects_a_region_with_no_area():
    with pytest.raises(RedrawError):
        _clamp_bbox({"x": 200, "y": 200, "width": 10, "height": 10}, image_size=(100, 100))


# ---------------------------------------------------------------------------
# _wrap_text / _fit_text
# ---------------------------------------------------------------------------


def test_wrap_text_keeps_short_text_on_one_line():
    image = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(_FONT_REGULAR), 20)
    lines = _wrap_text("hi there", font, max_width=1000, draw=draw)
    assert lines == ["hi there"]


def test_wrap_text_breaks_long_text_across_lines():
    image = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(_FONT_REGULAR), 20)
    lines = _wrap_text(
        "this is a much longer sentence than fits on one narrow line",
        font,
        max_width=120,
        draw=draw,
    )
    assert len(lines) > 1
    # No word was dropped in the process of wrapping.
    assert " ".join(lines) == "this is a much longer sentence than fits on one narrow line"


def test_fit_text_shrinks_font_to_fit_a_small_box():
    image = Image.new("RGB", (400, 400))
    draw = ImageDraw.Draw(image)
    font, lines = _fit_text(
        "A fairly long adapted line that will not fit at a large size",
        box_width=100,
        box_height=60,
        draw=draw,
    )
    assert font.size < 72  # did not stay at the max size
    assert len(lines) >= 1


def test_fit_text_never_raises_even_when_nothing_fits():
    """A box too small for even the minimum font size should still
    return something rather than raising - overflowing is more honest
    than crashing the whole redraw over one stubborn region."""
    image = Image.new("RGB", (400, 400))
    draw = ImageDraw.Draw(image)
    font, lines = _fit_text(
        "an extremely long line of adapted dialogue that cannot possibly fit",
        box_width=15,
        box_height=10,
        draw=draw,
    )
    assert font.size == 8  # bottomed out at the minimum
    assert lines


# ---------------------------------------------------------------------------
# _estimate_text_color
# ---------------------------------------------------------------------------


def test_estimate_text_color_finds_dark_text_on_a_light_bubble():
    image = _bubble_image(bubble_color=(255, 255, 255))
    bbox = {"x": 60, "y": 50, "width": 180, "height": 60}
    _draw_black_text(image, bbox, "HELLO")

    r, g, b = _estimate_text_color(image, bbox)
    # Should land near black, not near the white bubble background.
    assert r < 100 and g < 100 and b < 100


def test_estimate_text_color_falls_back_to_black_for_a_blank_region():
    image = _bubble_image(bubble_color=(255, 255, 255))
    bbox = {"x": 60, "y": 50, "width": 180, "height": 60}  # no text drawn
    assert _estimate_text_color(image, bbox) == (0, 0, 0)


# ---------------------------------------------------------------------------
# redraw_panel (full pipeline, synthetic images)
# ---------------------------------------------------------------------------


def test_redraw_panel_returns_a_same_sized_png():
    image = _bubble_image(300, 150)
    bbox = {"x": 60, "y": 50, "width": 180, "height": 60}
    _draw_black_text(image, bbox, "hola mundo")

    result_bytes = redraw_panel(
        _png_bytes(image),
        [{"bbox": bbox, "adapted_text": "hello world"}],
    )
    result = Image.open(io.BytesIO(result_bytes))
    assert result.size == (300, 150)
    assert result.format == "PNG"


def test_redraw_panel_actually_changes_the_region_pixels():
    """Proves something was drawn, not a silent no-op - the redrawn
    region's pixel content must differ from the original."""
    image = _bubble_image(300, 150)
    bbox = {"x": 60, "y": 50, "width": 180, "height": 60}
    _draw_black_text(image, bbox, "hola")

    original_crop = np.asarray(image.crop((bbox["x"], bbox["y"], bbox["x"] + bbox["width"], bbox["y"] + bbox["height"])))

    result_bytes = redraw_panel(_png_bytes(image), [{"bbox": bbox, "adapted_text": "a completely different line"}])
    result = Image.open(io.BytesIO(result_bytes)).convert("RGB")
    result_crop = np.asarray(result.crop((bbox["x"], bbox["y"], bbox["x"] + bbox["width"], bbox["y"] + bbox["height"])))

    assert not np.array_equal(original_crop, result_crop)


def test_redraw_panel_leaves_pixels_outside_every_region_untouched():
    image = _bubble_image(300, 150)
    bbox = {"x": 60, "y": 50, "width": 180, "height": 60}
    _draw_black_text(image, bbox, "hola")

    corner_before = np.asarray(image.crop((0, 0, 20, 20)))

    result_bytes = redraw_panel(_png_bytes(image), [{"bbox": bbox, "adapted_text": "hello"}])
    result = Image.open(io.BytesIO(result_bytes)).convert("RGB")
    corner_after = np.asarray(result.crop((0, 0, 20, 20)))

    assert np.array_equal(corner_before, corner_after)


def test_redraw_panel_handles_multiple_regions_independently():
    image = _bubble_image(400, 200)
    bbox_a = {"x": 20, "y": 20, "width": 150, "height": 50}
    bbox_b = {"x": 220, "y": 120, "width": 150, "height": 50}
    _draw_black_text(image, bbox_a, "first")
    _draw_black_text(image, bbox_b, "second")

    result_bytes = redraw_panel(
        _png_bytes(image),
        [
            {"bbox": bbox_a, "adapted_text": "one"},
            {"bbox": bbox_b, "adapted_text": "two"},
        ],
    )
    result = Image.open(io.BytesIO(result_bytes))
    assert result.size == (400, 200)


def test_redraw_panel_rejects_an_empty_region_list():
    image = _bubble_image()
    with pytest.raises(RedrawError):
        redraw_panel(_png_bytes(image), [])


def test_redraw_panel_rejects_unreadable_image_bytes():
    with pytest.raises(RedrawError):
        redraw_panel(b"not a real image", [{"bbox": {"x": 0, "y": 0, "width": 10, "height": 10}, "adapted_text": "x"}])


def test_redraw_panel_rejects_a_region_entirely_outside_the_image():
    image = _bubble_image(100, 100)
    with pytest.raises(RedrawError):
        redraw_panel(
            _png_bytes(image),
            [{"bbox": {"x": 500, "y": 500, "width": 20, "height": 20}, "adapted_text": "x"}],
        )


def test_redraw_panel_composites_a_transparent_panel_onto_white_not_raw_black():
    """The color-fade bug report: a panel with a real alpha channel (a
    ZIP-slice PNG, a PDF page rendered to an RGBA canvas) previously had
    its alpha silently dropped by a bare convert("RGB") - not composited
    onto anything - which exposed whatever raw color sat underneath a
    transparent pixel as a visible discoloration. Every pixel here is
    fully transparent with an underlying raw color of pure black; a
    correct fix must show white (or close to it) outside the drawn
    regions, not black.
    """
    width, height = 100, 60
    rgba = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    buffer = io.BytesIO()
    rgba.save(buffer, format="PNG")

    bbox = {"x": 20, "y": 20, "width": 40, "height": 20}
    out_bytes = redraw_panel(buffer.getvalue(), [{"bbox": bbox, "adapted_text": "hi"}])
    out = Image.open(io.BytesIO(out_bytes)).convert("RGB")

    # Sample well outside the redrawn region, where nothing but the
    # alpha-flattening step could have touched the pixel.
    corner = np.asarray(out)[5, 5]
    assert corner.tolist() == [255, 255, 255], (
        f"expected the transparent panel to composite onto white, got {corner.tolist()} "
        "(a bare convert(\"RGB\") would have leaked the raw black through instead)"
    )
