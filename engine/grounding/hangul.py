"""Korean syllable counting.

The most exact grounding of any language here: a Hangul syllable block is
one syllable by construction, and U+AC00–U+D7A3 covers all 11,172
precomposed blocks. No dictionary, no heuristic, no ambiguity — unlike
Hindi (schwa deletion is irregular), Spanish (synalepha), or Japanese
(kanji readings must be inferred).

That exactness only holds if everything sung is actually counted, so
three things that appear constantly in Korean lyrics are handled rather
than skipped:

  - **Latin words.** K-pop mixes English continuously; dropping it
    undercounts most choruses.
  - **Digits.** "24시간" is sung 이-십-사-시-간 — five syllables, not the
    two you get by counting only the Hangul. Numbers are read aloud, so
    they are counted aloud.
  - **Hanja.** Rare in modern lyrics but present in older and lyrical
    registers; each Hanja character is one Korean syllable when read.

Anything left uncounted would be a silent undercount that still looks
exact, which is worse than declining — the same standard the Japanese
counter applies to kanji.
"""
from __future__ import annotations

import re
import unicodedata

from .base import GroundingResult, register_counter

_HANGUL_SYLLABLES = (0xAC00, 0xD7A3)
_HANJA = (0x4E00, 0x9FFF)
_LATIN_RUN_RE = re.compile(r"[A-Za-z][A-Za-z']*")
_DIGIT_RUN_RE = re.compile(r"\d+")

# Sino-Korean numerals, one syllable each: 일 이 삼 사 오 육 칠 팔 구.
# Place markers 십/백/천/만 are likewise one syllable each.
_PLACE_VALUES = ((10000, "만"), (1000, "천"), (100, "백"), (10, "십"))


def _is_hangul_block(char: str) -> bool:
    return _HANGUL_SYLLABLES[0] <= ord(char) <= _HANGUL_SYLLABLES[1]


def _is_hanja(char: str) -> bool:
    return _HANJA[0] <= ord(char) <= _HANJA[1]


def sino_korean_syllables(number: int) -> int:
    """Syllables when a number is read aloud in Sino-Korean.

    24 -> 이십사 (3). 10 -> 십 (1), not 일십. 2024 -> 이천이십사 (5).

    Korean has two numeral systems and the choice depends on the counter
    that follows (Sino with 시간/분/년, native with 개/명/살). Sino-Korean
    is used here because it covers most numeric expressions in lyrics;
    the caveat on the result says so rather than hiding the ambiguity.
    """
    if number == 0:
        return 1  # 영
    syllables = 0
    remaining = number
    for value, _marker in _PLACE_VALUES:
        if remaining >= value:
            count = remaining // value
            # 십 not 일십: a leading 1 in a place is dropped.
            if count > 1:
                syllables += sino_korean_syllables(count)
            syllables += 1  # the place marker itself
            remaining %= value
    if remaining:
        syllables += 1  # the ones digit, one syllable
    return syllables


def count_korean(text: str) -> GroundingResult | None:
    # Compose any separately-written jamo into syllable blocks first.
    normalized = unicodedata.normalize("NFC", text)
    blocks = sum(1 for c in normalized if _is_hangul_block(c))

    if blocks == 0:
        return None  # nothing Korean here — let another counter handle it

    from ..rhythm import count_syllables_word

    extras: list[str] = []

    latin = sum(count_syllables_word(w) for w in _LATIN_RUN_RE.findall(normalized))
    if latin:
        extras.append(f"{latin} from Latin-script words")

    digits = sum(
        sino_korean_syllables(int(run)) for run in _DIGIT_RUN_RE.findall(normalized)
    )
    if digits:
        extras.append(f"{digits} from digits read as Sino-Korean numerals")

    hanja = sum(1 for c in normalized if _is_hanja(c))
    if hanja:
        extras.append(f"{hanja} from Hanja (one syllable each)")

    caveat = ("includes " + ", ".join(extras)) if extras else None
    if digits:
        caveat += (
            "; Korean has two numeral systems and the counter word decides "
            "which is used, so a digit read natively (하나/둘) instead would "
            "differ"
        )

    return GroundingResult(
        value=blocks + latin + digits + hanja,
        unit="syllables",
        language="Korean",
        caveat=caveat,
    )


register_counter("ko", count_korean)
