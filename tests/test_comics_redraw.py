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
    DEFAULT_FONT,
    FONTS,
    FONTS_BOLD,
    RedrawError,
    _clamp_bbox,
    _estimate_text_color,
    _fit_text,
    _merge_overlapping_regions,
    _parse_emphasis,
    _resolve_bold_font_path,
    _resolve_font_path,
    _wrap_text,
    redraw_panel,
    redraw_panel_detailed,
)

_FONT_REGULAR = FONTS[DEFAULT_FONT]


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


def _draw_white_text(image: Image.Image, bbox: dict, text: str) -> Image.Image:
    draw = ImageDraw.Draw(image)
    draw.text((bbox["x"] + 5, bbox["y"] + 5), text, fill=(245, 245, 245))
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
        font_path=_FONT_REGULAR,
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
        font_path=_FONT_REGULAR,
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


def test_estimate_text_color_finds_light_text_on_a_dark_bubble():
    """The bug this session fixed: picking the darkest cluster
    unconditionally used to sample the dark BUBBLE itself as "the text"
    on an inverted panel. The real signal is which cluster is the
    minority, not which one is darker."""
    image = _bubble_image(bubble_color=(20, 20, 20))
    bbox = {"x": 60, "y": 50, "width": 180, "height": 60}
    _draw_white_text(image, bbox, "HELLO")

    r, g, b = _estimate_text_color(image, bbox)
    # Should land near white (the minority, actual text), not near the
    # dark bubble background that dominates the region's pixel count.
    assert r > 150 and g > 150 and b > 150


def test_estimate_text_color_falls_back_to_black_for_a_blank_dark_region():
    """A uniformly dark bubble with no text has no minority cluster
    either - same "nothing to sample" case as the light-bubble blank
    region above, just on the other side of the threshold."""
    image = _bubble_image(bubble_color=(20, 20, 20))
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


# ---------------------------------------------------------------------------
# _merge_overlapping_regions - the real bug report: Cloud Vision splits one
# physical bubble's sentence into 2+ "blocks", each got typeset
# independently, producing overlapping garbled text.
# ---------------------------------------------------------------------------


def test_merge_leaves_non_overlapping_regions_untouched():
    regions = [
        {"bbox": {"x": 0, "y": 0, "width": 50, "height": 50}, "adapted_text": "one"},
        {"bbox": {"x": 200, "y": 200, "width": 50, "height": 50}, "adapted_text": "two"},
    ]
    merged = _merge_overlapping_regions(regions)
    assert merged == regions


def test_merge_combines_two_overlapping_regions_into_one():
    regions = [
        {"bbox": {"x": 0, "y": 0, "width": 100, "height": 50}, "adapted_text": "Isn't that right?"},
        {"bbox": {"x": 20, "y": 10, "width": 200, "height": 80}, "adapted_text": "But why would I betray you?"},
    ]
    merged = _merge_overlapping_regions(regions)

    assert len(merged) == 1
    assert merged[0]["adapted_text"] == "Isn't that right? But why would I betray you?"
    # Union bbox - covers both original boxes exactly.
    assert merged[0]["bbox"] == {"x": 0, "y": 0, "width": 220, "height": 90}


def test_merge_is_transitive_across_a_chain_of_three():
    """A overlaps B, B overlaps C, A does not directly overlap C - all
    three must still collapse into one region, not two."""
    regions = [
        {"bbox": {"x": 0, "y": 0, "width": 30, "height": 30}, "adapted_text": "a"},
        {"bbox": {"x": 20, "y": 0, "width": 30, "height": 30}, "adapted_text": "b"},
        {"bbox": {"x": 40, "y": 0, "width": 30, "height": 30}, "adapted_text": "c"},
    ]
    merged = _merge_overlapping_regions(regions)
    assert len(merged) == 1
    assert merged[0]["adapted_text"] == "a b c"


def test_merge_only_combines_the_overlapping_pair_leaving_others_alone():
    regions = [
        {"bbox": {"x": 0, "y": 0, "width": 50, "height": 50}, "adapted_text": "one"},
        {"bbox": {"x": 10, "y": 10, "width": 50, "height": 50}, "adapted_text": "two"},
        {"bbox": {"x": 500, "y": 500, "width": 50, "height": 50}, "adapted_text": "three"},
    ]
    merged = _merge_overlapping_regions(regions)
    assert len(merged) == 2
    texts = {r["adapted_text"] for r in merged}
    assert texts == {"one two", "three"}


def test_redraw_panel_merges_overlapping_regions_before_typesetting():
    """End-to-end: two overlapping regions passed to redraw_panel produce
    one legible combined block instead of two independently-drawn,
    overlapping text blocks - proven by confirming it doesn't raise and
    a same-sized image comes back (the merge happens transparently
    inside redraw_panel, so there's no separate "regions used" output to
    assert against directly here - see the _merge_overlapping_regions
    unit tests above for the actual merge logic coverage)."""
    image = _bubble_image(400, 200)
    bbox_a = {"x": 40, "y": 40, "width": 150, "height": 60}
    bbox_b = {"x": 60, "y": 50, "width": 200, "height": 80}
    _draw_black_text(image, bbox_a, "first")

    result_bytes = redraw_panel(
        _png_bytes(image),
        [
            {"bbox": bbox_a, "adapted_text": "Isn't that right?"},
            {"bbox": bbox_b, "adapted_text": "But why would I betray you?"},
        ],
    )
    result = Image.open(io.BytesIO(result_bytes))
    assert result.size == (400, 200)


def test_redraw_panel_detailed_also_merges_overlapping_regions(monkeypatch):
    """redraw_panel_detailed must apply the same merge redraw_panel does -
    it's a near-duplicate implementation, easy for the two to drift."""
    import engine.comics_redraw as comics_redraw

    captured: list[list[dict]] = []
    real_merge = comics_redraw._merge_overlapping_regions

    def spy_merge(regions):
        result = real_merge(regions)
        captured.append(result)
        return result

    monkeypatch.setattr(comics_redraw, "_merge_overlapping_regions", spy_merge)

    image = _bubble_image(400, 200)
    bbox_a = {"x": 40, "y": 40, "width": 150, "height": 60}
    bbox_b = {"x": 60, "y": 50, "width": 200, "height": 80}

    redraw_panel_detailed(
        _png_bytes(image),
        [
            {"bbox": bbox_a, "adapted_text": "Isn't that right?"},
            {"bbox": bbox_b, "adapted_text": "But why would I betray you?"},
        ],
    )

    assert len(captured) == 1
    assert len(captured[0]) == 1  # the two overlapping regions became one


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


# ---------------------------------------------------------------------------
# Font selection - a small curated set of bundled OFL comic fonts (Comic
# Neue by default) replacing the single fixed Liberation Sans, with
# per-region/default overrides.
# ---------------------------------------------------------------------------


def test_resolve_font_path_returns_the_named_font():
    assert _resolve_font_path("patrick-hand") == FONTS["patrick-hand"]


def test_resolve_font_path_falls_back_to_default_for_none():
    assert _resolve_font_path(None) == FONTS[DEFAULT_FONT]


def test_resolve_font_path_falls_back_to_default_for_an_unknown_name():
    """A typo or a stale saved value degrades to the default rather than
    raising - a wrong font is cosmetic, not worth failing the redraw."""
    assert _resolve_font_path("not-a-real-font") == FONTS[DEFAULT_FONT]


def test_resolve_font_path_falls_back_to_default_for_an_empty_string():
    assert _resolve_font_path("") == FONTS[DEFAULT_FONT]


def test_every_registered_font_actually_loads():
    for name, path in FONTS.items():
        font = ImageFont.truetype(str(path), 24)
        assert font.getbbox("Ag") is not None, f"{name} failed to load a usable font"


def test_redraw_panel_uses_the_requested_default_font(monkeypatch):
    import engine.comics_redraw as comics_redraw

    used_font_paths = []
    real_draw = comics_redraw._draw_text_in_region

    def spy_draw(image, bbox, text, color, font_path=FONTS[DEFAULT_FONT], bold_font_path=None):
        used_font_paths.append(font_path)
        return real_draw(image, bbox, text, color, font_path, bold_font_path)

    monkeypatch.setattr(comics_redraw, "_draw_text_in_region", spy_draw)

    image = _bubble_image()
    redraw_panel(
        _png_bytes(image),
        [{"bbox": {"x": 40, "y": 30, "width": 100, "height": 40}, "adapted_text": "hi"}],
        default_font="patrick-hand",
    )

    assert used_font_paths == [FONTS["patrick-hand"]]


def test_redraw_panel_a_per_region_font_overrides_the_default(monkeypatch):
    import engine.comics_redraw as comics_redraw

    used_font_paths = []
    real_draw = comics_redraw._draw_text_in_region

    def spy_draw(image, bbox, text, color, font_path=FONTS[DEFAULT_FONT], bold_font_path=None):
        used_font_paths.append(font_path)
        return real_draw(image, bbox, text, color, font_path, bold_font_path)

    monkeypatch.setattr(comics_redraw, "_draw_text_in_region", spy_draw)

    image = _bubble_image(400, 200)
    redraw_panel(
        _png_bytes(image),
        [
            {
                "bbox": {"x": 20, "y": 20, "width": 100, "height": 40},
                "adapted_text": "one",
                "font": "liberation-sans",
            },
            {"bbox": {"x": 220, "y": 120, "width": 100, "height": 40}, "adapted_text": "two"},
        ],
        default_font="patrick-hand",
    )

    assert used_font_paths == [FONTS["liberation-sans"], FONTS["patrick-hand"]]


def test_redraw_panel_defaults_to_comic_neue_with_no_font_specified(monkeypatch):
    import engine.comics_redraw as comics_redraw

    used_font_paths = []
    real_draw = comics_redraw._draw_text_in_region

    def spy_draw(image, bbox, text, color, font_path=FONTS[DEFAULT_FONT], bold_font_path=None):
        used_font_paths.append(font_path)
        return real_draw(image, bbox, text, color, font_path, bold_font_path)

    monkeypatch.setattr(comics_redraw, "_draw_text_in_region", spy_draw)

    image = _bubble_image()
    redraw_panel(
        _png_bytes(image),
        [{"bbox": {"x": 40, "y": 30, "width": 100, "height": 40}, "adapted_text": "hi"}],
    )

    assert used_font_paths == [FONTS["comic-neue"]]


def test_merge_preserves_the_first_regions_font():
    regions = [
        {
            "bbox": {"x": 0, "y": 0, "width": 100, "height": 50},
            "adapted_text": "one",
            "font": "patrick-hand",
        },
        {
            "bbox": {"x": 20, "y": 10, "width": 200, "height": 80},
            "adapted_text": "two",
            "font": "liberation-sans",
        },
    ]
    merged = _merge_overlapping_regions(regions)
    assert len(merged) == 1
    assert merged[0]["font"] == "patrick-hand"


# ---------------------------------------------------------------------------
# Dynamic typography: **emphasis** markers (engine/prompts.py's
# _EMPHASIS_INSTRUCTION, comics-only) rendered as bold words - a
# letterer's actual tool for conveying vocal stress.
# ---------------------------------------------------------------------------


def test_parse_emphasis_returns_every_word_unemphasized_when_there_are_no_markers():
    assert _parse_emphasis("why would I betray you") == [
        ("why", False),
        ("would", False),
        ("I", False),
        ("betray", False),
        ("you", False),
    ]


def test_parse_emphasis_marks_a_single_emphasized_word():
    tokens = _parse_emphasis("why would I **betray** you")
    assert tokens == [
        ("why", False),
        ("would", False),
        ("I", False),
        ("betray", True),
        ("you", False),
    ]


def test_parse_emphasis_marks_every_word_in_a_multi_word_phrase():
    tokens = _parse_emphasis("**never going back** now")
    assert tokens == [
        ("never", True),
        ("going", True),
        ("back", True),
        ("now", False),
    ]


def test_parse_emphasis_handles_two_separate_emphasized_spans():
    tokens = _parse_emphasis("**why** would I **betray** you")
    assert tokens == [
        ("why", True),
        ("would", False),
        ("I", False),
        ("betray", True),
        ("you", False),
    ]


def test_parse_emphasis_reconstructs_the_same_plain_words_as_the_original():
    """The lockstep-consumption trick in _draw_text_in_region depends on
    this holding for any input, not just the hand-picked examples above."""
    text = "**why** would I **betray** you now"
    tokens = _parse_emphasis(text)
    assert " ".join(word for word, _ in tokens) == "why would I betray you now"


def test_draw_text_in_region_renders_emphasized_words_in_the_bold_font(monkeypatch):
    calls: list[tuple[str, object]] = []
    original_text = ImageDraw.ImageDraw.text

    def spy_text(self, xy, text, font=None, fill=None, **kwargs):
        calls.append((text, font))
        return original_text(self, xy, text, font=font, fill=fill, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy_text)

    from engine.comics_redraw import FONTS_BOLD, _draw_text_in_region

    image = _bubble_image(400, 150)
    _draw_text_in_region(
        image,
        {"x": 20, "y": 20, "width": 300, "height": 80},
        "why would I **betray** you",
        (0, 0, 0),
        FONTS["comic-neue"],
        FONTS_BOLD["comic-neue"],
    )

    drawn = {text: font.path for text, font in calls}
    assert drawn["betray"] == str(FONTS_BOLD["comic-neue"])
    for word in ("why", "would", "I", "you"):
        assert drawn[word] == str(FONTS["comic-neue"])


def test_draw_text_in_region_falls_back_to_regular_weight_when_no_bold_font_given(monkeypatch):
    """patrick-hand has no bundled bold file - _resolve_bold_font_path
    already falls back to the regular font, and _draw_text_in_region
    itself must not crash or silently drop the emphasized word when
    bold_font_path is None (the default)."""
    calls: list[tuple[str, object]] = []
    original_text = ImageDraw.ImageDraw.text

    def spy_text(self, xy, text, font=None, fill=None, **kwargs):
        calls.append((text, font))
        return original_text(self, xy, text, font=font, fill=fill, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy_text)

    from engine.comics_redraw import _draw_text_in_region

    image = _bubble_image(400, 150)
    _draw_text_in_region(
        image,
        {"x": 20, "y": 20, "width": 300, "height": 80},
        "why would I **betray** you",
        (0, 0, 0),
        FONTS["patrick-hand"],
    )

    drawn = {text: font.path for text, font in calls}
    assert drawn["betray"] == str(FONTS["patrick-hand"])


def test_resolve_bold_font_path_uses_the_real_bold_file_when_available():
    assert _resolve_bold_font_path("comic-neue") == FONTS_BOLD["comic-neue"]
    assert _resolve_bold_font_path("liberation-sans") == FONTS_BOLD["liberation-sans"]


def test_resolve_bold_font_path_falls_back_to_regular_for_a_font_with_no_bold_file():
    assert _resolve_bold_font_path("patrick-hand") == FONTS["patrick-hand"]


def test_resolve_bold_font_path_falls_back_to_default_for_an_unknown_font():
    assert _resolve_bold_font_path("not-a-real-font") == FONTS_BOLD[DEFAULT_FONT]
