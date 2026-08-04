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
