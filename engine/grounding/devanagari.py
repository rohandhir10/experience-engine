"""Hindi/Marathi syllable counting for Devanagari.

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
rather than claiming exactness. Note also that Marathi deletes schwas
somewhat differently from Hindi; this counter is tuned for Hindi and
says so in its result (`language="Hindi"` even when registered for
"mr"). Punjabi is NOT handled here — see engine/grounding/gurmukhi.py.
"""
from __future__ import annotations

import re
import unicodedata

from .base import GroundingResult, register_counter

# Independent vowels: अ आ इ ई उ ऊ ऋ ए ऐ ओ औ (plus ऑ ऍ for loanwords)
_INDEPENDENT_VOWELS = set("अआइईउऊऋॠऌएऐओऔऑऍ")
# Dependent vowel signs (matras) — these REPLACE the inherent schwa.
_MATRAS = set("ािीुूृॄॢेैोौॉॅ")
# Consonants: क through ह. Nukta forms are deliberately NOT listed here.
#
# They used to be, written as "क़ख़ग़ज़ड़ढ़फ़" — which is 14 codepoints for 7
# letters, because each is a base consonant plus a combining nukta.
# set() over that string therefore put the bare NUKTA MARK in the
# consonant set and left the precomposed characters (U+0958-095F) out of
# it entirely, so the same word counted differently depending only on
# which Unicode form it arrived in: decomposed क+़ gained a spurious
# consonant, precomposed क़ was not recognised as a consonant at all and
# lost its vowel. Handled by normalising to NFD below and treating the
# nukta as what it is - a modifier on the preceding consonant.
_CONSONANTS = set("कखगघङचछजझञटठडढणतथदधनपफबभमयरलळवशषसह")
_VIRAMA = "्"  # ्  — kills the inherent schwa (conjunct former)
_NUKTA = "़"   # ़  — modifies the preceding consonant; never a syllable
_ANUSVARA_CANDRABINDU = set("ंँः")  # nasalization/visarga: no new syllable

_LATIN_RUN_RE = re.compile(r"[A-Za-z][A-Za-z']*")
_DIGIT_RUN_RE = re.compile(r"\d")

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
            # A nukta binds to this consonant and changes its sound, not
            # its syllable count - look past it for the real next mark.
            offset = 2 if word[i + 1 : i + 2] == _NUKTA else 1
            nxt = word[i + offset] if i + offset < len(word) else ""
            if nxt == _VIRAMA:
                # Conjunct: this consonant has no vowel of its own.
                i += offset + 1
                continue
            if nxt in _MATRAS:
                nuclei.append("explicit")
                i += offset + 1
                continue
            # Bare consonant: carries the inherent schwa (for now).
            nuclei.append("schwa")
            i += offset
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
    # NFD, not NFC: U+0958-095F (the precomposed nukta consonants) are
    # Unicode composition exclusions, so NFC leaves them precomposed and
    # the two encodings stay different. NFD collapses both to the same
    # base+nukta sequence, which is what makes the count encoding-
    # independent.
    text = unicodedata.normalize("NFD", text)

    if not _has_devanagari(text):
        return None

    # Hindi numerals are suppletive - एक दो तीन ... इक्कीस बाईस are all
    # separate words, unlike Sino-Korean's regular place-value system
    # (see grounding/hangul.py, which CAN count digits for that reason).
    # There is no honest way to syllabify an arbitrary digit run here, and
    # silently dropping it would be an undercount that still looks exact.
    if _DIGIT_RUN_RE.search(text):
        return None

    total = 0
    for line in text.splitlines():
        for word in _WORD_SPLIT_RE.split(line):
            if word:
                total += _count_word(word)

    # Hindi film lyrics code-switch into English constantly, and dropping
    # it silently undercounts exactly the lines that do it most. The
    # Korean counter already handles this for the same reason.
    from ..rhythm import count_syllables_word

    latin = sum(count_syllables_word(w) for w in _LATIN_RUN_RE.findall(text))

    if total == 0:
        return None

    caveat = (
        "schwa deletion applied (word-final and one medial position); "
        "Hindi schwa deletion is not fully regular, so treat as close "
        "rather than exact"
    )
    if latin:
        caveat += f"; includes {latin} syllable(s) from Latin-script words"

    return GroundingResult(
        value=total + latin,
        unit="syllables",
        language="Hindi",
        caveat=caveat,
    )


register_counter("hi", count_hindi)
register_counter("mr", count_hindi)
# Punjabi ("pa") is NOT registered here. Punjabi is written in Gurmukhi
# (U+0A00-0A7F), a different Unicode block entirely, so pointing it at
# this Devanagari-only counter meant `_has_devanagari` always failed and
# "pa" always silently declined. See engine/grounding/gurmukhi.py, which
# is what "pa" is actually registered to now.
