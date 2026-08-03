"""Deterministic end-rhyme measurement for shipped English lines, using
the same CMU-dictionary-backed `pronouncing` library already in use for
syllable counting (engine/rhythm.py). `rhyming_part()` exposes the part
of a word's pronunciation that actually has to match for a rhyme, which
is the right unit to compare — orthography is not: "though" and "through"
don't rhyme (OW1 vs UW1); "fire" and "higher" do (AY1 ER0 both), despite
neither spelling pair suggesting the opposite of what's true.

This module MEASURES. It does not judge. Whether a given rhyme_density is
"enough" varies by language and genre: Hindi film-song couplets expect
dense end rhyme, while traditional Japanese verse does not rhyme at all
by convention (engine/profiles/japanese.json's rhyme_convention says so
explicitly — Japanese phonology makes rhyme nearly automatic and
therefore uninformative). A single hardcoded threshold across every
language/genre would misfire constantly on exactly the cases the profiles
already document. Calibrating an expectation per genre is future work,
gated on real corpus data existing to calibrate it — not something to
guess at here.
"""
from __future__ import annotations

import re

import pronouncing

_WORD_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")


def rhyming_part_word(word: str) -> str | None:
    """The ARPAbet suffix from the last stressed vowel onward — the part
    that has to match for two words to rhyme. None if the word isn't in
    the CMU dictionary (never guessed from spelling).
    """
    phones_list = pronouncing.phones_for_word(word.lower())
    if not phones_list:
        return None
    return pronouncing.rhyming_part(phones_list[0])


def _line_end_word(line: str) -> str | None:
    words = _WORD_RE.findall(line)
    return words[-1] if words else None


def end_rhyme_scheme(lines: list[str]) -> list[str | None]:
    """One label per line: lines whose end words share a rhyming part get
    the same letter (A, B, C, ...), assigned in order of first appearance
    — the conventional ABAB/AABB notation. None for a line whose end word
    isn't in the CMU dictionary, reported as unresolved rather than
    guessed.
    """
    end_words = [_line_end_word(line) for line in lines]
    parts = [rhyming_part_word(w) if w else None for w in end_words]

    labels: dict[str, str] = {}
    result: list[str | None] = []
    next_label = ord("A")
    for part in parts:
        if part is None:
            result.append(None)
            continue
        if part not in labels:
            labels[part] = chr(next_label)
            next_label += 1
        result.append(labels[part])
    return result


def rhyme_density(lines: list[str]) -> float | None:
    """Fraction of resolvable end words that rhyme with at least one
    other end word in the same set of lines. None when fewer than 2 end
    words are resolvable (density is undefined here, not zero — reporting
    0.0 would claim "measured no rhyme" when the truth is "couldn't
    measure enough of it").
    """
    scheme = end_rhyme_scheme(lines)
    resolvable = [label for label in scheme if label is not None]
    if len(resolvable) < 2:
        return None
    counts: dict[str, int] = {}
    for label in resolvable:
        counts[label] = counts.get(label, 0) + 1
    rhymed = sum(1 for label in resolvable if counts[label] > 1)
    return rhymed / len(resolvable)


# ---------------------------------------------------------------------------
# Phoneme repetition similarity — adapted from Kim, Watanabe, Goto & Nam,
# "A Computational Evaluation Framework for Singable Lyric Translation"
# (ISMIR 2023). Their Sim_pho compares a source-language section's overall
# phonetic-repetition density against the target-language section's, via
# each section's phoneme distinct-2 (unique bigrams / total bigrams —
# lower means more repetition) and a Spearman correlation across a whole
# song's sections.
#
# rhyme_density above only looks at line-END words (classic end-rhyme);
# distinct-2 captures repetition anywhere in a section (internal rhyme,
# alliteration, repeated grammatical endings) — a materially different,
# broader signal, which is why it's worth having both.
#
# What's NOT reproduced here: the paper's cross-LANGUAGE comparison
# (source-language phonemes vs. target-language phonemes) needs a G2P
# tool per language — AURA only has one for English (the CMU dictionary,
# same as rhythm.py/rhyming_part_word above). Comparing phonemes across
# two different languages' phoneme inventories with only one language's
# G2P available isn't possible without fabricating the other side.
# Adapted instead to the comparison AURA CAN make honestly with the tools
# that exist: the Translator's literal anchor (English, maximally
# faithful) against the Judge's shipped final line (English, the actual
# adaptation) — same language, same CMU dictionary, real measurement.
# This asks a related but distinct question than the paper's original:
# not "does the target preserve the source's repetition pattern" but
# "did adapting away from the literal anchor distort the repetition
# pattern a faithful rendering would have had." Only meaningful for an
# English target — see engine/verify.py's target_language gate.
_PHONEME_RE = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")
MIN_PHONEMES_FOR_DISTINCT2 = 6  # need a few bigrams before the ratio means anything
MIN_SECTIONS_FOR_PHO_SIMILARITY = 3  # a correlation needs more than 1-2 points


def _phones_for_text(text: str) -> list[str] | None:
    """Flat phoneme sequence for a whole (English) text, one '<eos>' marker
    per line boundary (matching the paper's bigram construction) so a
    bigram never silently straddles two unrelated lines. Words absent
    from the CMU dictionary are skipped rather than guessed at — this
    thins the phoneme count for slang/loanwords/names, which is the
    honest tradeoff (fewer, real phonemes) over a fabricated pronunciation.
    """
    phones: list[str] = []
    for line in text.splitlines():
        words = _PHONEME_RE.findall(line)
        line_had_words = False
        for word in words:
            phones_list = pronouncing.phones_for_word(word.lower())
            if not phones_list:
                continue
            phones.extend(phones_list[0].split())
            line_had_words = True
        if line_had_words:
            phones.append("<eos>")
    return phones or None


def phoneme_distinct2(text: str) -> float | None:
    """distinct-2 (Li et al. 2016, adapted from words to phonemes by Kim
    et al. 2023): unique phoneme bigrams / total phoneme bigrams. Lower
    means more repetition. None if too few phonemes were resolvable to
    trust the ratio (see MIN_PHONEMES_FOR_DISTINCT2) — never computed
    from a handful of words and reported as if it meant something.
    """
    phones = _phones_for_text(text)
    if phones is None or len(phones) < MIN_PHONEMES_FOR_DISTINCT2:
        return None
    bigrams = list(zip(phones, phones[1:]))
    if not bigrams:
        return None
    return len(set(bigrams)) / len(bigrams)


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    """Spearman rank correlation without a scipy dependency: rank both
    lists, then Pearson-correlate the ranks. None for constant input
    (zero variance - correlation is undefined, not 0)."""
    n = len(xs)

    def _ranks(values: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: values[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and values[order[j + 1]] == values[order[i]]:
                j += 1
            average_rank = (i + j) / 2 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = average_rank
            i = j + 1
        return ranks

    rx, ry = _ranks(xs), _ranks(ys)
    mean_rx, mean_ry = sum(rx) / n, sum(ry) / n
    cov = sum((a - mean_rx) * (b - mean_ry) for a, b in zip(rx, ry))
    var_x = sum((a - mean_rx) ** 2 for a in rx)
    var_y = sum((b - mean_ry) ** 2 for b in ry)
    if var_x == 0 or var_y == 0:
        return None
    return cov / (var_x**0.5 * var_y**0.5)


def phoneme_repetition_similarity(pairs: list[tuple[str, str]]) -> float | None:
    """Sim_pho, adapted (see module comment above): Spearman correlation
    between the anchor's and the final line's phoneme distinct-2 across a
    whole song's sections. `pairs` is [(anchor_text, final_text), ...],
    one per section, in song order. Returns None when fewer than
    MIN_SECTIONS_FOR_PHO_SIMILARITY sections have a resolvable distinct-2
    on BOTH sides — a correlation over 1-2 points isn't a trend, and a
    section with too few CMU-resolvable words on either side is excluded
    rather than guessed at.
    """
    anchor_values: list[float] = []
    final_values: list[float] = []
    for anchor_text, final_text in pairs:
        anchor_pho = phoneme_distinct2(anchor_text)
        final_pho = phoneme_distinct2(final_text)
        if anchor_pho is None or final_pho is None:
            continue
        anchor_values.append(anchor_pho)
        final_values.append(final_pho)
    if len(anchor_values) < MIN_SECTIONS_FOR_PHO_SIMILARITY:
        return None
    return _spearman(anchor_values, final_values)
