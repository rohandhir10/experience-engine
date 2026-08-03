"""Urdu phrase-end phonetic coda — Perso-Arabic script.

Extends `engine/rhythm.py::phrase_end_sustainability` to Urdu targets,
but NOT via "read the last written letter and treat it as the answer" —
that fails, confidently and silently, on one of Urdu poetry's most
common constructions: izafat (اضافت), the Persian genitive that joins
two nouns/adjectives with an UNWRITTEN "-e-" vowel (dast-e-tanha,
shama-e-mehfil, kitab-e-zindagi). Any Perso-Arabic-origin noun can head
an izafat phrase, and real typed/pasted Urdu — including virtually all
song lyrics — almost never marks the izafat diacritic. So a word that
looks like it ends in a bare stop consonant ("closed") may, in the
construction it actually appears in, be sung with a trailing vowel
("sustainable") the bare script never shows. Reading the final letter's
shape alone cannot tell these two apart; that is exactly the "guessing
a missing short vowel" this module must avoid, not a smaller version of
it (see engine/grounding/urdu.py's syllable counter for the same
reasoning applied to counting).

The ambiguity only bites for STOP/AFFRICATE letters (`URDU_CLOSED_STOPS`)
— an unwritten trailing vowel would flip "closed" to "sustainable" for
those, so they decline unless a diacritic settles it. Every other
ending is safe to answer even without one: the unambiguous long-vowel/
nasal letters (`URDU_SUSTAINABLE_ENDINGS`) are already vowels, not
candidates for a hidden one after them (izafat after a vowel-final word
requires an extra WRITTEN hamza/ye, it is not silent); and any other
bare consonant (fricative, liquid, nasal letter) is "sustainable"
whether or not an unwritten vowel follows it, since both possible
readings agree. Only the stop/affricate case has two readings that
disagree, which is the one place this declines rather than guesses.
"""
from __future__ import annotations

_ARABIC_RANGE = (0x0600, 0x06FF)
_ARABIC_EXT_RANGE = (0x0750, 0x077F)

# Short vowel diacritics and nunation — an explicit, unambiguous vowel.
_FATHA = "َ"
_DAMMA = "ُ"
_KASRA = "ِ"
_SHORT_VOWELS = frozenset((_FATHA, _DAMMA, _KASRA))
_TANWIN = frozenset(("ً", "ٌ", "ٍ"))

_SUKUN = "ْ"    # explicit "no vowel here" — settles the letter it sits on
_SHADDA = "ّ"   # gemination marker, not a vowel itself

# Stop and affricate consonants: airflow closes abruptly, cannot be
# sustained. ط is phonetically the same stop as ت in Urdu (a spelling
# distinction inherited from Arabic orthography, not a sound
# distinction); ء (hamza) is a glottal stop, the same category.
URDU_CLOSED_STOPS = frozenset("تپٹکگدڈقبجچطء")

# Visible long vowels, gol/do-chashmi he, and noon ghunna (nasalization)
# — held open or nasal, never abruptly stopped, and not a site an
# unwritten izafat vowel could hide behind (see module docstring).
URDU_SUSTAINABLE_ENDINGS = frozenset("اویےہآں")

_PUNCT = ".,!?;:\"'()[]«»۔،؛؟!—-"


def _in_arabic_script(c: str) -> bool:
    cp = ord(c)
    return _ARABIC_RANGE[0] <= cp <= _ARABIC_RANGE[1] or _ARABIC_EXT_RANGE[0] <= cp <= _ARABIC_EXT_RANGE[1]


def _has_urdu_script(text: str) -> bool:
    return any(_in_arabic_script(c) for c in text)


def _strip_punctuation(word: str) -> str:
    return word.strip(_PUNCT)


def get_urdu_phrase_end_coda(word: str) -> dict | None:
    """{"coda_type": "sustainable"|"closed", "final_character": str} when
    the word's true ending is unambiguous from the visible script, else
    None. See module docstring for exactly which case declines and why.
    """
    if not _has_urdu_script(word):
        return None

    cleaned = _strip_punctuation(word.strip())
    if not cleaned:
        return None

    last = cleaned[-1]

    if last in _SHORT_VOWELS or last in _TANWIN:
        return {"coda_type": "sustainable", "final_character": last}

    if last == _SHADDA:
        # Gemination marker with nothing after it — malformed/ambiguous.
        return None

    if last == _SUKUN:
        if len(cleaned) < 2:
            return None
        coda_letter = cleaned[-2]
        coda_type = "closed" if coda_letter in URDU_CLOSED_STOPS else "sustainable"
        return {"coda_type": coda_type, "final_character": coda_letter}

    if last in URDU_SUSTAINABLE_ENDINGS:
        return {"coda_type": "sustainable", "final_character": last}

    if last in URDU_CLOSED_STOPS:
        # No diacritic to settle it: an unwritten trailing izafat or
        # inflectional vowel would make this word actually end open, not
        # closed. This is the one letter class where the two possible
        # readings disagree — decline rather than guess.
        return None

    # Any other bare consonant (fricative, liquid, nasal letter): both
    # possible readings — bare-consonant-final or vowel-final via an
    # unwritten ending — are "sustainable", so this is safe either way.
    return {"coda_type": "sustainable", "final_character": last}
