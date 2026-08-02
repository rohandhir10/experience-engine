"""Hindi/Punjabi syllable counting for Devanagari.

The production language has had no source grounding at all until now —
`rhythm.source_syllable_estimate` returns None for any non-Latin script,
so every Hindi run so far has judged singability against nothing on the
source side.

Devanagari is an abugida: a consonant carries an inherent /ə/ (schwa)
unless something removes it. Counting syllables is therefore counting
vowels, where a vowel is:

  - an independent vowel letter (अ आ इ ई उ ऊ ए ऐ ओ औ ऋ)
  - a dependent vowel sign (matra) on a consonant (ा ि ी ु ू े ै ो ौ ृ)
  - a consonant's *inherent* schwa, when it is neither replaced by a
    matra, nor killed by virama (्), nor deleted by the schwa-deletion
    rule below

**Schwa deletion** is the part a naive counter gets wrong, and it is not
optional: Hindi deletes the inherent schwa word-finally (कमल is kamal =
2 syllables, not ka-ma-la = 3) and in certain medial positions. Without
it, every Hindi line is overcounted by roughly one per word — which is
worse than no grounding, because it looks authoritative.

Implemented here: word-final deletion (near-universal in Hindi, and the
dominant error term) plus the standard medial VC_CV rule. Schwa deletion
in Hindi is genuinely not fully regular, so the result carries a caveat
rather than claiming exactness. Note also that Punjabi and Marathi
delete schwas differently from Hindi; this counter is tuned for Hindi
and says so.
"""
from __future__ import annotations

import re

from .base import GroundingResult, register_counter

# Independent vowels: अ आ इ ई उ ऊ ऋ ए ऐ ओ औ (plus ऑ ऍ for loanwords)
_INDEPENDENT_VOWELS = set("अआइईउऊऋॠऌएऐओऔऑऍ")
# Dependent vowel signs (matras) — these REPLACE the inherent schwa.
_MATRAS = set("ािीुूृॄॢेैोौॉॅ")
# Consonants: क through ह, plus nukta forms.
_CONSONANTS = set(
    "कखगघङचछजझञटठडढणतथदधनपफबभमयरलळवशषसह"
    "क़ख़ग़ज़ड़ढ़फ़"
)
_VIRAMA = "्"  # ्  — kills the inherent schwa (conjunct former)
_ANUSVARA_CANDRABINDU = set("ंँः")  # nasalization/visarga: no new syllable

_DEVANAGARI_RANGE = (0x0900, 0x097F)
_WORD_SPLIT_RE = re.compile(r"[\s।॥,.!?;:—\-​]+")


def _has_devanagari(text: str) -> bool:
    return any(_DEVANAGARI_RANGE[0] <= ord(c) <= _DEVANAGARI_RANGE[1] for c in text)


def _syllable_nuclei(word: str) -> list[str]:
    """Returns one marker per syllable nucleus, before schwa deletion.

    "schwa" = a consonant's inherent vowel that survived; "explicit" = an
    independent vowel or a matra.
    """
    nuclei: list[str] = []
    i = 0
    while i < len(word):
        char = word[i]

        if char in _INDEPENDENT_VOWELS:
            nuclei.append("explicit")
            i += 1
            continue

        if char in _CONSONANTS:
            nxt = word[i + 1] if i + 1 < len(word) else ""
            if nxt == _VIRAMA:
                # Conjunct: this consonant has no vowel of its own.
                i += 2
                continue
            if nxt in _MATRAS:
                nuclei.append("explicit")
                i += 2
                continue
            # Bare consonant: carries the inherent schwa (for now).
            nuclei.append("schwa")
            i += 1
            continue

        # Matras/nasalization handled with their consonant; skip anything else.
        i += 1
    return nuclei


def _count_word(word: str) -> int:
    nuclei = _syllable_nuclei(word)
    if not nuclei:
        return 0

    # Word-final schwa deletion: कमल -> ka-mal (2), not ka-ma-la (3).
    # Not applied to monosyllables (न stays "na", not zero).
    if len(nuclei) > 1 and nuclei[-1] == "schwa":
        nuclei = nuclei[:-1]

    # Medial schwa deletion, standard VC_CV rule: a schwa between two
    # consonants deletes when a vowel follows the next consonant —
    # समझ -> sam-jha. Applied right-to-left, which is the usual
    # formulation, and never to the first nucleus (word-initial schwas
    # are stable: अमर stays a-mar).
    result = list(nuclei)
    for idx in range(len(result) - 2, 0, -1):
        if (
            result[idx] == "schwa"
            and idx + 1 < len(result)
            and result[idx + 1] is not None
        ):
            # Only delete if a nucleus survives on both sides.
            before = any(n is not None for n in result[:idx])
            after = any(n is not None for n in result[idx + 1 :])
            if before and after:
                result[idx] = None
                break  # at most one medial deletion per word, conservatively

    return sum(1 for n in result if n is not None)


def count_hindi(text: str) -> GroundingResult | None:
    if not _has_devanagari(text):
        return None

    total = 0
    for line in text.splitlines():
        for word in _WORD_SPLIT_RE.split(line):
            if word:
                total += _count_word(word)

    if total == 0:
        return None

    return GroundingResult(
        value=total,
        unit="syllables",
        language="Hindi",
        caveat=(
            "schwa deletion applied (word-final and one medial position); "
            "Hindi schwa deletion is not fully regular, so treat as close "
            "rather than exact"
        ),
    )


register_counter("hi", count_hindi)
register_counter("pa", count_hindi)  # Gurmukhi-written Punjabi differs; see docs
register_counter("mr", count_hindi)
