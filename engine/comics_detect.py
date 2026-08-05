"""Text-region detection for a comic panel: where the text is, not what
it says.

Splitting detection from recognition is the change that makes the rest of
the pipeline cheap and parallel. Cloud Vision's DOCUMENT_TEXT_DETECTION
does both at once, which forces everything downstream to wait for the
slow half (recognition) before it can even learn the boxes. With them
separated:

  - The detector runs first and alone. It is the fast, cheap step.
  - Its box ids are then handed to BOTH the vision-LLM narrative pass and
    the text recogniser, which run concurrently. Total latency is the
    slower of those two rather than their sum.
  - Because both are keyed to the same ids, the two results align
    exactly (engine/comics_align.py's node_id pass) instead of being
    matched back together by text similarity, which can mis-pair a
    badly-garbled bubble and send redraw at the wrong artwork.

`TextDetector` is a Protocol rather than a base class so an
implementation only has to be the right shape - no import of this module,
no inheritance. A local model, a hosted service, and the Cloud Vision
adapter below are interchangeable to every caller.

On running local models here, stated plainly: comic-text-detector and
similar YOLO-based bubble detectors need model weights and a torch
runtime. That is a real deployment decision, not a pip install - torch
alone takes this project's python:3.11-slim image from a couple of
hundred megabytes to several gigabytes. `RemoteDetector` exists so that
weight can live in its own service and never enter the main API image.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class DetectedBox:
    """One region of a panel believed to contain text.

    `node_id` is this pipeline's join key. It is issued by the detector
    and then threaded through every later stage - the recogniser's
    output, the vision model's reading, the alignment step, and finally
    the redraw call - so that all of them are provably talking about the
    same box rather than about whatever happened to be nth in a list.
    """

    node_id: str
    x: int
    y: int
    width: int
    height: int
    # The detector's own 0-1 confidence that this region holds text, when
    # it reports one. Not a claim about the TEXT's correctness - nothing
    # has been read at this point.
    confidence: float = 0.0

    def to_bbox(self) -> dict:
        """The {x, y, width, height} shape the rest of the codebase
        already speaks (engine/comics_ocr.py::_bounding_box,
        engine/comics_redraw.py, PanelWorkspace.tsx).
        """
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


class TextDetector(Protocol):
    """Finds text regions in a panel. Must not attempt to read them."""

    def detect(self, image_bytes: bytes) -> list[DetectedBox]:
        ...


def boxes_from_regions(regions: list[dict]) -> list[DetectedBox]:
    """Adapts the region dicts engine/comics_ocr.py already returns into
    DetectedBoxes, issuing a stable node_id per position.

    This is what lets the new architecture run on the CURRENT Cloud
    Vision call with no new infrastructure: the same response supplies
    both the boxes and a first-pass reading. It is a bridge, not the
    destination - it still pays for full DOCUMENT_TEXT_DETECTION, so it
    does not yet deliver the cost saving that a cheap local detector
    would. What it does deliver immediately is exact node_id alignment.
    """
    return [
        DetectedBox(
            node_id=f"r{index}",
            x=region["bbox"]["x"],
            y=region["bbox"]["y"],
            width=region["bbox"]["width"],
            height=region["bbox"]["height"],
            # Cloud Vision reports 0-100 here; DetectedBox is 0-1 so that
            # every detector reports confidence on one scale.
            confidence=round(region.get("confidence", 0.0) / 100.0, 3),
        )
        for index, region in enumerate(regions)
    ]


class CloudVisionDetector:
    """Uses the existing Cloud Vision call purely for geometry.

    Deliberately discards the text Vision also returned: in the two-step
    architecture the recogniser owns reading, and having two components
    silently disagree about what a bubble says is worse than having one
    answer. Callers that still want Vision's text should use
    engine/comics_ocr.extract_text_regions directly.
    """

    def __init__(self, language: str | None = None):
        self._language = language

    def detect(self, image_bytes: bytes) -> list[DetectedBox]:
        from . import comics_ocr

        result = comics_ocr.extract_text_regions(image_bytes, language=self._language)
        return boxes_from_regions(result.get("regions", []))


class RemoteDetector:
    """Calls a detector running as its own HTTP service.

    The point of this adapter is that a torch/YOLO bubble detector never
    has to be installed in the API container. It scales separately, can
    sit on a GPU box or scale to zero, and a failure in it degrades this
    service instead of crashing it.

    Expects: POST {url} with the raw image bytes, replying
    {"boxes": [{"node_id"?, "x", "y", "width", "height", "confidence"?}]}.
    node_id is optional in the reply - positional ids are issued here when
    the service doesn't supply them, so a simple detector doesn't have to
    care about this pipeline's join-key convention.
    """

    def __init__(self, url: str, timeout_seconds: float = 20.0):
        self._url = url
        self._timeout = timeout_seconds

    def detect(self, image_bytes: bytes) -> list[DetectedBox]:
        import httpx

        response = httpx.post(
            self._url,
            content=image_bytes,
            headers={"Content-Type": "application/octet-stream"},
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        return parse_detector_payload(payload)


def parse_detector_payload(payload: dict) -> list[DetectedBox]:
    """Turns a detector service's JSON into DetectedBoxes, treating every
    field as untrusted. A box missing any coordinate is dropped rather
    than defaulted to zero - a silently zero-sized box at the origin
    would send redraw at the top-left corner of the artwork.
    """
    raw = payload.get("boxes")
    if not isinstance(raw, list):
        return []

    boxes: list[DetectedBox] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            continue
        try:
            x, y = int(entry["x"]), int(entry["y"])
            width, height = int(entry["width"]), int(entry["height"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Detector returned an unusable box, skipping: %r", entry)
            continue
        if width <= 0 or height <= 0:
            continue
        node_id = entry.get("node_id")
        if not isinstance(node_id, str) or not node_id.strip():
            node_id = f"r{index}"
        confidence = entry.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            confidence = 0.0
        boxes.append(
            DetectedBox(
                node_id=node_id.strip(),
                x=x,
                y=y,
                width=width,
                height=height,
                confidence=max(0.0, min(1.0, float(confidence))),
            )
        )
    return boxes
