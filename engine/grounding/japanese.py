"""Japanese mora counting.

Japanese does NOT count syllables. It counts **morae** — timing units —
and the difference is not academic: きょう ("today") is 3 characters but
2 morae, and 東京 (Tokyo) is 4 morae (to-u-kyo-u), not the 2 syllables an
English speaker hears. Every traditional Japanese form is built on mora
counts (haiku 5-7-5, tanka 5-7-5-7-7), and J-pop lines are written to
mora counts against a melody. Applying the English syllable counter here
would produce a number that is simply about the wrong thing.

The rules, which are fully deterministic once you have kana:
  - each kana is one mora
  - EXCEPT small ゃゅょ / ぁぃぅぇぉ (yōon), which fuse with the kana
    before them and add nothing
  - ん (moraic nasal), っ (sokuon, the geminating pause), and ー (chōonpu,
    the long-vowel mark) each count as a FULL mora on their own, which is
    the rule non-speakers most often miss

The real obstacle is kanji, which carry no reading on their face — 今日
could be きょう or こんにち. Real lyrics are 30-50% kanji, so a kana-only
counter would silently undercount most lines by half.

This module therefore uses SudachiPy (an optional dependency) to get
readings, giving exact counts on ordinary mixed script. Without it, kana
is still counted exactly, but text containing kanji returns None rather
than a number that looks authoritative and is wrong by half — the same
discipline every other counter here follows.
"""
from __future__ import annotations

import functools
import re

from .base import GroundingResult, register_counter

# Small kana fuse with the preceding mora and add nothing of their own.
_SMALL_KANA = set("ゃゅょぁぃぅぇぉゎャュョァィゥェォヮ")
# These look like modifiers but are each a full mora in their own right.
_FULL_MORA_MARKS = set("んンっッー")

_HIRAGANA = (0x3041, 0x309F)
_KATAKANA = (0x30A0, 0x30FF)
_KANJI = (0x4E00, 0x9FFF)

_JAPANESE_PUNCT = "、。！？「」『』・…〜　"


def _in(char: str, rng: tuple[int, int]) -> bool:
    return rng[0] <= ord(char) <= rng[1]


def _is_kana(char: str) -> bool:
    return _in(char, _HIRAGANA) or _in(char, _KATAKANA)


def _is_kanji(char: str) -> bool:
    return _in(char, _KANJI)


def count_morae_in_kana(text: str) -> int:
    """Exact mora count for pure-kana text.

    Every kana counts once; small kana fuse with what precedes them.
    ん/っ/ー are already covered by "every kana counts once" — they are
    listed in _FULL_MORA_MARKS for documentation, since assuming they are
    modifiers rather than morae is the classic error.
    """
    return sum(
        1 for c in text if _is_kana(c) and c not in _SMALL_KANA and c != "ー"
    ) + sum(1 for c in text if c == "ー")


@functools.lru_cache(maxsize=1)
def _tokenizer():
    """SudachiPy is optional; absence degrades honestly rather than crashing."""
    try:
        from sudachipy import Dictionary

        return Dictionary().create()
    except Exception:  # noqa: BLE001 — missing dict/package are both "no reader"
        return None


def _readings(text: str) -> str | None:
    """Katakana readings for mixed script, or None without a tokenizer."""
    tokenizer = _tokenizer()
    if tokenizer is None:
        return None
    try:
        return "".join(m.reading_form() for m in tokenizer.tokenize(text))
    except Exception:  # noqa: BLE001
        return None


def count_japanese(text: str) -> GroundingResult | None:
    stripped = "".join(c for c in text if c not in _JAPANESE_PUNCT and not c.isspace())
    if not stripped:
        return None
    if not any(_is_kana(c) or _is_kanji(c) for c in stripped):
        return None  # not Japanese

    has_kanji = any(_is_kanji(c) for c in stripped)

    if has_kanji:
        reading = _readings(text)
        if reading is None:
            # Counting only the kana of a kanji-heavy line would report
            # roughly half the true value while looking exact. None is
            # the honest answer.
            return None
        return GroundingResult(
            value=count_morae_in_kana(reading),
            unit="morae",
            language="Japanese",
            caveat=(
                "morae, not syllables — the unit Japanese verse is actually "
                "built on; kanji readings resolved by morphological analysis, "
                "which can pick the wrong reading for names and rare words"
            ),
        )

    return GroundingResult(
        value=count_morae_in_kana(stripped),
        unit="morae",
        language="Japanese",
        caveat="morae, not syllables — the unit Japanese verse is actually built on",
    )


register_counter("ja", count_japanese)
