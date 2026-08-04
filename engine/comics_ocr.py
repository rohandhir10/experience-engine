"""Comic panel OCR: pulls speech-bubble/caption text out of an uploaded
panel image via Google Cloud Vision's DOCUMENT_TEXT_DETECTION, for
/comics's panel-by-panel review workspace (components/comics/
PanelWorkspace.tsx) to pre-fill instead of a fully manual paste.

Replaces the original Tesseract-based scaffold (see docs/
CAPABILITY_MATRIX.md's "/comics OCR integration" and "Switch to Google
Cloud Vision" entries for that history and the reasoning behind the
switch). Tesseract required a language pack installed per script AND a
language picked before every run, with no reliable way to guess script
on its own; the real target content this product needs to handle
(Japanese manga, Chinese manhua, Spanish/French indie comics, alongside
AURA's existing Hindi/Korean/Urdu roster) made that untenable. Cloud
Vision auto-detects script/language per block of text and needs no
per-language setup on this server at all.

The tradeoff, stated plainly: this is now a paid, metered, external API
call instead of a free local binary, and it requires a real GCP service
account credential configured in this deployment's environment
(GOOGLE_CLOUD_VISION_CREDENTIALS_JSON — base64-encoded service-account
JSON, not a plain API key; see docs/CAPABILITY_MATRIX.md's Cloud Vision
entry for why a service account was chosen over the simpler API-key
auth this module originally shipped with, and for the exact GCP console
setup steps). Unset or invalid, this raises OcrError rather than
silently failing, falling back to a worse method, or returning a
fabricated result.

Deliberately NOT an adaptation step - this only extracts text and where
it was found on the page (a bounding box per detected text block). The
extracted text is handed back to the browser as a draft the human
reviews and edits, the same "never pipe straight into anything" review
step engine/youtube_ingest.py already established for captions.

What this can't fix, stated plainly, same discipline as every other
ingestion module in this project:
  - Cloud Vision is trained on general documents and photographed text,
    not comic lettering specifically - hand-drawn fonts, outlined/bold
    sound-effect text, and text warped to follow a speech-bubble tail
    can still come back wrong or garbled, same caveat manga/webtoon OCR
    has regardless of provider. Every region carries Vision's own
    per-block confidence so a low-confidence result can be flagged
    rather than silently trusted.
  - Reading order is a plain top-to-bottom, left-to-right ordering of
    detected blocks, not a real guess at panel/bubble reading order -
    which can run right-to-left or in a Z-pattern across multiple
    bubbles. The human reviewing the draft is expected to reorder it.
"""
from __future__ import annotations

import base64
import binascii
import json
import logging
import os

import httpx
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

_VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
_CREDENTIALS_ENV_VAR = "GOOGLE_CLOUD_VISION_CREDENTIALS_JSON"
_SCOPES = ["https://www.googleapis.com/auth/cloud-vision"]
_REQUEST_TIMEOUT_SECONDS = 30.0

# Below this per-block confidence (Vision's own 0-1 scale, reported here
# scaled to 0-100 to match the rest of this API's percentages), a result
# is unreliable enough that the reviewing human should be told plainly -
# stylized comic lettering can score below this even when the text is
# basically legible to a person.
_LOW_CONFIDENCE_THRESHOLD = 60.0

# AURA's language names -> BCP-47 codes, used ONLY as an optional
# `imageContext.languageHints` bias when the caller happens to know the
# language - never required, never used to gate or reject a request.
# Cloud Vision auto-detects script/language per block on its own; this
# is a hint, not a dependency, unlike the old Tesseract setup.
_LANGUAGE_HINTS = {
    "English": "en",
    "Hindi": "hi",
    "Japanese": "ja",
    "Korean": "ko",
    "Spanish": "es",
    "Urdu": "ur",
}

# BCP-47 code -> a human-readable name, for surfacing what Vision itself
# detected (page.property.detectedLanguages) back to the frontend - NOT
# the same direction as _LANGUAGE_HINTS above, and deliberately broader
# than AURA's current 6-language roster: real target content for
# /comics (Chinese manhua, French indie comics) isn't a language AURA
# adapts yet, but a human reviewing a chapter still benefits from being
# told plainly "this looks like Chinese," rather than seeing nothing
# just because there's no engine profile for it. An unrecognized code
# is reported as the raw BCP-47 string rather than hidden.
_LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "ur": "Urdu",
    "fr": "French",
    "zh": "Chinese",
    "zh-Hans": "Chinese (Simplified)",
    "zh-Hant": "Chinese (Traditional)",
}


class OcrError(Exception):
    """Raised for any OCR failure a human needs to see plainly, not a stack trace."""


def _access_token() -> str:
    """Builds a fresh OAuth access token from the service-account JSON in
    GOOGLE_CLOUD_VISION_CREDENTIALS_JSON (base64-encoded, since Railway
    env vars are single-line strings, not files) and refreshes it
    immediately so the returned token is valid to use right away.

    Deliberately NOT cached across calls: a cached token needs a
    thread-safe refresh-before-expiry mechanism to be correct under
    concurrent requests, which is real complexity not worth taking on
    for this scaffold's request volume. The known cost, stated plainly:
    every OCR call does a real token-exchange round-trip to Google's
    OAuth endpoint in addition to the Vision API call itself - a real,
    deferred optimization, not an oversight.
    """
    encoded = os.environ.get(_CREDENTIALS_ENV_VAR, "")
    if not encoded:
        raise OcrError(
            f"{_CREDENTIALS_ENV_VAR} is not set on this server. Panel OCR needs "
            "a base64-encoded Google Cloud service-account JSON key - see "
            "docs/CAPABILITY_MATRIX.md's Cloud Vision entry for setup."
        )
    try:
        info = json.loads(base64.b64decode(encoded))
    except (binascii.Error, ValueError, json.JSONDecodeError) as exc:
        raise OcrError(
            f"{_CREDENTIALS_ENV_VAR} is not valid base64-encoded JSON: {exc}"
        ) from exc

    try:
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=_SCOPES
        )
        credentials.refresh(GoogleAuthRequest())
    except (ValueError, KeyError, GoogleAuthError) as exc:
        raise OcrError(f"Could not authenticate with Google Cloud: {exc}") from exc

    return credentials.token


def _block_text(block: dict) -> str:
    """Reconstructs one block's text from Vision's nested paragraph ->
    word -> symbol structure. Words within a paragraph are joined with
    single spaces; paragraphs within a block are joined with newlines -
    a reasonable default for a speech bubble that may have more than one
    line, without trying to reproduce Vision's detected break types
    exactly.
    """
    paragraphs = []
    for paragraph in block.get("paragraphs", []):
        words = []
        for word in paragraph.get("words", []):
            words.append("".join(s.get("text", "") for s in word.get("symbols", [])))
        paragraph_text = " ".join(w for w in words if w)
        if paragraph_text:
            paragraphs.append(paragraph_text)
    return "\n".join(paragraphs)


def _bounding_box(vertices: list[dict]) -> dict:
    """Vision's boundingBox.vertices is a (possibly rotated)
    quadrilateral's 4 corners; this collapses it to the axis-aligned
    box the frontend's percentage-coordinate overlay expects (same
    {x, y, width, height} shape the old Tesseract-based version used,
    so components/comics/PanelWorkspace.tsx needed no changes).
    """
    xs = [v.get("x", 0) for v in vertices]
    ys = [v.get("y", 0) for v in vertices]
    if not xs or not ys:
        return {"x": 0, "y": 0, "width": 0, "height": 0}
    x, y = min(xs), min(ys)
    return {"x": x, "y": y, "width": max(xs) - x, "height": max(ys) - y}


def _detected_languages(page: dict) -> list[dict]:
    """Reads Vision's own page-level script/language detection
    (page.property.detectedLanguages), sorted most-confident first. This
    is the actual "no language picker needed" payoff of switching to
    Cloud Vision (see this module's docstring) - the old Tesseract
    version had no equivalent at all, so a chapter's source language had
    to be picked by the human before every single OCR run. `language_name`
    is None for any BCP-47 code this project doesn't recognize (see
    _LANGUAGE_NAMES) rather than guessing or omitting the entry outright.
    """
    languages = page.get("property", {}).get("detectedLanguages", [])
    result = [
        {
            "language_code": lang["languageCode"],
            "language_name": _LANGUAGE_NAMES.get(lang["languageCode"]),
            "confidence": round(lang.get("confidence", 0.0) * 100, 1),
        }
        for lang in languages
        if lang.get("languageCode")
    ]
    result.sort(key=lambda entry: entry["confidence"], reverse=True)
    return result


def extract_text_regions(image_bytes: bytes, language: str | None = None) -> dict:
    """Sends one panel image to Google Cloud Vision's
    DOCUMENT_TEXT_DETECTION feature and returns:
    {"regions": [{"text", "bbox": {x, y, width, height}, "confidence"}],
     "full_text": str, "warning": str | None,
     "image_width": int, "image_height": int,
     "detected_languages": [{"language_code", "language_name", "confidence"}]}

    bbox values are pixel coordinates in the original image - the
    caller is expected to scale them against the image's actual
    rendered size, not assume any fixed display resolution.

    detected_languages is Vision's own page-level script/language
    detection, most-confident first - empty when nothing was detected
    (e.g. no text found at all). This is the frontend's actual source
    for "what language is this chapter probably in," replacing what
    used to require a human picking a language before every Tesseract
    run; see components/comics/PanelWorkspace.tsx and lib/
    chapterLanguage.ts for how it's aggregated across a whole chapter's
    panels.

    `language` is accepted for signature compatibility with the
    pre-Cloud-Vision version of this function but is NOT used to gate
    anything - see _LANGUAGE_HINTS above. Pass None (the default) to let
    Vision auto-detect entirely on its own, which is the normal case.

    Raises OcrError if GOOGLE_CLOUD_VISION_CREDENTIALS_JSON isn't
    configured or isn't a valid service-account key, if the request
    fails, or if Vision itself reports an error - never returns a
    fabricated/placeholder result on failure.
    """
    token = _access_token()

    request_payload: dict = {
        "requests": [
            {
                "image": {"content": base64.b64encode(image_bytes).decode("ascii")},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
            }
        ]
    }
    hint = _LANGUAGE_HINTS.get(language) if language else None
    if hint:
        request_payload["requests"][0]["imageContext"] = {"languageHints": [hint]}

    try:
        response = httpx.post(
            _VISION_ENDPOINT,
            headers={"Authorization": f"Bearer {token}"},
            json=request_payload,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        logger.warning("Cloud Vision request failed: %s", exc)
        raise OcrError(
            "Could not reach Google Cloud Vision right now. This is usually "
            "temporary - try again in a moment."
        ) from exc

    if response.status_code != 200:
        logger.warning(
            "Cloud Vision returned HTTP %d: %s", response.status_code, response.text[:500]
        )
        raise OcrError(
            f"Google Cloud Vision returned an error (HTTP {response.status_code})."
        )

    data = response.json()
    result = (data.get("responses") or [{}])[0]
    if "error" in result:
        message = result["error"].get("message", "unknown error")
        raise OcrError(f"Google Cloud Vision could not process this image: {message}")

    full_annotation = result.get("fullTextAnnotation")
    pages = full_annotation.get("pages") if full_annotation else None
    if not pages:
        return {
            "regions": [],
            "full_text": "",
            "warning": "No text detected in this panel. Type it in by hand.",
            "image_width": 0,
            "image_height": 0,
            "detected_languages": [],
        }

    page = pages[0]
    regions = []
    for block in page.get("blocks", []):
        text = _block_text(block)
        if not text.strip():
            continue
        vertices = block.get("boundingBox", {}).get("vertices", [])
        confidence = round(block.get("confidence", 0.0) * 100, 1)
        regions.append({"text": text, "bbox": _bounding_box(vertices), "confidence": confidence})

    full_text = "\n\n".join(r["text"] for r in regions)

    warning = None
    if not regions:
        warning = "No text detected in this panel. Type it in by hand."
    else:
        low_confidence = [r for r in regions if r["confidence"] < _LOW_CONFIDENCE_THRESHOLD]
        if len(low_confidence) >= len(regions) / 2:
            warning = (
                "OCR confidence is low for much of this panel - common for "
                "stylized comic lettering. Check every region against the "
                "image before trusting this text."
            )

    return {
        "regions": regions,
        "full_text": full_text,
        "warning": warning,
        "image_width": page.get("width", 0),
        "image_height": page.get("height", 0),
        "detected_languages": _detected_languages(page),
    }
