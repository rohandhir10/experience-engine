"""Deterministic detection of source-side formal recurrence — a phrase or
refrain repeated verbatim across sections (a ghazal's radif, a chorus hook)
that Song DNA's single interpretive LLM pass may fail to notice and tag as
a motif. Detection here is exact string matching over normalized source
text; it makes no claim about whether any target-language rendering is
correct, only that a recurring source-side element exists and therefore
needs deliberate, consistent handling.

This exists because Song DNA's motif list, and every consistency check
downstream of it (Law 5 Ambiguity Lock, cultural-anchor consistency,
compensation consistency), only fires on an item that was voluntarily
reported. None has independent detection — a recurring element the DNA
call never tagged is invisible to all three. A ghazal's radif is exactly
this case: a formally required repetition that a single LLM pass over the
whole song can simply fail to notice.

Note what this module does NOT try to check: whether the recurring
element's target-language rendering is WORDED identically every time. For
a named cultural term that is the right bar (Law 5). For a structural
device like a radif it is the wrong one — CASTIA is an adaptation engine,
not a translator, and the whole point is that "kya hai" earns a
differently-worded English line each time. What must stay consistent is
the STRUCTURAL FUNCTION (each line closes on the same kind of question),
not the wording. See verify.py's `_check_structural_recurrence` for that
narrower, syntactic check.

Also lives here: `detect_section_repeats`, whole-SECTION recurrence — a
chorus (or any block) that reappears later in the song either verbatim
(`SectionInput.repeats`) or with a small number of lines changed
(`SectionInput.varies_from`, e.g. a final chorus with one "lifted" line).
This is a different question from the suffix-matching above (a single
recurring trailing phrase within otherwise-distinct sections) — this
detects two sections that are substantially the SAME section. Both are
"exact string matching over normalized source text" in the same sense:
no interpretation, no LLM call, just a deterministic comparison the real
ingestion path (engine/text_ingest.py) runs on every submitted song so a
verbatim or near-verbatim repeated chorus doesn't silently get re-judged
from scratch (and risk coming out worded differently) each time it
recurs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_WORD_RE = re.compile(r"\S+")

# A recurring ending must show up in at least this many sections before
# it's treated as a formal device rather than coincidence — two sections
# sharing a short trailing phrase is common and means nothing on its own.
MIN_SECTIONS_FOR_RECURRENCE = 3

# Below this many shared trailing words, a match is likely a common
# function-word tail ("...to you", "...like this") rather than a
# deliberate refrain. Conservative on purpose: a false negative here just
# means a section relies solely on Song DNA's own read of the song, which
# is the status quo; a false positive manufactures a requirement the song
# never had, which is the worse failure of the two.
MIN_SUFFIX_WORDS = 2


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _last_line(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


@dataclass
class RecurringEnding:
    shared_suffix: str
    sections: list[str] = field(default_factory=list)


def detect_recurring_endings(
    sections: list[tuple[str, str]],
) -> list[RecurringEnding]:
    """`sections` is (section_name, source_text) pairs, in song order.

    Finds the longest word-level suffix shared verbatim by the LAST LINE
    of at least MIN_SECTIONS_FOR_RECURRENCE sections. A radif is exactly
    this: the same trailing phrase closing every couplet's final line.
    Returns at most one match — the longest, most section-covering one —
    since a song built around two independent formal refrains at once is
    rare enough not to be worth the added complexity here.
    """
    endings: list[tuple[str, list[str]]] = []
    for name, text in sections:
        words = _WORD_RE.findall(_normalize(_last_line(text)))
        if words:
            endings.append((name, words))

    if len(endings) < MIN_SECTIONS_FOR_RECURRENCE:
        return []

    max_len = min(len(words) for _, words in endings)
    for suffix_len in range(max_len, MIN_SUFFIX_WORDS - 1, -1):
        groups: dict[tuple[str, ...], list[str]] = {}
        for name, words in endings:
            suffix = tuple(w.lower() for w in words[-suffix_len:])
            groups.setdefault(suffix, []).append(name)
        best_suffix, best_names = max(groups.items(), key=lambda kv: len(kv[1]))
        if len(best_names) >= MIN_SECTIONS_FOR_RECURRENCE:
            return [RecurringEnding(shared_suffix=" ".join(best_suffix), sections=best_names)]
    return []


# A variant match (same line count, some lines changed) needs at least
# this many lines before it counts as a real chorus-with-variation rather
# than a coincidence — a 1-2 line section matching another 1-2 line
# section by line count is common and not meaningful on its own (same
# spirit as MIN_SECTIONS_FOR_RECURRENCE/MIN_SUFFIX_WORDS above).
MIN_LINES_FOR_VARIANT_MATCH = 3


def _normalized_lines(text: str) -> list[str]:
    return [_normalize(line) for line in text.splitlines() if line.strip()]


def diff_line_indices(a_text: str, b_text: str) -> list[int] | None:
    """0-based indices where `b_text`'s non-empty lines differ from
    `a_text`'s, comparing position-wise after whitespace normalization.
    None if the two don't have the same non-empty line count — nothing
    meaningful to align in that case (a genuinely different section, not
    a same-shape variant)."""
    a_lines = _normalized_lines(a_text)
    b_lines = _normalized_lines(b_text)
    if len(a_lines) != len(b_lines):
        return None
    return [i for i, (a, b) in enumerate(zip(a_lines, b_lines)) if a != b]


@dataclass
class SectionRepeat:
    kind: str  # "exact" | "variant"
    repeats_from: str
    # 0-based line indices that changed — always empty for "exact",
    # always non-empty for "variant".
    changed_line_indices: list[int] = field(default_factory=list)


def detect_section_repeats(sections: list[tuple[str, str]]) -> dict[str, SectionRepeat]:
    """`sections` is (section_name, source_text) pairs, in song order.

    For each section, checks every EARLIER section for a whole-section
    match: identical (normalized) lines is "exact"; same line count with
    a minority of lines differing is "variant". When a section matches
    more than one earlier candidate, an exact match always wins over a
    variant one (it's strictly cheaper and cleaner to reuse outright);
    among variant candidates, the one with the fewest changed lines wins,
    tie-broken by whichever occurs earliest in the song.

    Conservative on purpose, same reasoning as detect_recurring_endings
    above: a false negative here just means a section is treated as
    ordinary (today's status quo, and still correct — just not free);
    a false positive would tell the room to copy an earlier ruling's
    wording onto a section that was never actually meant to match it.
    """
    results: dict[str, SectionRepeat] = {}
    seen: list[tuple[str, str]] = []
    for name, text in sections:
        lines = _normalized_lines(text)
        exact_match: str | None = None
        best_variant: tuple[str, list[int]] | None = None
        if lines:
            for earlier_name, earlier_text in seen:
                diff = diff_line_indices(earlier_text, text)
                if diff is None:
                    continue
                if not diff:
                    exact_match = earlier_name
                    break
                if len(lines) >= MIN_LINES_FOR_VARIANT_MATCH and len(diff) <= len(lines) // 2:
                    if best_variant is None or len(diff) < len(best_variant[1]):
                        best_variant = (earlier_name, diff)
        if exact_match is not None:
            results[name] = SectionRepeat(kind="exact", repeats_from=exact_match)
        elif best_variant is not None:
            results[name] = SectionRepeat(
                kind="variant", repeats_from=best_variant[0], changed_line_indices=best_variant[1]
            )
        seen.append((name, text))
    return results
