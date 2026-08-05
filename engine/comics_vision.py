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
import math

from . import config
from .comics_align import Reading

logger = logging.getLogger(__name__)

# Panel reading is a single structured extraction, not a creative task -
# it needs enough room for a dense page of dialogue and nothing more.
_MAX_TOKENS = 1500

# The text-node vocabulary. Finer-grained than "is this dialogue?"
# because each distinction changes what a localizer actually does:
# speech and thought are typeset in different faces, a shout needs room
# to stay large, signage is often left untouched entirely, and SFX are
# frequently redrawn rather than replaced.
_VALID_KINDS = {
    "speech",
    "thought",
    "shout",
    "whisper",
    "narration",
    "sfx",
    "signage",
    "unknown",
}

# Bounded on purpose. Free-text emotion reads richer but cannot be
# compared across panels, so it could never drive voice consistency -
# only decorate a UI. Anything this list can't hold goes in `tone_note`.
_VALID_TONES = {
    "neutral",
    "tender",
    "angry",
    "fearful",
    "joyful",
    "sad",
    "sarcastic",
    "urgent",
    "resigned",
    "playful",
}

_VALID_EMPHASIS = {"normal", "bold", "large", "small", "trembling"}

# The response contract, kept as one string so the prompt and the parser
# below can be read against each other without hunting through f-strings.
_SCHEMA_DOC = """{
  "text_nodes": [
    {
      "node_id": str | null,
      "text": str,
      "kind": "speech"|"thought"|"shout"|"whisper"|"narration"|"sfx"|"signage"|"unknown",
      "reading_index": int,
      "speaker": str | null,
      "speaker_confidence": number,
      "speaker_appearance": str | null,
      "speaker_visible": bool,
      "tone": "neutral"|"tender"|"angry"|"fearful"|"joyful"|"sad"|"sarcastic"|"urgent"|"resigned"|"playful",
      "tone_note": str | null,
      "emphasis": "normal"|"bold"|"large"|"small"|"trembling"
    }
  ]
}"""

_SYSTEM = (
    "You are the Narrative Director for a comic/webtoon localization "
    "pipeline. You are shown one panel image. Your job is not to "
    "translate it - a later stage does that - but to give the "
    "translator everything they cannot get from the raw text alone: who "
    "is speaking, what kind of text each node is, and how it is "
    "delivered.\n\n"
    "TRANSCRIPTION\n"
    "1. Report every piece of written text in the panel, transcribed "
    "EXACTLY as printed and in its ORIGINAL language. Do not translate, "
    "correct spelling, expand abbreviations, or tidy phrasing. A later "
    "stage needs the real source text, and your transcription is also "
    "matched against a separate OCR pass - rewriting it breaks that "
    "match.\n"
    "2. Do not invent text. If the panel has no text, return an empty "
    "list.\n\n"
    "CLASSIFICATION\n"
    "3. Set `kind` from the shape and context of the lettering, not from "
    "what it says: 'speech' (a bubble with a tail), 'thought' (a cloud "
    "bubble, or a tail of small circles), 'shout' (a jagged/burst "
    "bubble, or oversized lettering), 'whisper' (a dashed or faint "
    "bubble, or notably small lettering), 'narration' (a caption box, "
    "usually rectangular and untailed), 'sfx' (a sound effect drawn "
    "into the art), 'signage' (text that is part of the world - a shop "
    "sign, a phone screen, a poster).\n\n"
    "SPEAKER\n"
    "4. `speaker` is a PANEL-LOCAL label: use Character_A, Character_B, "
    "... assigned in order of first appearance in this panel. You are "
    "seeing one panel in isolation - do NOT try to match these to "
    "characters from elsewhere, and do not use real names even if the "
    "dialogue says one.\n"
    "5. `speaker_appearance` is a short physical description of that "
    "character as drawn here ('tall, dark bob, red jacket'). Be "
    "concrete and visual. This is how the same person gets recognised "
    "across panels later, so it matters more than the label itself.\n"
    "6. `speaker_confidence` is your own 0-1 certainty about the "
    "attribution. Use a high value ONLY when something in the art "
    "settles it - a tail pointing at a figure, or a single character "
    "alone in frame. If you are inferring from context or dialogue "
    "content, say so with a low value. A confidently wrong speaker is "
    "the worst output you can produce here: it silently corrupts that "
    "character's voice for the whole chapter. When you genuinely cannot "
    "tell, use null and 0.\n"
    "7. `speaker_visible` is false when the line comes from outside the "
    "frame (a tail leaving the panel, or an untailed line clearly spoken "
    "by someone not drawn). Narration, SFX, and signage take speaker "
    "null.\n\n"
    "DELIVERY\n"
    "8. `tone` must be one of the listed values - pick the closest. Put "
    "anything the list cannot carry in `tone_note` as free text, or null.\n"
    "9. `emphasis` describes the LETTERING's visual weight, not the "
    "emotion: 'bold', 'large', 'small', 'trembling' (wavy/shaky "
    "lettering), or 'normal'. This is used later to match the "
    "original's typography.\n"
    "10. `reading_index` is this node's 1-based position in the order a "
    "native reader of this panel's language would read it - "
    "right-to-left for Japanese manga, left-to-right otherwise.\n\n"
    "If you were given a list of detected text regions, reuse their "
    "`node_id` values verbatim so your reading can be matched to them "
    "exactly. Report a node with node_id null only for text you can see "
    "that the region list does not cover. If you were given no regions, "
    "set every node_id to null.\n\n"
    "Respond with ONLY a JSON object of this shape:\n" + _SCHEMA_DOC
)


def _clamp_confidence(value) -> float:
    """A confidence that isn't a number, or sits outside 0-1, is treated
    as no confidence rather than clamped optimistically - the whole point
    of the field is to be able to distrust an attribution, so a
    malformed one must not read as certain.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return 0.0
    # NaN and infinity must be caught BEFORE clamping. min/max comparisons
    # against NaN are all False, so max(0.0, min(1.0, nan)) silently
    # returns 1.0 - a malformed value arriving as MAXIMUM confidence,
    # which is precisely backwards for a field whose only job is to let
    # an attribution be distrusted.
    if not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _clean_str(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _parse_readings(data: dict) -> list[Reading]:
    """Turns the model's JSON into Readings, treating every field as
    untrusted.

    Values outside a bounded vocabulary are downgraded to that
    vocabulary's safe default rather than passed through, so downstream
    code that filters on `kind` or groups by `tone` can rely on the set
    of values actually being the set it was told about. A node with no
    usable text is dropped entirely - there is nothing to align, adapt,
    or typeset.
    """
    raw = data.get("text_nodes")
    if not isinstance(raw, list):
        return []

    readings: list[Reading] = []
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict):
            continue
        text = _clean_str(entry.get("text"))
        if not text:
            continue

        kind = entry.get("kind")
        if kind not in _VALID_KINDS:
            kind = "unknown"
        tone = entry.get("tone")
        if tone not in _VALID_TONES:
            tone = "neutral"
        emphasis = entry.get("emphasis")
        if emphasis not in _VALID_EMPHASIS:
            emphasis = "normal"

        speaker = _clean_str(entry.get("speaker"))
        confidence = _clamp_confidence(entry.get("speaker_confidence"))
        # An attribution with no stated confidence is not evidence of a
        # confident one. Dropping the speaker entirely here would throw
        # away a real signal, so it's kept at confidence 0 and left for
        # the caller to threshold.
        if speaker is None:
            confidence = 0.0

        reading_index = entry.get("reading_index")
        if not isinstance(reading_index, int) or isinstance(reading_index, bool):
            # Fall back to the order the model listed them in, which is
            # what it was asked to sort by anyway.
            reading_index = position

        readings.append(
            Reading(
                text=text,
                kind=kind,
                speaker=speaker,
                speaker_confidence=confidence,
                speaker_appearance=_clean_str(entry.get("speaker_appearance")),
                speaker_visible=entry.get("speaker_visible") is not False,
                tone=tone,
                tone_note=_clean_str(entry.get("tone_note")),
                emphasis=emphasis,
                reading_index=reading_index,
                node_id=_clean_str(entry.get("node_id")),
            )
        )
    return readings


def _known_regions_block(known_regions: list[dict] | None) -> str:
    """The optional grounding half of the user turn: the text regions a
    detector already found, each with an id for the model to key its
    reading against.

    Supplying this makes alignment exact (match on node_id) instead of
    probabilistic (match on text similarity), at the cost of having to
    wait for the detector first. See read_panel's docstring.
    """
    if not known_regions:
        return ""
    lines = [
        f"- {region['node_id']}: " + (region.get("text") or "(no OCR text)")
        for region in known_regions
    ]
    return (
        "\n\nA detector already found these text regions in this panel. "
        "Reuse their node_id values verbatim. Any OCR text shown is a "
        "rough, often-garbled read - correct it from the image, do not "
        "trust it:\n" + "\n".join(lines)
    )


def read_panel(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    known_regions: list[dict] | None = None,
) -> list[Reading]:
    """Asks a vision-capable model to read and direct this panel.

    `known_regions` is optional and decides which of two modes this runs
    in - a real architectural trade, not a tuning knob:

      - Omitted (cold read): this call depends on nothing, so it can be
        fired at the same instant as the OCR call and total latency is
        the slower of the two rather than their sum. The cost is that
        the model's text must afterwards be matched back onto the
        detector's boxes by similarity (engine/comics_align.py), which
        can fail to pair a badly-garbled bubble.
      - Supplied (grounded read): the model is handed the detected
        regions and keys its answer to their node_ids, so alignment is
        exact and the similarity matching becomes a fallback for nodes
        it didn't key. The cost is that this call can no longer start
        until the detector has finished.

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
            "Read and direct this panel." + _known_regions_block(known_regions),
            image_data_url=f"data:{mime_type};base64,{encoded}",
            max_tokens=_MAX_TOKENS,
            stage="comics_vision_read",
        )
    except Exception as exc:  # noqa: BLE001 - deliberately broad; see docstring
        logger.warning("Vision reading call failed, falling back to OCR only: %s", exc)
        return []

    return _parse_readings(data)
