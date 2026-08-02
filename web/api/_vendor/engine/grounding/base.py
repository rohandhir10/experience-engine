"""The grounding registry and result type."""
from __future__ import annotations

from typing import Callable

from pydantic import BaseModel


class GroundingResult(BaseModel):
    """A deterministic count of the source text's rhythmic units.

    `unit` is load-bearing, not decoration: 12 morae and 12 syllables are
    different quantities, and the Judge must be told which it received so
    it does not silently compare one against an English syllable count as
    though they were commensurable.
    """

    value: int
    unit: str  # "syllables" | "morae" | "hangul-blocks" | ...
    language: str
    # Set when the count is reliable but approximate for a stated reason
    # (e.g. Hindi schwa deletion is rule-governed but not perfect).
    caveat: str | None = None

    def for_prompt(self) -> str:
        base = f"{self.value} {self.unit} ({self.language})"
        return f"{base} — {self.caveat}" if self.caveat else base


# language code -> counter. A counter returns None whenever it cannot
# honestly count the text it was given.
Counter = Callable[[str], GroundingResult | None]

_COUNTERS: dict[str, Counter] = {}


def register_counter(language_code: str, counter: Counter) -> None:
    _COUNTERS[language_code.lower()] = counter


def count_source_units(text: str, language_code: str | None) -> GroundingResult | None:
    """Counts the source text's rhythmic units, or returns None when no
    counter exists for the language or the counter declines to guess.
    """
    if not language_code:
        return None
    counter = _COUNTERS.get(language_code.lower())
    if counter is None:
        return None
    return counter(text)


def supported_languages() -> list[str]:
    return sorted(_COUNTERS)
