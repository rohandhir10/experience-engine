"""Comic panel redraw: erases the original text out of a speech bubble
and draws the adapted line back in its place — the image-editing half of
Scope B from the "premium landing page" design conversation, kept
deliberately separate from engine/comics_ocr.py (extraction) and
engine/comics_adapt.py (adaptation), which only ever touch text, never
pixels.

Honest scope, stated plainly up front, same discipline as every other
module in this project:

- SPEECH BUBBLES ONLY. A bubble interior is usually a plain or
  near-solid color, which is the one case this pipeline's inpainting
  step can plausibly reconstruct. Sound-effect (SFX) text integrated
  into busy, textured artwork is NOT attempted here — inpainting a
  jagged action-line background is a much harder problem, and silently
  attempting it would produce a visibly broken smudge, not a redrawn
  SFX. Nothing here rejects an SFX-shaped region; the caller is
  responsible for only sending genuine bubble regions (this module has
  no way to tell the difference from a bounding box alone).
- ONE fixed bundled font (Liberation Sans, SIL-OFL-licensed, shipped in
  engine/assets/fonts/) for every redrawn line, always. This does NOT
  match the original comic's lettering style, weight, or size — "exact
  font weight match" was flagged as aspirational marketing copy, not a
  real capability, when this was scoped, and it still isn't one here.
- The inpainting step (OpenCV's classical Telea algorithm — see
  _inpaint_regions) reconstructs a background by extrapolating from
  surrounding pixels. It has no understanding of what a speech bubble
  "should" look like; on a shaded, gradient, or textured bubble this can
  still look wrong, just less wrong than leaving the original text in
  place.
- Text color is a heuristic (see _estimate_text_color): it assumes dark
  text on a lighter bubble, the overwhelmingly common case, and will
  guess backwards on the rarer light-text-on-dark-bubble panel.
- No persistence, no caching, no share link — this is a synchronous
  request/response transform (server/main.py's /api/comics/redraw),
  unlike engine/comics_adapt.py's results, which are cached and
  recorded in history. Redrawing the same panel twice re-runs the whole
  pipeline both times.
"""
from __future__ import annotations

import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
_FONT_REGULAR = _FONT_DIR / "LiberationSans-Regular.ttf"

# How far past a text region's own bounding box to inpaint, in pixels -
# OCR boxes tend to hug the glyphs tightly, and a zero-padding erase
# leaves a visible ring of the original text's anti-aliased edge pixels
# behind. Not so large that it eats into a neighboring bubble's border.
_INPAINT_PADDING_PX = 4

# OpenCV's inpaint "radius" - how far the algorithm looks from the
# masked edge when extrapolating a fill. Small and fast; comic bubble
# interiors are usually near-uniform, so a large radius buys nothing.
_INPAINT_RADIUS = 3

# A region taller/wider than this (in font-size search) is where the
# search bottoms out rather than looping forever on a region too small
# for even the smallest legible text.
_MIN_FONT_SIZE = 8
_MAX_FONT_SIZE = 72

# Text darker than this normalized luminance (0=black, 1=white) is what
# _estimate_text_color treats as "probably the text, not the bubble
# background" - see that function's docstring for the dark-on-light
# assumption this encodes.
_DARK_LUMINANCE_THRESHOLD = 0.5


class RedrawError(Exception):
    """Raised for a malformed image or region — same "fail loudly, don't
    fabricate a result" convention as engine/comics_ocr.py::OcrError."""


def _load_image(image_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception as exc:
        raise RedrawError(f"Could not read this image: {exc}") from exc
    return image.convert("RGB")


def _clamp_bbox(bbox: dict, image_size: tuple[int, int], padding: int = 0) -> tuple[int, int, int, int]:
    """Returns (left, top, right, bottom), padded and clamped to the
    image's own bounds - a region near an edge must not ask PIL/OpenCV
    to read or write outside the actual pixel buffer."""
    width, height = image_size
    left = max(0, int(bbox["x"]) - padding)
    top = max(0, int(bbox["y"]) - padding)
    right = min(width, int(bbox["x"]) + int(bbox["width"]) + padding)
    bottom = min(height, int(bbox["y"]) + int(bbox["height"]) + padding)
    if right <= left or bottom <= top:
        raise RedrawError(f"Region has no area after clamping to the image: {bbox!r}")
    return left, top, right, bottom


def _estimate_text_color(image: Image.Image, bbox: dict) -> tuple[int, int, int]:
    """Guesses the original text's color by sampling the darkest cluster
    of pixels inside the (un-inpainted) region - assumes dark text on a
    lighter bubble, the common case for comic lettering. Must be called
    BEFORE _inpaint_regions erases the very pixels this reads. Falls
    back to plain black if the region turns out to have no meaningfully
    dark pixels at all (a blank/empty region), rather than raising -
    color is a cosmetic guess, not something worth failing the whole
    redraw over.
    """
    left, top, right, bottom = _clamp_bbox(bbox, image.size)
    crop = np.asarray(image.crop((left, top, right, bottom)), dtype=np.float64)
    if crop.size == 0:
        return (0, 0, 0)

    luminance = (0.299 * crop[..., 0] + 0.587 * crop[..., 1] + 0.114 * crop[..., 2]) / 255.0
    dark_mask = luminance < _DARK_LUMINANCE_THRESHOLD
    if not dark_mask.any():
        return (0, 0, 0)

    dark_pixels = crop[dark_mask]
    r, g, b = dark_pixels.mean(axis=0)
    return (int(r), int(g), int(b))


def _inpaint_regions(image: Image.Image, bboxes: list[dict]) -> Image.Image:
    """Erases every region at once (one OpenCV call, one combined mask)
    rather than per-region, so overlapping padding between two nearby
    regions is handled correctly instead of one region's fill
    overwriting another's."""
    width, height = image.size
    mask = np.zeros((height, width), dtype=np.uint8)
    for bbox in bboxes:
        left, top, right, bottom = _clamp_bbox(bbox, image.size, padding=_INPAINT_PADDING_PX)
        mask[top:bottom, left:right] = 255

    # PIL is RGB; OpenCV's inpaint expects BGR - a plain channel-order
    # swap, not a color-space conversion, so this is loss-free.
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    inpainted_bgr = cv2.inpaint(bgr, mask, _INPAINT_RADIUS, cv2.INPAINT_TELEA)
    inpainted_rgb = cv2.cvtColor(inpainted_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(inpainted_rgb)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_text(
    text: str, box_width: int, box_height: int, draw: ImageDraw.ImageDraw
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Finds the largest font size (within _MIN/_MAX_FONT_SIZE) whose
    word-wrapped lines fit inside the box, searching downward from the
    max. If even the minimum size doesn't fit vertically, returns the
    minimum size anyway with whatever lines it produces - overflowing
    slightly is more honest than raising on a bubble too small for its
    own adapted line, which a longer English rendering of a short
    source line can genuinely produce.
    """
    for size in range(_MAX_FONT_SIZE, _MIN_FONT_SIZE - 1, -2):
        font = ImageFont.truetype(str(_FONT_REGULAR), size)
        lines = _wrap_text(text, font, box_width, draw)
        line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        total_height = line_height * len(lines) * 1.2  # 1.2x for line spacing
        widest_line = max(draw.textlength(line, font=font) for line in lines)
        if total_height <= box_height and widest_line <= box_width:
            return font, lines

    font = ImageFont.truetype(str(_FONT_REGULAR), _MIN_FONT_SIZE)
    return font, _wrap_text(text, font, box_width, draw)


def _draw_text_in_region(
    image: Image.Image, bbox: dict, text: str, color: tuple[int, int, int]
) -> None:
    """Mutates `image` in place - draws centered, word-wrapped text into
    the (already-inpainted) region."""
    left, top, right, bottom = _clamp_bbox(bbox, image.size)
    box_width, box_height = right - left, bottom - top
    draw = ImageDraw.Draw(image)

    font, lines = _fit_text(text, box_width, box_height, draw)
    line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
    total_height = line_height * len(lines) * 1.2
    y = top + max(0, (box_height - total_height) / 2)

    for line in lines:
        line_width = draw.textlength(line, font=font)
        x = left + max(0, (box_width - line_width) / 2)
        draw.text((x, y), line, font=font, fill=color)
        y += line_height * 1.2


def redraw_panel(image_bytes: bytes, regions: list[dict]) -> bytes:
    """The full pipeline: estimate each region's text color from the
    original pixels, inpaint every region's text away, draw each
    region's adapted text back in its own estimated color. Returns a
    new PNG's raw bytes.

    `regions` is `[{"bbox": {"x", "y", "width", "height"}, "adapted_text": str}, ...]`
    - the same bbox shape engine/comics_ocr.py already produces per
    detected region, paired with whatever adapted line the caller wants
    drawn there (this module has no opinion on where that text came
    from - it could be engine/comics_adapt.py's output, or anything
    else the caller supplies).

    Raises RedrawError for an unreadable image, an empty regions list,
    or a region with no area after clamping to the image bounds.
    """
    if not regions:
        raise RedrawError("At least one region is required to redraw a panel.")

    image = _load_image(image_bytes)
    bboxes = [r["bbox"] for r in regions]

    text_colors = [_estimate_text_color(image, bbox) for bbox in bboxes]

    inpainted = _inpaint_regions(image, bboxes)

    for region, color in zip(regions, text_colors):
        _draw_text_in_region(inpainted, region["bbox"], region["adapted_text"], color)

    buffer = io.BytesIO()
    inpainted.save(buffer, format="PNG")
    return buffer.getvalue()
