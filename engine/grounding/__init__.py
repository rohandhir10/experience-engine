"""Per-language deterministic grounding for source text.

`engine/rhythm.py` grounds the TARGET side (English syllables, CMUdict).
This package grounds the SOURCE side, where the correct unit is not
always "syllable" — Japanese counts morae, Korean counts Hangul blocks,
Arabic classical verse is quantitative meter rather than syllable count
at all (docs/MULTILINGUAL_V2.md §5).

Two rules hold everywhere:

1. **Never fabricate.** A counter that cannot honestly count returns
   None. `rhythm.source_syllable_estimate` has always done this for
   non-Latin scripts; every counter here inherits that discipline.
2. **Always label the unit.** Morae and syllables are not the same
   quantity, and handing the Judge a bare integer invites it to compare
   them as if they were. Every result carries its unit name.
"""
from __future__ import annotations

from .base import GroundingResult, count_source_units, register_counter

# Importing a counter module is what registers it. These imports are the
# registration, not a convenience — without them count_source_units()
# silently returns None for every language, which looks exactly like
# "unsupported" and would hide the failure.
from . import devanagari as _devanagari  # noqa: F401,E402
from . import hangul as _hangul  # noqa: F401,E402
from . import japanese as _japanese  # noqa: F401,E402
from . import spanish as _spanish  # noqa: F401,E402
from . import urdu as _urdu  # noqa: F401,E402

__all__ = ["GroundingResult", "count_source_units", "register_counter"]
