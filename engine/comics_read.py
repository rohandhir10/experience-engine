"""The two-step panel read: detect, then read twice in parallel.

    detect boxes                     (step 1, fast, alone)
         |
         +--> vision-LLM narrative pass  --+   (step 2, concurrent)
         +--> text recogniser             --+
                        |
                  align by node_id

Step 1 has to finish first - both readers are handed its box ids. Step 2
runs both at once, so its latency is the slower of the two rather than
their sum, and because both are keyed to the same ids the results align
exactly instead of being matched back together by text similarity.

That last point is the real prize. Similarity matching works well and is
still the fallback, but it can fail on precisely the bubbles that need
help most: when a recogniser garbles a bubble badly enough, no score
pairs it with the model's clean reading of the same bubble. A shared id
has no such failure mode, and a mis-pairing here is not cosmetic - the
redraw path erases and re-letters whatever box it is handed.

Every stage degrades rather than raises. No detector, a dead recogniser,
a failed vision call: each is survivable and leaves a usable draft,
because a human reviews this workspace either way.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from . import comics_align, comics_detect, comics_recognize, comics_vision
from .comics_detect import DetectedBox, TextDetector
from .comics_recognize import TextRecognizer

logger = logging.getLogger(__name__)


def build_detector(language: str | None = None) -> TextDetector:
    """A dedicated detector service when one is configured, otherwise
    boxes derived from the Cloud Vision call this pipeline already makes.

    The fallback is honest about its limits: it still pays for full
    DOCUMENT_TEXT_DETECTION, so it does not yet deliver the cost saving a
    cheap local detector would. What it does deliver immediately is the
    node_id-keyed structure everything downstream needs, so the
    architecture is real before the model swap lands rather than after.
    """
    from . import config

    if config.TEXT_DETECTOR_URL:
        return comics_detect.RemoteDetector(config.TEXT_DETECTOR_URL)
    return comics_detect.CloudVisionDetector(language)


def read_panel_two_step(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    language: str | None = None,
    script_code: str | None = None,
    detector: TextDetector | None = None,
    recognizer: TextRecognizer | None = None,
    vision_client=None,
) -> dict:
    """Runs the full two-step read and returns the same result shape
    engine/comics_ocr.extract_text_regions produces, enriched.

    `script_code` routes to a script-specific recogniser (manga-ocr for
    Japanese; see comics_recognize.build_registry). It is separate from
    `language`, which is only ever a hint passed to Cloud Vision.

    Returns {} when detection found nothing, letting the caller fall
    back to the single-step path rather than inventing an empty result.

    `vision_client`, when given, is forwarded to comics_vision.read_panel
    so the caller can inspect its real call_log (measured token usage)
    afterward instead of it being built and discarded internally.
    """
    detector = detector or build_detector(language)

    try:
        boxes = detector.detect(image_bytes)
    except Exception as exc:  # noqa: BLE001 - the caller can still fall back
        logger.warning("Detection failed, no two-step read possible: %s", exc)
        return {}

    if not boxes:
        return {}

    if recognizer is None:
        registry = comics_recognize.build_registry(language)
        recognizer = comics_recognize.select_recognizer(registry, script_code)

    known_regions = [{"node_id": box.node_id, "text": ""} for box in boxes]

    # The concurrent half. Neither call depends on the other's output -
    # both were given the boxes already - so running them together costs
    # max(a, b) instead of a + b.
    with ThreadPoolExecutor(max_workers=2) as pool:
        recognize_future = pool.submit(recognizer.recognize, image_bytes, boxes)
        vision_future = pool.submit(
            comics_vision.read_panel, image_bytes, mime_type, known_regions, vision_client
        )
        try:
            texts = recognize_future.result()
        except Exception as exc:  # noqa: BLE001 - degrade to whatever vision read
            logger.warning("Recognition failed, continuing on the vision read: %s", exc)
            texts = {}
        # read_panel never raises - it returns [] - so this cannot cost
        # the recogniser's result.
        readings = vision_future.result()

    return assemble(boxes, texts, readings)


def assemble(
    boxes: list[DetectedBox],
    texts: dict[str, str],
    readings: list[comics_align.Reading],
) -> dict:
    """Merges detector geometry, recogniser text and the narrative pass
    into one result, aligned on node_id.

    Boxes always come from the detector and are never touched by either
    reader - the redraw path depends on that geometry being real.
    """
    aligned = comics_align.align_readings(
        [texts.get(box.node_id, "") for box in boxes],
        readings,
        node_ids=[box.node_id for box in boxes],
    )

    regions = []
    for box, match in zip(boxes, aligned.regions):
        reading = match.reading
        regions.append(
            {
                "node_id": box.node_id,
                "text": match.text,
                "bbox": box.to_bbox(),
                # The detector's 0-1 confidence, reported on the 0-100
                # scale the existing API already uses for this field.
                "confidence": round(box.confidence * 100, 1),
                "text_source": match.source,
                "kind": reading.kind if reading else "unknown",
                "speaker": reading.speaker if reading else None,
                "speaker_confidence": reading.speaker_confidence if reading else 0.0,
                "speaker_appearance": reading.speaker_appearance if reading else None,
                "tone": reading.tone if reading else "neutral",
                "tone_note": reading.tone_note if reading else None,
                "emphasis": reading.emphasis if reading else "normal",
                "reading_index": reading.reading_index if reading else 0,
            }
        )

    # Reading order comes from the narrative pass where it exists, since
    # geometry alone guesses it badly for right-to-left and Z-pattern
    # layouts. Regions themselves stay in DETECTOR order - downstream
    # code indexes them positionally against their boxes - so the order
    # is expressed as a separate list of ids rather than by reordering.
    ordered = sorted(
        regions,
        key=lambda r: (r["reading_index"] or len(regions) + 1, r["node_id"]),
    )

    return {
        "regions": regions,
        "reading_order": [r["node_id"] for r in ordered],
        "full_text": "\n\n".join(r["text"] for r in ordered if r["text"]),
        "warning": _warning_for(regions),
        "vision_corrected_count": aligned.corrected_count,
        "unplaced_readings": [
            {"text": r.text, "kind": r.kind, "speaker": r.speaker} for r in aligned.unplaced
        ],
    }


def _warning_for(regions: list[dict]) -> str | None:
    """One honest caveat for the human reviewing this panel, or None."""
    if not regions:
        return "No text detected in this panel. Type it in by hand."
    empty = [r for r in regions if not r["text"].strip()]
    if len(empty) == len(regions):
        return (
            "Text regions were found but none could be read. Type them in "
            "by hand, or check that a recogniser is configured."
        )
    if empty:
        return (
            f"{len(empty)} of {len(regions)} detected regions came back empty - "
            "check them against the image."
        )
    return None
