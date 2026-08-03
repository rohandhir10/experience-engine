"""Deterministic Hindi (Devanagari) schwa-deletion heuristic.

Hindi consonants carry an inherent, unwritten vowel /ə/ (schwa) unless a
dependent vowel sign (matra) replaces it or a virama (halant) explicitly
kills it. Whether that inherent schwa is actually PRONOUNCED is not
recoverable from spelling alone without a rule — कमल is written
"ka-ma-la" (3 written units) but spoken "kamal" (2 syllables): only the
final schwa deletes, the other two survive. This is the well-known
schwa-deletion problem in Hindi computational phonology (Ohala 1983 and
much subsequent work).

The heuristic implemented here (validated against कमल "kamal", करवट
"karvaṭ", नमक "namak", and एक "ek" - all independently well-known,
correctly-pronounced words, worked through by hand and then checked
against this exact algorithm before trusting it):

1. Terminal deletion: a word-final consonant's inherent schwa deletes if
   the word has 2+ syllables (units). Essentially undisputed in the
   literature.
2. Medial deletion: for a consonant that isn't first or last, count its
   position from the END of the word (the terminal, already-deleted
   consonant is position 1). Odd positions delete, even positions
   retain. This is the standard simplification of Ohala's VC_CV
   environment rule.
3. Word-initial protection: the very first consonant's schwa is never
   deleted by rule 2, regardless of what parity would otherwise say -
   a commonly-cited exception, and necessary to get कमल right (क is at
   an odd position counting from the end in a 3-unit word, but is never
   deleted in real speech).
4. Conjuncts (virama-joined consonant clusters) are never split apart
   for this analysis - a whole cluster shares one syllable position,
   consistent with the exemption that a schwa is never deleted mid-
   conjunct (there's no schwa there to begin with; virama already marks
   it absent).

This is a heuristic approximation, not a definitive solution - real
Hindi has known exceptions this doesn't model (Sanskrit tatsama words
that resist deletion, certain compounds and suffix boundaries, loanwords,
proper-noun idiosyncrasies). It is expected to be right on ordinary,
synchronically-transparent words and wrong on some edge cases, the same
disclosed-limits standard as this codebase's other heuristics (e.g.
engine/rhythm.py's Latin vowel-cluster fallback).

A real bug surfaced while testing this against इश्क़ ("ishq," love): the
8 nukta consonants (क़ ख़ ग़ ज़ ड़ ढ़ फ़ य़) have precomposed Unicode
codepoints, but Unicode's own normalization rules put them on the
"composition exclusion" list - NFC/NFD both DECOMPOSE them into base
consonant + combining nukta sign (U+093C), never recompose them. Code
that expects the precomposed singleton codepoint will never actually see
it in normalized text. This module works entirely in the decomposed
form instead, and normalizes incoming text to make sure of it.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# --- Devanagari character classification -----------------------------------

_NUKTA_SIGN = "़"

_INDEPENDENT_VOWELS = set("अआइईउऊऋॠऌॡऍऎएऐऑऒओऔ")
_BASE_CONSONANTS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलळवशषसह")
_MATRAS = set("ािीुूृॄॅॆेैॉॊोौ")
_VIRAMA = "्"
_ANUSVARA = "ं"
_CHANDRABINDU = "ँ"
_VISARGA = "ः"
_NASAL_MARKS = {_ANUSVARA, _CHANDRABINDU}

# Manner of articulation -> can the sound be sustained/sung, or does it
# choke off like a Latin stop consonant (engine/rhythm.py's Latin-script
# rule)? Stops and flaps are momentary releases, physically impossible to
# hold; nasals, liquids/glides, and fricatives can all be held to some
# degree, same distinction rhythm.py already draws for Latin script.
_STOPS_AND_FLAPS = set("कखगघचछजझटठडढतथदधपफबभ")
_NASALS = set("ङञणनम")
_LIQUIDS_GLIDES = set("यरलळ")
_FRICATIVES = set("शषसह")

# Nukta consonants (base+U+093C, always decomposed - see module docstring)
# by manner: क़(qa) is a stop; ड़ढ़ are flaps (also can't be sustained);
# ख़ग़ज़फ़ are fricatives; य़ (rare) is glide-like.
_NUKTA_STOPS_AND_FLAPS = {"क" + _NUKTA_SIGN, "ड" + _NUKTA_SIGN, "ढ" + _NUKTA_SIGN}
_NUKTA_FRICATIVES = {"ख" + _NUKTA_SIGN, "ग" + _NUKTA_SIGN, "ज" + _NUKTA_SIGN, "फ" + _NUKTA_SIGN}
_NUKTA_LIQUIDS_GLIDES = {"य" + _NUKTA_SIGN}


def is_devanagari(text: str) -> bool:
    """True when the majority of a text's letters fall in the Devanagari
    Unicode block - the same "is this even the right script" gate
    engine/rhythm.py's is_latin_script provides for Latin text."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    devanagari = sum(1 for c in letters if "ऀ" <= c <= "ॿ")
    return (devanagari / len(letters)) > 0.8


def _read_consonant(word: str, i: int) -> tuple[str, int]:
    """Reads one consonant at position i, absorbing an immediately
    following nukta sign into its identity (so क+़ is treated as the
    single consonant क़ for classification, not as क followed by a
    dangling combining mark). Returns (identity, next_index).
    """
    identity = word[i]
    i += 1
    if i < len(word) and word[i] == _NUKTA_SIGN:
        identity += _NUKTA_SIGN
        i += 1
    return identity, i


@dataclass
class _Akshara:
    """One orthographic syllable unit: the (possibly clustered) consonant
    it ends on, and whether its vowel is explicit (a matra), inherent
    (schwa, eligible for deletion), or absent (word-initial vowel letter
    has no consonant at all)."""

    ending_consonant: str | None  # None for a vowel-only akshara
    is_schwa: bool  # True only for a bare consonant with no matra/virama


def _split_aksharas(word: str) -> list[_Akshara]:
    """Segments a Devanagari word into syllable units. A run of virama-
    joined consonants (a conjunct) collapses into one unit ending on the
    last (vowel-bearing) consonant - the earlier consonants in the
    cluster never carried a schwa to begin with, so they're never
    independent deletion candidates (rule 4 in the module docstring)."""
    aksharas: list[_Akshara] = []
    i = 0
    n = len(word)
    while i < n:
        ch = word[i]
        if ch in _INDEPENDENT_VOWELS:
            i += 1
            if i < n and word[i] in _NASAL_MARKS | {_VISARGA}:
                i += 1
            aksharas.append(_Akshara(ending_consonant=None, is_schwa=False))
            continue
        if ch in _BASE_CONSONANTS:
            last_consonant, i = _read_consonant(word, i)
            # Consume a chain of virama-joined consonants: each is "dead"
            # (no vowel at all) and just extends the cluster's onset.
            while i < n and word[i] == _VIRAMA and i + 1 < n and word[i + 1] in _BASE_CONSONANTS:
                last_consonant, i = _read_consonant(word, i + 1)
            # A trailing bare virama (word-final dead consonant, rare -
            # some Sanskrit-derived spellings) means no vowel at all.
            if i < n and word[i] == _VIRAMA:
                i += 1
                aksharas.append(_Akshara(ending_consonant=last_consonant, is_schwa=False))
                continue
            if i < n and word[i] in _MATRAS:
                i += 1
                if i < n and word[i] in _NASAL_MARKS | {_VISARGA}:
                    i += 1
                aksharas.append(_Akshara(ending_consonant=last_consonant, is_schwa=False))
                continue
            # Bare consonant, no matra, no virama -> inherent schwa.
            if i < n and word[i] in _NASAL_MARKS | {_VISARGA}:
                i += 1
            aksharas.append(_Akshara(ending_consonant=last_consonant, is_schwa=True))
            continue
        # A stray nukta sign (not consumed by _read_consonant because it
        # didn't immediately follow a consonant), or anything else not
        # part of an akshara nucleus - skip rather than guess at its role.
        i += 1
    return aksharas


def _resolve_deletions(aksharas: list[_Akshara]) -> list[bool]:
    """Returns, per akshara, whether its schwa is deleted. Only
    is_schwa=True units are ever eligible; explicit-vowel and vowel-only
    units are never touched."""
    n = len(aksharas)
    deleted = [False] * n
    if n == 0:
        return deleted
    if n >= 2 and aksharas[-1].is_schwa:
        deleted[-1] = True  # terminal deletion
    for i in range(n - 2, -1, -1):
        if i == 0:
            continue  # word-initial schwa is never deleted
        if not aksharas[i].is_schwa:
            continue
        position_from_end = n - i
        if position_from_end % 2 == 1:
            deleted[i] = True
    return deleted


def _manner_is_sustainable(consonant: str) -> bool:
    if len(consonant) == 2:  # nukta consonant (base + U+093C)
        if consonant in _NUKTA_STOPS_AND_FLAPS:
            return False
        return consonant in _NUKTA_FRICATIVES or consonant in _NUKTA_LIQUIDS_GLIDES
    if consonant in _STOPS_AND_FLAPS:
        return False
    if consonant in _NASALS or consonant in _LIQUIDS_GLIDES or consonant in _FRICATIVES:
        return True
    # An unrecognized consonant (shouldn't happen given the tables above
    # cover the full modern Devanagari consonant inventory) - default to
    # the more conservative "closed" rather than assume it's singable.
    return False


def get_hindi_phonetic_coda(word: str) -> dict | None:
    """Returns {"coda_type": "sustainable"|"closed", "final_sound": str,
    "syllable_count": int} for a single Devanagari word, or None if the
    word isn't recognizably Devanagari (wrong script entirely) or has no
    parseable aksharas (empty/punctuation-only input).
    """
    # Normalize first: a nukta consonant can arrive as either the
    # precomposed singleton or base+combining-nukta, and per the module
    # docstring, Unicode normalization always yields the decomposed form
    # for these - so normalizing guarantees the shape _read_consonant
    # expects, regardless of how the input text happened to be encoded.
    word = unicodedata.normalize("NFC", word)
    if not is_devanagari(word):
        return None
    aksharas = _split_aksharas(word)
    if not aksharas:
        return None

    deleted = _resolve_deletions(aksharas)
    syllable_count = sum(1 for d in deleted if not d)

    last = aksharas[-1]
    last_deleted = deleted[-1]

    if last.ending_consonant is None:
        # Vowel-only final akshara - always an open ending.
        return {"coda_type": "sustainable", "final_sound": "vowel", "syllable_count": syllable_count}

    if last_deleted:
        # Schwa deleted (or, for a virama-final word, never present) -
        # the audible ending is the bare final consonant's own sound.
        sustainable = _manner_is_sustainable(last.ending_consonant)
        return {
            "coda_type": "sustainable" if sustainable else "closed",
            "final_sound": last.ending_consonant,
            "syllable_count": syllable_count,
        }

    # Schwa (or an explicit matra) survived - the word ends on a vowel.
    return {"coda_type": "sustainable", "final_sound": "vowel", "syllable_count": syllable_count}
