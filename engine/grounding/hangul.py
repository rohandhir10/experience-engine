"""Korean syllable counting.

The easiest non-Latin grounding by a wide margin: a Hangul syllable block
is one syllable by construction. U+AC00–U+D7A3 covers all 11,172
precomposed blocks, so counting them counts syllables exactly — no
dictionary, no heuristic, no ambiguity.

Two real cases are handled rather than ignored:
  - Jamo written separately (U+1100–U+11FF, U+3130–U+318F) instead of
    composed into blocks. NFC normalization composes them first.
  - Latin/digit content mixed into Korean lyrics, which is extremely
    common in K-pop. Those runs are counted with the English syllable
    counter rather than dropped, since they are sung too.
"""
from __future__ import annotations

import re
import unicodedata

from .base import GroundingResult, register_counter

_HANGUL_SYLLABLES = (0xAC00, 0xD7A3)
_LATIN_RUN_RE = re.compile(r"[A-Za-z][A-Za-z']*")


def _is_hangul_block(char: str) -> bool:
    return _HANGUL_SYLLABLES[0] <= ord(char) <= _HANGUL_SYLLABLES[1]


def count_korean(text: str) -> GroundingResult | None:
    # Compose any separately-written jamo into syllable blocks first.
    normalized = unicodedata.normalize("NFC", text)
    blocks = sum(1 for c in normalized if _is_hangul_block(c))

    if blocks == 0:
        return None  # nothing Korean here — let another counter handle it

    # Mixed-script lyrics are the norm in Korean pop; count the sung
    # Latin words too rather than silently undercounting the line.
    from ..rhythm import count_syllables_word

    latin = sum(count_syllables_word(w) for w in _LATIN_RUN_RE.findall(normalized))

    caveat = (
        f"includes {latin} syllable(s) from Latin-script words"
        if latin
        else None
    )
    return GroundingResult(
        value=blocks + latin,
        unit="syllables",
        language="Korean",
        caveat=caveat,
    )


register_counter("ko", count_korean)
