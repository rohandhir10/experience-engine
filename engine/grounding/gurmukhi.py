"""Punjabi syllable counting for Gurmukhi.

Until now, `register_counter("pa", ...)` (engine/grounding/devanagari.py)
pointed `count_hindi` at Punjabi — which only recognizes the Devanagari
Unicode block. Real Punjabi lyrics are written in Gurmukhi (U+0A00-
0A7F), an entirely different block, so `_has_devanagari` always returned
False and the counter always declined. Punjabi source grounding has
never actually run; this module is what makes it run.

Gurmukhi is an abugida exactly like Devanagari: a consonant carries an
inherent schwa unless something removes it. Counting syllables means
counting vowel nuclei, where a nucleus is:

  - an independent vowel letter (ਅ ਆ ਇ ਈ ਉ ਊ ਏ ਐ ਓ ਔ — Gurmukhi has no
    vocalic-r letter the way Devanagari has ऋ)
  - a dependent vowel sign (matra) on a consonant (ਾ ਿ ੀ ੁ ੂ ੇ ੈ ੋ ੌ)
  - a consonant's inherent schwa, when not replaced by a matra, not
    killed by virama (੍), and not deleted by the schwa-deletion rule

**Schwa deletion**: applies the same word-final-plus-one-medial rule
already implemented for Hindi (devanagari.py) — word-final deletion is
the dominant, near-universal case in both languages (ਕਮਲ kamal = 2
syllables, not ka-ma-la = 3), and Punjabi shares enough of the broader
Indo-Aryan schwa-deletion pattern that the same rule is a reasonable,
disclosed approximation rather than a Punjabi-tuned model of its own.
It is not a claim that Punjabi and Hindi delete schwas identically —
they don't in every case — only that this is the same order of
approximation, carrying the same "close, not exact" caveat.

**Gurmukhi-specific marks that carry no syllable of their own**, each
confirmed by manual trace before shipping (see tests/test_grounding.py):
  - Nukta (਼, U+0A3C) modifies the preceding consonant's sound, not its
    syllable count. ਲ਼/ਸ਼/ਖ਼/ਗ਼/ਜ਼/ਫ਼ are Unicode composition exclusions —
    NFD decomposes them to base+nukta, NFC leaves them precomposed — so
    this counter NFD-normalizes and treats the nukta as a modifier on
    the preceding consonant, exactly the fix already made for
    Devanagari's ड़/ढ़/... (see that module's docstring for the double-
    counting bug this avoids). ੜ (RRA, U+0A5C) looks like a nukta form
    but is its own atomic Unicode letter with no decomposition at all —
    confirmed by direct check, not assumed — so it is listed as a plain
    consonant and never touches the nukta-offset logic.
  - Addak (ੱ, U+0A71) marks gemination of the *following* consonant
    (ਪੱਕਾ "pakka" = ਪ + addak + ਕ + ਾ). It sits between two consonants
    and is neither a nukta, a virama nor a matra, so it already falls
    through the existing "anything else, skip" path unchanged — verified
    ਪੱਕਾ still counts as 2 (pak-ka), not 3.
  - Bindi (ਂ, U+0A02) and Tippi (ੰ, U+0A70) both mark nasalization —
    Gurmukhi's equivalent of Devanagari's anusvara/candrabindu — and add
    no new syllable, same treatment.

**Not attempted**: the traditional vowel-bearer letters ਇੜੀ (IRI,
U+0A72) and ਊੜਾ (URA, U+0A73), used in some (mostly older/religious)
orthography to spell certain vowel sequences the precomposed
independent-vowel letters don't cover. They are listed as ordinary
consonants here, which is right when a matra follows them but would
wrongly credit a bare inherent schwa if one is ever used alone — rare
enough in contemporary lyrics that this is named rather than solved.
"""
from __future__ import annotations

import re
import unicodedata

from .base import GroundingResult, register_counter

# Independent vowels: ਅ ਆ ਇ ਈ ਉ ਊ ਏ ਐ ਓ ਔ — no vocalic-r letter here.
_INDEPENDENT_VOWELS = set("ਅਆਇਈਉਊਏਐਓਔ")
# Dependent vowel signs (matras) — these REPLACE the inherent schwa.
_MATRAS = set("ਾਿੀੁੂੇੈੋੌ")
# Consonants, base forms only. Nukta forms (ਲ਼ਸ਼ਖ਼ਗ਼ਜ਼ਫ਼) are deliberately
# NOT listed — see this module's docstring; NFD collapses them to
# base+nukta below. ੜ (RRA) IS listed directly: it has no decomposition
# despite looking like one, confirmed via unicodedata.decomposition().
# ੲ/ੳ (IRI/URA, vowel-bearer letters) are included as plain consonants —
# see the "Not attempted" note above.
_CONSONANTS = set(
    "ਕਖਗਘਙਚਛਜਝਞਟਠਡਢਣਤਥਦਧਨਪਫਬਭਮਯਰਲਵਸਹੜੲੳ"
)
_VIRAMA = "੍"  # kills the inherent schwa (conjunct former)
_NUKTA = "਼"  # modifies the preceding consonant; never a syllable
_NASALIZATION = set("ਂੰ")  # bindi, tippi: no new syllable
_ADDAK = "ੱ"  # gemination of the following consonant; no syllable of its own

_LATIN_RUN_RE = re.compile(r"[A-Za-z][A-Za-z']*")
_ASCII_DIGIT_RUN_RE = re.compile(r"\d")
_GURMUKHI_DIGITS = "੦੧੨੩੪੫੬੭੮੯"

_GURMUKHI_RANGE = (0x0A00, 0x0A7F)
_WORD_SPLIT_RE = re.compile(r"[\s।॥,.!?;:—\-​]+")


def _has_gurmukhi(text: str) -> bool:
    return any(_GURMUKHI_RANGE[0] <= ord(c) <= _GURMUKHI_RANGE[1] for c in text)


def _syllable_nuclei(word: str) -> list[str]:
    """Returns one marker per syllable nucleus, before schwa deletion.

    "schwa" = a consonant's inherent vowel that survived; "explicit" = an
    independent vowel or a matra. Addak and nasalization marks are
    neither a consonant, an independent vowel, nor handled specially —
    they fall through the trailing `i += 1` and contribute nothing,
    which is the correct behaviour for both (see module docstring).
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

        # Matras/nasalization/addak handled with their consonant, or
        # carry no syllable of their own; skip anything else.
        i += 1
    return nuclei


def _count_word(word: str) -> int:
    nuclei = _syllable_nuclei(word)
    if not nuclei:
        return 0

    # Word-final schwa deletion: ਕਮਲ -> ka-mal (2), not ka-ma-la (3).
    # Not applied to monosyllables.
    if len(nuclei) > 1 and nuclei[-1] == "schwa":
        nuclei = nuclei[:-1]

    # Medial schwa deletion, standard VC_CV rule, same as Hindi's — right
    # to left, never the first nucleus, at most one deletion per word.
    result = list(nuclei)
    for idx in range(len(result) - 2, 0, -1):
        if result[idx] == "schwa" and idx + 1 < len(result) and result[idx + 1] is not None:
            before = any(n is not None for n in result[:idx])
            after = any(n is not None for n in result[idx + 1 :])
            if before and after:
                result[idx] = None
                break

    return sum(1 for n in result if n is not None)


def count_punjabi(text: str) -> GroundingResult | None:
    # NFD, not NFC — ਲ਼/ਸ਼/ਖ਼/ਗ਼/ਜ਼/ਫ਼ are Unicode composition exclusions,
    # so NFC leaves them precomposed and the two input encodings would
    # stay different. NFD collapses both to the same base+nukta
    # sequence, which is what makes the count encoding-independent.
    text = unicodedata.normalize("NFD", text)

    if not _has_gurmukhi(text):
        return None

    # Punjabi numerals are suppletive the same way Hindi's are (ਇੱਕ ਦੋ
    # ਤਿੰਨ ... ਵੀਹ are separate words, not a regular place-value system),
    # so there is no honest way to syllabify an arbitrary digit run.
    # Checked for both ASCII and native Gurmukhi digits.
    if _ASCII_DIGIT_RUN_RE.search(text) or any(c in _GURMUKHI_DIGITS for c in text):
        return None

    total = 0
    for line in text.splitlines():
        for word in _WORD_SPLIT_RE.split(line):
            if word:
                total += _count_word(word)

    # Punjabi lyrics code-switch into English constantly, same as Hindi;
    # dropping it silently would undercount exactly the lines that do it
    # most (see devanagari.py and hangul.py for the same reasoning).
    from ..rhythm import count_syllables_word

    latin = sum(count_syllables_word(w) for w in _LATIN_RUN_RE.findall(text))

    if total == 0:
        return None

    caveat = (
        "schwa deletion applied (word-final and one medial position), using "
        "the same rule as the Hindi counter; Indo-Aryan schwa deletion is "
        "not fully regular in either language, so treat as close rather "
        "than exact"
    )
    if latin:
        caveat += f"; includes {latin} syllable(s) from Latin-script words"

    return GroundingResult(
        value=total + latin,
        unit="syllables",
        language="Punjabi",
        caveat=caveat,
    )


register_counter("pa", count_punjabi)
