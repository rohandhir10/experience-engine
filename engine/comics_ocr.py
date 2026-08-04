"""Comic panel OCR: pulls speech-bubble/caption text out of an uploaded
panel image via Tesseract (open source, deterministic, no API key and no
per-call cost), for /comics's panel-by-panel review workspace
(components/comics/PanelWorkspace.tsx) to pre-fill instead of a fully
manual paste.

Deliberately NOT an adaptation step - this only extracts text and where
it was found on the page (a bounding box per detected text region). The
extracted text is handed back to the browser as a draft the human
reviews and edits, the same "never pipe straight into anything" review
step engine/youtube_ingest.py already established for captions.

What this can't fix, stated plainly, same discipline as youtube_ingest.py:
  - Tesseract is trained on ordinary printed/scanned text, not stylized
    comic lettering (hand-drawn fonts, outlined/bold sound-effect text,
    text warped to follow a speech-bubble tail). Expect it to miss or
    garble stylized text more often than it does printed prose - every
    region comes back with Tesseract's own per-word confidence, averaged
    per region, so a low-confidence result can be flagged rather than
    silently trusted.
  - Only English-language OCR data (tesseract-ocr-eng) ships with this
    engine today (see the root Dockerfile). Requesting any other AURA-
    supported language raises OcrError naming exactly which system
    package is missing, rather than silently falling back to English or
    returning garbage - the remaining five languages' tesseract data
    packages (tesseract-ocr-hin/jpn/kor/spa/urd) are a follow-up, not
    done here.
  - Reading order is a plain top-to-bottom, left-to-right sort of
    detected regions - not a real guess at panel/bubble reading order,
    which can run right-to-left (Urdu, some manga-style layouts) or in a
    Z-pattern across multiple bubbles. The human reviewing the draft is
    expected to reorder it, the same way youtube_ingest's section
    boundaries are a guess the human corrects, not a final answer.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from pytesseract import TesseractError, TesseractNotFoundError
except ImportError:  # pytesseract itself isn't installed
    pytesseract = None  # type: ignore[assignment]

    class TesseractError(Exception):  # type: ignore[no-redef]
        pass

    class TesseractNotFoundError(Exception):  # type: ignore[no-redef]
        pass


class OcrError(Exception):
    """Raised for any OCR failure a human needs to see plainly, not a stack trace."""


# AURA's language names -> Tesseract's ISO 639-2 language codes. Only
# "eng" actually ships with this engine's Docker image today; the rest
# are named here so OcrError can say exactly what's missing instead of
# guessing or silently defaulting to English.
_TESSERACT_LANGUAGE_CODES = {
    "English": "eng",
    "Hindi": "hin",
    "Japanese": "jpn",
    "Korean": "kor",
    "Spanish": "spa",
    "Urdu": "urd",
}

# Below this per-word confidence (Tesseract's own 0-100 scale), a result
# is unreliable enough that the reviewing human should be told plainly -
# stylized comic lettering routinely scores below this even when the
# text is basically legible to a person.
_LOW_CONFIDENCE_THRESHOLD = 60.0


@dataclass
class TextRegion:
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float  # 0-100, averaged over this region's words


def _group_words_into_regions(ocr_data: dict) -> list[TextRegion]:
    """Tesseract's image_to_data returns one row per detected word, each
    tagged with (block_num, par_num). Grouping by that pair clusters
    words into the same layout region Tesseract's own page-segmentation
    already separated, which in practice usually lines up with one
    speech bubble or caption box per region rather than the whole page
    as one blob - not guaranteed, just the deterministic grouping
    Tesseract's own layout analysis gives us for free.
    """
    groups: dict[tuple[int, int], list[int]] = {}
    for i in range(len(ocr_data["text"])):
        text = ocr_data["text"][i].strip()
        if not text:
            continue
        key = (ocr_data["block_num"][i], ocr_data["par_num"][i])
        groups.setdefault(key, []).append(i)

    regions: list[TextRegion] = []
    for indices in groups.values():
        words = [ocr_data["text"][i].strip() for i in indices]
        lefts = [ocr_data["left"][i] for i in indices]
        tops = [ocr_data["top"][i] for i in indices]
        rights = [ocr_data["left"][i] + ocr_data["width"][i] for i in indices]
        bottoms = [ocr_data["top"][i] + ocr_data["height"][i] for i in indices]
        confidences = [
            float(ocr_data["conf"][i]) for i in indices if float(ocr_data["conf"][i]) >= 0
        ]

        x, y = min(lefts), min(tops)
        regions.append(
            TextRegion(
                text=" ".join(words),
                x=x,
                y=y,
                width=max(rights) - x,
                height=max(bottoms) - y,
                confidence=sum(confidences) / len(confidences) if confidences else 0.0,
            )
        )

    # Stable top-to-bottom-then-left-to-right order - see the module
    # docstring's note on reading order not being a real structural guess.
    regions.sort(key=lambda r: (r.y, r.x))
    return regions


def extract_text_regions(image_bytes: bytes, language: str = "English") -> dict:
    """Runs Tesseract over one panel image and returns a dict:
    {"regions": [{"text", "bbox": {x, y, width, height}, "confidence"}],
     "full_text": str, "warning": str | None,
     "image_width": int, "image_height": int}

    bbox values are pixel coordinates in the original image - the caller
    is expected to scale them against the image's actual rendered size,
    not assume any fixed display resolution.

    Raises OcrError if Tesseract/pytesseract isn't installed, if the
    requested language's data pack isn't installed, or if the image
    can't be decoded. Never returns a fabricated/placeholder result on
    failure - an error the caller must surface is preferred over a
    result that looks real and isn't.
    """
    if pytesseract is None:
        raise OcrError(
            "pytesseract is not installed on this server. Add it to "
            "requirements.txt and install tesseract-ocr (see the Dockerfile)."
        )

    lang_code = _TESSERACT_LANGUAGE_CODES.get(language)
    if lang_code is None:
        raise OcrError(
            f"OCR is not configured for {language!r} - supported languages "
            f"are {sorted(_TESSERACT_LANGUAGE_CODES)}."
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception as exc:  # noqa: BLE001 - surfaced as OcrError either way
        raise OcrError(f"Could not decode this image: {exc}") from exc

    try:
        ocr_data = pytesseract.image_to_data(
            image, lang=lang_code, output_type=pytesseract.Output.DICT
        )
    except TesseractNotFoundError as exc:
        raise OcrError("The tesseract-ocr binary is not installed on this server.") from exc
    except TesseractError as exc:
        raise OcrError(
            f"Tesseract could not process this image with language data "
            f"{lang_code!r} - is tesseract-ocr-{lang_code} installed? ({exc})"
        ) from exc

    regions = _group_words_into_regions(ocr_data)
    full_text = "\n\n".join(r.text for r in regions)

    warning = None
    if not regions:
        warning = "No text detected in this panel. Type it in by hand."
    else:
        low_confidence = [r for r in regions if r.confidence < _LOW_CONFIDENCE_THRESHOLD]
        if len(low_confidence) >= len(regions) / 2:
            warning = (
                "OCR confidence is low for much of this panel - common for stylized "
                "comic lettering. Check every region against the image before "
                "trusting this text."
            )

    return {
        "regions": [
            {
                "text": r.text,
                "bbox": {"x": r.x, "y": r.y, "width": r.width, "height": r.height},
                "confidence": round(r.confidence, 1),
            }
            for r in regions
        ],
        "full_text": full_text,
        "warning": warning,
        "image_width": image.width,
        "image_height": image.height,
    }
