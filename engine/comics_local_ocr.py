"""Local, zero-per-request-cost OCR for comic pages using Tesseract.

This is a conservative first pass, not a manga-specialist recogniser. It
returns word-line regions and confidence from Tesseract; stylised lettering,
vertical Japanese text, and sound effects can be missed. Keep review in the
loop and use the paid provider only when explicitly enabled as a fallback.

The binary and language packs are installed in the API image. No network call
or model download happens at request time.
"""
from __future__ import annotations

import io
import logging
import os
import shutil
from collections import defaultdict

from PIL import Image, ImageOps

from .comics_ocr import sort_reading_order

logger = logging.getLogger(__name__)

_LANGUAGE_MAP = {
    "English": "eng",
    "Hindi": "hin",
    "Japanese": "jpn",
    "Korean": "kor",
    "Spanish": "spa",
    "Urdu": "urd",
}


class LocalOcrError(RuntimeError):
    """Local OCR is unavailable or could not decode/process the image."""


def extract_text_regions(image_bytes: bytes, language: str | None = None) -> dict:
    """Extract text lines and approximate boxes without calling a paid API."""
    import pytesseract
    from pytesseract import Output

    if not shutil.which("tesseract"):
        raise LocalOcrError("Local OCR is unavailable: Tesseract is not installed.")

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            width, height = image.size
            if width <= 0 or height <= 0:
                raise ValueError("empty image")
    except Exception as exc:
        raise LocalOcrError("Could not decode the uploaded image for local OCR.") from exc

    lang = _LANGUAGE_MAP.get(language or "English", "eng")
    try:
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config="--psm 11",
            output_type=Output.DICT,
        )
    except Exception as exc:
        # Missing language packs are a setup error, not a reason to silently
        # incur a paid-provider call.
        raise LocalOcrError(
            f"Local OCR failed for language {language or 'English'}; "
            "check the matching Tesseract language pack is installed."
        ) from exc

    grouped: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    count = len(data.get("text", []))
    for i in range(count):
        text = str(data["text"][i]).strip()
        try:
            confidence = float(data["conf"][i])
            x, y = int(data["left"][i]), int(data["top"][i])
            w, h = int(data["width"][i]), int(data["height"][i])
        except (TypeError, ValueError, IndexError):
            continue
        if not text or confidence < 0 or w <= 0 or h <= 0:
            continue
        key = (
            int(data.get("block_num", [0] * count)[i]),
            int(data.get("par_num", [0] * count)[i]),
            int(data.get("line_num", [0] * count)[i]),
        )
        grouped[key].append({
            "text": text,
            "x": x, "y": y, "right": x + w, "bottom": y + h,
            "confidence": confidence,
        })

    regions = []
    for words in grouped.values():
        words.sort(key=lambda word: word["x"])
        text = " ".join(word["text"] for word in words).strip()
        if not text:
            continue
        left = max(0, min(word["x"] for word in words))
        top = max(0, min(word["y"] for word in words))
        right = min(width, max(word["right"] for word in words))
        bottom = min(height, max(word["bottom"] for word in words))
        if right <= left or bottom <= top:
            continue
        regions.append({
            "text": text,
            "bbox": {"x": left, "y": top, "width": right-left, "height": bottom-top},
            "confidence": round(sum(word["confidence"] for word in words) / len(words), 1),
            "source": "tesseract-local",
        })

    ordered = sort_reading_order(regions, language=language)
    for index, region in enumerate(ordered):
        region["id"] = f"local-{index}"
    return {
        "regions": ordered,
        "image_size": {"width": width, "height": height},
        "detected_language": language or "English",
        "ocr_provider": "tesseract-local",
    }
