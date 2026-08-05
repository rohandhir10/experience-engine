"""A vision-capable LLM reading of a comic panel, run alongside Cloud
Vision's OCR rather than instead of it.

What this adds that OCR cannot do, stated concretely:
  - Reads stylized/hand-drawn lettering that classic OCR garbles, because
    it can use the surrounding artwork as context instead of matching
    glyph shapes in isolation.
  - Classifies each piece of text (dialogue / sfx / narration /
    background), so sound effects and shop signs stop being fed into the
    adapted dialogue script as if a character had said them.
  - Attributes dialogue to a speaker when the panel makes that visually
    unambiguous, which is what character voice consistency across a
    chapter needs and OCR has no way to supply.

What it deliberately does NOT do: report bounding boxes. Vision-capable
LLMs are unreliable at exact pixel coordinates, and the redraw/typeset
path (engine/comics_redraw.py) needs real geometry, so boxes keep coming
from Cloud Vision and this module's text is matched back onto them
afterwards (engine/comics_align.py).

Failure is always soft. Every failure mode here - no API key, a model
error, unparseable output, an empty reading - returns no readings rather
than raising, because the caller (server/main.py's OCR endpoint) already
has a complete, usable Cloud Vision result in hand. Degrading to plain
OCR is correct; failing the request the user asked for is not.
"""
from __future__ import annotations

import base64
import logging

from . import config
from .comics_align import Reading

logger = logging.getLogger(__name__)

# Panel reading is a single structured extraction, not a creative task -
# it needs enough room for a dense page of dialogue and nothing more.
_MAX_TOKENS = 1500

_VALID_KINDS = {"dialogue", "sfx", "narration", "background", "unknown"}

_SYSTEM = (
    "You read comic and webtoon panels. You are given one panel image. "
    "Report every piece of written text visible in it, exactly as it "
    "appears.\n\n"
    "Rules:\n"
    "1. Transcribe the text as printed, in its ORIGINAL language. Do not "
    "translate, correct spelling, or tidy up phrasing - a later stage "
    "does the adaptation, and it needs the real source text.\n"
    "2. Classify each piece: 'dialogue' (someone is speaking), 'sfx' (a "
    "sound effect), 'narration' (a caption box), or 'background' (a sign, "
    "a poster, text that is part of the artwork).\n"
    "3. For dialogue, name the speaker ONLY when the panel makes it "
    "visually clear - a bubble tail pointing at a character, or an "
    "unmistakable single speaker. If you are guessing, use null. A wrong "
    "speaker is worse than no speaker, because it silently corrupts "
    "character voice for the whole chapter.\n"
    "4. Do not invent text that isn't there. If the panel has no text at "
    "all, return an empty list.\n\n"
    'Respond with ONLY a JSON object: {"readings": [{"text": str, '
    '"kind": "dialogue"|"sfx"|"narration"|"background", "speaker": str '
    "or null}]}, in natural reading order for this panel's language."
)


def _parse_readings(data: dict) -> list[Reading]:
    """Pulls a clean list of Readings out of the model's JSON, dropping
    anything malformed rather than trusting the shape. An unknown `kind`
    is downgraded to "unknown" instead of being passed through, so
    downstream filtering (e.g. "exclude sfx") can rely on the vocabulary.
    """
    raw = data.get("readings")
    if not isinstance(raw, list):
        return []

    readings: list[Reading] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        kind = entry.get("kind")
        if kind not in _VALID_KINDS:
            kind = "unknown"
        speaker = entry.get("speaker")
        if not isinstance(speaker, str) or not speaker.strip():
            speaker = None
        readings.append(Reading(text=text.strip(), kind=kind, speaker=speaker))
    return readings


def read_panel(image_bytes: bytes, mime_type: str = "image/jpeg") -> list[Reading]:
    """Asks a vision-capable model what text it can see in this panel.

    Returns [] on any failure - see this module's docstring for why that
    is the correct behavior rather than raising.
    """
    if not config.VISION_READING_ENABLED:
        return []

    try:
        from .llm_client import create_vision_client

        client = create_vision_client()
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        logger.warning("Vision reading unavailable, falling back to OCR only: %s", exc)
        return []

    encoded = base64.b64encode(image_bytes).decode("ascii")
    try:
        data = client.complete_json_with_image(
            _SYSTEM,
            "Read this panel.",
            image_data_url=f"data:{mime_type};base64,{encoded}",
            max_tokens=_MAX_TOKENS,
            stage="comics_vision_read",
        )
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        logger.warning("Vision reading call failed, falling back to OCR only: %s", exc)
        return []

    return _parse_readings(data)
