"""Aligns a vision-LLM's reading of a comic panel to Cloud Vision's
detected text regions.

Why this exists at all: the two systems are good at different halves of
the same job. Cloud Vision produces precise per-block pixel geometry but
reads stylized comic lettering badly and has no idea what it's looking at
(dialogue? a sound effect? a shop sign in the background?). A vision-
capable LLM reads stylized lettering far better and can classify and
attribute it, but is unreliable at exact pixel coordinates - which the
redraw/typeset path (engine/comics_redraw.py) genuinely depends on.

So each is asked only for what it's actually good at, and the two are run
CONCURRENTLY rather than in sequence - the LLM is not handed Vision's
boxes to correct one at a time, because that would make total latency the
sum of both calls instead of the slower of the two. The cost of that
choice is precisely this module: with no shared coordinate frame, the
LLM's text has to be matched back to Vision's boxes after the fact.

The matching is deterministic and pure (no model involved), which is the
point - it's the part that has to be right, so it's the part that can be
unit-tested. Vision's garbled read of a bubble is still usually similar
enough to the true text to match it confidently ("H0LD 0N TlGHT" against
"HOLD ON TIGHT"), and where it isn't, this module says so rather than
guessing: an unmatched region keeps Vision's own text and is flagged for
the human, exactly as an un-reviewed OCR draft already is.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

# Below this similarity, a Vision region and an LLM reading are not
# confidently the same piece of text, and pairing them would risk
# putting one bubble's dialogue in another bubble's box - a silent,
# invisible error far worse than simply keeping the OCR draft. Tuned to
# tolerate heavy character-level garbling while still refusing to match
# two genuinely different lines.
DEFAULT_MIN_SIMILARITY = 0.55

_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Casefolds and strips punctuation/whitespace for comparison only.

    Keeps every Unicode letter and number and drops everything else,
    rather than filtering by codepoint range. A range-based version of
    this kept all of U+0080 and up so non-Latin scripts would survive,
    but that also kept CJK and fullwidth punctuation - so a Japanese
    bubble read with and without its exclamation mark normalized to two
    different strings and scored as a weaker match than it deserved.
    Categories get both halves right: any script's letters are kept, any
    script's punctuation is not.
    """
    kept = [
        ch if unicodedata.category(ch)[0] in ("L", "N") else " "
        for ch in text.casefold()
    ]
    return _WHITESPACE_RE.sub(" ", "".join(kept)).strip()


def similarity(a: str, b: str) -> float:
    """0.0-1.0 similarity between two readings of (possibly) the same
    text. Both empty counts as no information, not a perfect match.
    """
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb, autojunk=False).ratio()


@dataclass
class Reading:
    """One text node the vision model reports seeing in the panel.

    Field names mirror the JSON schema in engine/comics_vision.py
    (_SCHEMA_DOC) one-for-one, so the prompt contract and this dataclass
    can be read side by side.
    """

    text: str
    # See comics_vision._VALID_KINDS. Finer-grained than a plain
    # dialogue/not-dialogue split because the distinctions are real
    # localization decisions, not decoration: a thought bubble is
    # typeset in a different face from speech, and signage often
    # shouldn't be touched at all.
    kind: str = "unknown"
    # PANEL-LOCAL label ("Character_A"), not a chapter-wide identity.
    # The model sees one panel and cannot know that its Character_A is
    # the Character_A of six panels ago; reconciling those into real
    # cast members is a separate step (see comics_vision's docstring).
    speaker: str | None = None
    # The model's own 0-1 confidence in that attribution. Carried so a
    # low-confidence guess can be shown differently from a bubble whose
    # tail plainly points at someone, instead of both arriving as bare
    # text that looks equally certain.
    speaker_confidence: float = 0.0
    # What the speaker physically looks like in this panel ("tall, dark
    # bob, red jacket"). This is the join key for cross-panel identity:
    # panel-local labels are meaningless across panels, appearance is not.
    speaker_appearance: str | None = None
    # False when the line is spoken from outside the frame (off-panel
    # tail, or none at all) - a real case where no visible figure can be
    # the speaker and guessing one would be wrong.
    speaker_visible: bool = True
    # Bounded vocabulary (comics_vision._VALID_TONES). Bounded on
    # purpose: free-text emotion can't be compared across panels, so it
    # could never drive consistency, only decorate a UI.
    tone: str = "neutral"
    # Free text for whatever the bounded tone can't carry. The escape
    # hatch that lets `tone` stay small enough to be useful.
    tone_note: str | None = None
    # Visual weight of the lettering ("normal" | "bold" | "large" |
    # "small" | "trembling"). Captured now because it is the input
    # typesetting needs later to match the original's emphasis, and it
    # is only recoverable while looking at the artwork.
    emphasis: str = "normal"
    # 1-based position in this panel's reading order, as the model reads
    # it. Genuinely useful because reading order is script-dependent
    # (right-to-left manga, Z-pattern spreads) and geometry alone
    # guesses it badly.
    reading_index: int = 0
    # The detector's node id when the model was given one to key against
    # (see comics_vision.read_panel's `known_regions`). None when the
    # model read the panel cold, in which case alignment falls back to
    # matching on text similarity.
    node_id: str | None = None


@dataclass
class AlignedRegion:
    """One Cloud Vision region, after (possibly) being matched to a
    vision-LLM reading of the same text.
    """

    index: int
    text: str
    # "llm" when the LLM's reading was confidently matched and used;
    # "vision" when it wasn't and Cloud Vision's own text was kept.
    source: str
    similarity: float
    kind: str = "unknown"
    speaker: str | None = None


@dataclass
class AlignmentResult:
    regions: list[AlignedRegion] = field(default_factory=list)
    # Readings the LLM reported that no Vision region matched. These have
    # no bounding box, so they cannot be placed on the panel or redrawn -
    # surfaced rather than dropped, since they usually mean Cloud Vision
    # missed a bubble entirely.
    unplaced: list[Reading] = field(default_factory=list)

    @property
    def corrected_count(self) -> int:
        return sum(1 for r in self.regions if r.source == "llm")


def align_readings(
    vision_texts: list[str],
    readings: list[Reading],
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> AlignmentResult:
    """Matches each LLM reading to at most one Vision region, and vice
    versa, by descending similarity.

    Greedy-by-best-score rather than positional (nth reading -> nth
    region): reading order in comics is genuinely not a solved problem -
    manga runs right-to-left, and a panel's bubbles can be laid out in a
    Z-pattern - so pairing by position would be wrong exactly where this
    feature matters most. Matching on the text itself sidesteps ordering
    entirely.

    Greedy rather than globally optimal (Hungarian): with the handful of
    bubbles a single panel holds, the two agree in practice, and greedy
    stays readable and obviously correct. Ties are broken by region
    order so the result is deterministic for identical input.
    """
    scored: list[tuple[float, int, int]] = []
    for region_index, vision_text in enumerate(vision_texts):
        for reading_index, reading in enumerate(readings):
            score = similarity(vision_text, reading.text)
            if score >= min_similarity:
                scored.append((score, region_index, reading_index))

    # Highest score first; region then reading index as tie-breakers so
    # equal scores resolve the same way on every run.
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))

    region_to_reading: dict[int, tuple[int, float]] = {}
    used_readings: set[int] = set()
    for score, region_index, reading_index in scored:
        if region_index in region_to_reading or reading_index in used_readings:
            continue
        region_to_reading[region_index] = (reading_index, score)
        used_readings.add(reading_index)

    regions: list[AlignedRegion] = []
    for region_index, vision_text in enumerate(vision_texts):
        match = region_to_reading.get(region_index)
        if match is None:
            # No confident counterpart: keep what OCR actually saw. This
            # is the honest fallback - the human is reviewing this draft
            # either way.
            regions.append(
                AlignedRegion(
                    index=region_index, text=vision_text, source="vision", similarity=0.0
                )
            )
            continue
        reading_index, score = match
        reading = readings[reading_index]
        regions.append(
            AlignedRegion(
                index=region_index,
                text=reading.text,
                source="llm",
                similarity=round(score, 3),
                kind=reading.kind,
                speaker=reading.speaker,
            )
        )

    unplaced = [r for i, r in enumerate(readings) if i not in used_readings]
    return AlignmentResult(regions=regions, unplaced=unplaced)
