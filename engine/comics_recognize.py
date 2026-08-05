"""Text recognition for already-detected regions: what the text says,
given where it is.

The second half of the detect/recognise split (see engine/
comics_detect.py). Recognisers take a panel plus the boxes a detector
found and return one string per box, keyed by the detector's node_id.

WHY THIS IS A REGISTRY AND NOT A SWAP
-------------------------------------
The obvious plan is "replace Cloud Vision with manga-ocr, which is much
better on comic lettering." That is true and also a trap: manga-ocr is,
by its own package description, "OCR for Japanese manga" - Japanese
only. Castia's roster is English, Hindi, Japanese, Korean, Spanish and
Urdu, so a straight swap would upgrade one language and reduce the other
five to nothing.

So recognisers are registered per script and routed to. manga-ocr
handles Japanese, where it is genuinely the better tool; everything else
keeps a general recogniser. Adding a Korean specialist later means
registering it, not rewriting this module - which is the actual point of
putting a boundary here.

DEPLOYMENT REALITY, STATED PLAINLY
----------------------------------
manga-ocr depends on torch and transformers. Installed into this
project's python:3.11-slim image, that takes it from a couple of hundred
megabytes to several gigabytes, plus the resident memory to hold a model.
That is a hosting decision, not a pip install. `RemoteRecognizer` is
therefore a first-class option rather than an afterthought: the heavy
model runs as its own service, and the API container stays small.

Everything here degrades rather than raises. A recogniser that fails
leaves its regions with empty text for the human to fill in, because the
vision-LLM pass running concurrently may well have read them anyway.
"""
from __future__ import annotations

import logging
from typing import Protocol

from .comics_detect import DetectedBox

logger = logging.getLogger(__name__)

# BCP-47 codes routed to a script-specific recogniser. Deliberately keyed
# on the SCRIPT the detector/caller believes it is looking at, not on the
# chapter's declared source language - a chapter can be declared Japanese
# and still contain an English sign.
JAPANESE_CODES = {"ja", "ja-JP"}


class TextRecognizer(Protocol):
    """Reads already-located regions. Must not relocate or re-detect them.

    Returns {node_id: text}. A node_id may be absent from the reply when
    that region could not be read; callers treat a missing entry as empty
    text rather than as an error.
    """

    def recognize(self, image_bytes: bytes, boxes: list[DetectedBox]) -> dict[str, str]:
        ...


class CloudVisionRecognizer:
    """The general recogniser, and the fallback for every script without
    a specialist.

    Honest about what it is: this re-runs the same full Cloud Vision call
    the old single-step path used and matches its output back onto the
    detector's boxes by geometry. It is not cheaper than what it replaces
    - its value is that it satisfies the TextRecognizer contract, so the
    surrounding two-step architecture works today, on every language,
    with no new infrastructure, and individual scripts can be moved onto
    better recognisers one at a time instead of all at once.
    """

    def __init__(self, language: str | None = None):
        self._language = language

    def recognize(self, image_bytes: bytes, boxes: list[DetectedBox]) -> dict[str, str]:
        from . import comics_ocr

        try:
            result = comics_ocr.extract_text_regions(image_bytes, language=self._language)
        except Exception as exc:  # noqa: BLE001 - degrade, never raise; see module docstring
            logger.warning("Cloud Vision recognition failed: %s", exc)
            return {}
        return assign_by_overlap(boxes, result.get("regions", []))


class MangaOcrRecognizer:
    """manga-ocr (kha-white), a Japanese-manga-specific recogniser.

    Reads one CROPPED region at a time - it is a recogniser, not a
    detector, which is exactly why the detector has to run first. Loading
    is lazy and the model is cached on the instance, because construction
    downloads and initialises a transformer model; doing that per panel
    would dominate every other cost in this pipeline.

    NOT VERIFIED END TO END IN THIS REPOSITORY. The package installs, but
    its weights are fetched from Hugging Face at first use, which this
    development environment blocks at the network layer - so this adapter
    is written against manga-ocr's documented interface and unit-tested
    against a stub, never against the real model. Treat its accuracy as
    unmeasured until it has been run on real panels in a deployment that
    can reach the weights.
    """

    def __init__(self):
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from manga_ocr import MangaOcr

            self._model = MangaOcr()
        return self._model

    def recognize(self, image_bytes: bytes, boxes: list[DetectedBox]) -> dict[str, str]:
        import io

        from PIL import Image

        try:
            model = self._ensure_model()
            page = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:  # noqa: BLE001 - degrade, never raise
            logger.warning("manga-ocr unavailable, skipping recognition: %s", exc)
            return {}

        out: dict[str, str] = {}
        for box in boxes:
            try:
                crop = page.crop((box.x, box.y, box.x + box.width, box.y + box.height))
                text = model(crop)
            except Exception as exc:  # noqa: BLE001 - one bad crop must not lose the page
                logger.warning("manga-ocr failed on %s: %s", box.node_id, exc)
                continue
            if isinstance(text, str) and text.strip():
                out[box.node_id] = text.strip()
        return out


class RemoteRecognizer:
    """Calls a recogniser running as its own HTTP service, so a torch
    model never has to live in the API container.

    Expects: POST {url} with {"image_b64", "boxes": [{node_id, x, y,
    width, height}]}, replying {"texts": {node_id: text}}.
    """

    def __init__(self, url: str, timeout_seconds: float = 30.0):
        self._url = url
        self._timeout = timeout_seconds

    def recognize(self, image_bytes: bytes, boxes: list[DetectedBox]) -> dict[str, str]:
        import base64

        import httpx

        try:
            response = httpx.post(
                self._url,
                json={
                    "image_b64": base64.b64encode(image_bytes).decode("ascii"),
                    "boxes": [
                        {"node_id": b.node_id, **b.to_bbox()} for b in boxes
                    ],
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 - degrade, never raise
            logger.warning("Remote recogniser failed: %s", exc)
            return {}
        return parse_recognizer_payload(payload)


def parse_recognizer_payload(payload: dict) -> dict[str, str]:
    """Untrusted-input parsing for a recogniser service's reply. Only
    string keys mapping to non-empty strings survive.
    """
    texts = payload.get("texts")
    if not isinstance(texts, dict):
        return {}
    return {
        key: value.strip()
        for key, value in texts.items()
        if isinstance(key, str) and isinstance(value, str) and value.strip()
    }


def _overlap_area(box: DetectedBox, bbox: dict) -> int:
    left = max(box.x, bbox["x"])
    top = max(box.y, bbox["y"])
    right = min(box.x + box.width, bbox["x"] + bbox["width"])
    bottom = min(box.y + box.height, bbox["y"] + bbox["height"])
    if right <= left or bottom <= top:
        return 0
    return (right - left) * (bottom - top)


def assign_by_overlap(boxes: list[DetectedBox], regions: list[dict]) -> dict[str, str]:
    """Maps a whole-page recogniser's own regions onto the detector's
    boxes by greatest pixel overlap.

    Needed because a page-level recogniser (Cloud Vision) segments the
    page itself and will not return the detector's boxes. Overlap rather
    than index order: the two segmentations legitimately differ, and
    pairing by position would scramble them. Each region is consumed at
    most once, so two detector boxes can't both claim the same text.
    """
    assignments: dict[str, str] = {}
    used: set[int] = set()

    scored: list[tuple[int, str, int]] = []
    for box in boxes:
        for region_index, region in enumerate(regions):
            bbox = region.get("bbox")
            if not isinstance(bbox, dict):
                continue
            area = _overlap_area(box, bbox)
            if area > 0:
                scored.append((area, box.node_id, region_index))

    # Largest overlap first; node_id then region index as tie-breakers so
    # the same input always resolves identically.
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    for _area, node_id, region_index in scored:
        if node_id in assignments or region_index in used:
            continue
        text = regions[region_index].get("text", "")
        if isinstance(text, str) and text.strip():
            assignments[node_id] = text.strip()
            used.add(region_index)
    return assignments


def build_registry(language: str | None = None) -> dict[str, TextRecognizer]:
    """Recogniser per script code, plus a "default" every unrouted script
    falls back to.

    Japanese routes to manga-ocr only when it is actually switched on
    (config.MANGA_OCR_ENABLED). Off by default: it needs torch,
    transformers and downloadable weights, none of which are assumptions
    this project makes about a deployment.
    """
    from . import config

    registry: dict[str, TextRecognizer] = {"default": CloudVisionRecognizer(language)}

    if config.MANGA_OCR_URL:
        # Preferred when set: the heavy model runs elsewhere.
        registry["ja"] = RemoteRecognizer(config.MANGA_OCR_URL)
    elif config.MANGA_OCR_ENABLED:
        registry["ja"] = MangaOcrRecognizer()
    return registry


def select_recognizer(
    registry: dict[str, TextRecognizer], language_code: str | None
) -> TextRecognizer:
    """Picks the recogniser for a detected script, falling back to the
    general one. An unknown or missing code is not an error - it is the
    normal case for a panel whose script nothing has identified yet.
    """
    if language_code:
        base = language_code.split("-")[0].lower()
        if base in registry:
            return registry[base]
    return registry["default"]
