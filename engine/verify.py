"""Deterministic verification of the Burden of Change constitution.

Until now the constitution existed only as prompt text: the Judge was
asked to log every deviation from the Translator's literal anchor, and
asked to score its own `invention_penalty`. Both were self-reported by the
same model being audited — which is a claim, not evidence.

This module checks those claims in code, with no LLM involved. It reads a
finished run (an EngineResult dict or a stored .result.json) and answers
questions the Judge cannot grade itself on:

  - Does the deviation ledger actually cover the real textual differences
    between the literal anchor and the shipped line? (Law 1, No Invention:
    an unlogged change is an unaudited change.)
  - Are the logged deviations real, or does the ledger cite fragments that
    appear in neither the anchor nor the final line? (A fabricated audit
    trail is worse than none.)
  - Did emotion words or intensifiers appear that the anchor never had,
    with nothing in the ledger covering them? (Law 4, Restraint Ceiling.)
  - Were explanatory connectives added that the anchor never had?
    (Law 3, Compression Floor.)
  - Is the same motif rendered identically everywhere it recurs?
    (Law 5, Ambiguity Lock — checkable now that rulings report
    motif_renderings.)
  - Do any justifications reduce to "it sounds better"?

What this is NOT: proof that an adaptation is good, or that a
justification is *correct*. No static check can judge whether "one breath"
earns its place. It verifies that the audit trail is complete, non-
fabricated, and free of the specific mechanical failures the constitution
names — which is exactly the part a human reviewer would otherwise have to
take on faith.

Usage:
    python -m engine.verify examples/agar_tum_saath_ho.result.json
"""
from __future__ import annotations

import argparse
import difflib
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .llm_client import LLMClient
from .models import Deviation, SectionResultV1
from .recurrence import detect_recurring_endings

logger = logging.getLogger(__name__)
from .rhyme import phoneme_repetition_similarity as _compute_pho_similarity
from .rhyme import rhyme_density as _compute_rhyme_density
from .rhythm import (
    STRESS_UNKNOWN,
    count_syllables_text,
    phrase_end_sustainability as _phrase_end_sustainability,
    stress_pattern_word,
)

# Words that name a feeling outright. The Restraint Ceiling exists because
# a model's instinct is to explain the emotion the source left implicit;
# these are the tells. Deliberately a short, high-precision list — a long
# fuzzy one would fire constantly and train a reviewer to ignore it.
EMOTION_WORDS = frozenset(
    """
    sad sadness sorrow sorrowful grief grieving heartbreak heartbroken
    lonely loneliness alone despair desperate anguish agony misery
    miserable pain painful hurt hurting suffering ache aching longing
    yearning bitter bitterness angry anger rage furious joy joyful happy
    happiness delight elated ecstatic bliss blissful hopeless helpless
    devastated shattered broken empty numb tender tenderness passion
    passionate love loving beloved adore adoring
    """.split()
)

# Intensifiers inflate a line past the source's own register.
INTENSIFIERS = frozenset(
    """
    so very utterly completely totally absolutely deeply profoundly
    endlessly forever always never entirely wholly truly really quite
    extremely incredibly unbearably desperately hopelessly
    """.split()
)

# Connectives that explain a logical relationship the source left implicit.
# "and"/"or" are excluded: they join without explaining.
EXPLANATORY_CONNECTIVES = frozenset(
    """
    because since therefore thus hence although though whereas while
    unless whenever wherever furthermore moreover however nevertheless
    consequently accordingly
    """.split()
)

# Function words are the connective tissue prose needs and lyric sheds.
# A shipped line carrying a markedly higher proportion of them than the
# literal anchor is explaining rather than compressing.
FUNCTION_WORDS = frozenset(
    """
    a an the of to in on at by for with from into onto upon about over
    is are was were be been being am do does did has have had
    that which who whom whose this these those
    and but or nor so yet because although while
    it its he she him her they them their his your my our we you i
    as if then than there here when where what how
    """.split()
)

# Song-wide mean adaptation distance below this means the run produced a
# translation, not an adaptation. Set low deliberately: the bar is "the
# room did something", not "the room changed a lot".
TRANSLATION_FLOOR = 0.08

# A section whose line count collapses below this fraction of the
# anchor's has turned lyric into prose (Law 3, Compression Floor).
LINE_COLLAPSE_RATIO = 0.5

# Only meaningful on sections with enough lines for collapse to mean
# anything — a one-line section cannot "collapse".
MIN_LINES_FOR_COLLAPSE_CHECK = 3

# Consecutive-syllable-run thresholds for flagging a likely stress clash
# (too many stressed syllables in a row — awkward against any regular
# beat) or stress lapse (too many unstressed in a row — rhythmically
# flat). These are general English-prosody heuristics, not corpus-
# calibrated per genre or song — a provisional starting point, disclosed
# as such, the same way SYLLABLE_DELTA_WARN_RATIO below is.
MIN_STRESS_CLASH_RUN = 3
MIN_STRESS_LAPSE_RUN = 5

# Relative gap between source and shipped-line syllable/mora counts before
# it's worth a human read. Deliberately not an error and not proof of bad
# singability — languages differ in syllable structure, and this number
# was previously computed at generation time, handed to the Judge as
# context, then discarded with no way to check the Judge's own
# singability_rhythm score against anything. This makes that check
# possible; it does not make the Judge's score correct or incorrect.
SYLLABLE_DELTA_WARN_RATIO = 0.4

# Justifications that restate the conclusion instead of giving a reason.
TAUTOLOGICAL_PATTERNS = (
    r"\bsounds?\s+better\b",
    r"\bflows?\s+better\b",
    r"\breads?\s+better\b",
    r"\bmore\s+natural\b",
    r"\bmore\s+poetic\b",
    r"\bmore\s+beautiful\b",
    r"\bmore\s+elegant\b",
    r"\bimproves?\s+the\s+line\b",
    r"\bbetter\s+word\s+choice\b",
    r"^\s*(it\s+)?just\b",
    # Found in a real production run's priority_tradeoffs_made, justifying
    # a dropped triple-repetition ("then who is right") as reading better:
    # "feels smoother and more relatable... in a more natural and engaging
    # way." Same tautology class as the patterns above — explains why a
    # line is easier, not why a dropped source device earns its absence.
    r"\bsmoother\b",
    r"\bmore\s+relatable\b",
    r"\bmore\s+engaging\b",
    r"\bmore\s+accessible\b",
    # Found in a real production run justifying a single inserted comma
    # as "for clearer rhythm and flow" — the same class as "flows better"
    # above, which the earlier patterns missed only because it says
    # "clearer" instead of "better".
    r"\bclearer\s+(rhythm|flow|phrasing|cadence)\b",
    r"\brhythm\s+and\s+flow\b",
    r"\bbetter\s+(rhythm|flow|phrasing|cadence)\b",
    r"\bimproves?\s+(the\s+)?(flow|rhythm|readability|clarity)\b",
    r"\beasier\s+to\s+(read|sing|follow|say)\b",
)

# At or below this adaptation_distance, the shipped line is the literal
# anchor for all practical purposes — a token-level diff found essentially
# nothing between them. Not zero: a one-word article swap shouldn't be
# treated as a full rewrite either.
_HOLLOW_CHANGE_DISTANCE = 0.05

_TOKEN_RE = re.compile(r"[^\W\d_]+")

Severity = Literal["error", "warning"]


class Finding(BaseModel):
    law: str
    severity: Severity
    section: str
    detail: str
    fragment: str | None = None


class SectionVerification(BaseModel):
    section: str
    findings: list[Finding] = Field(default_factory=list)
    # Fraction of the words that actually changed between anchor and final
    # line which the deviation ledger accounts for. 1.0 = every change is
    # logged; 0.0 = the line was rewritten with an empty ledger.
    ledger_coverage: float
    computed_invention_penalty: float
    reported_invention_penalty: float
    changed_word_count: int
    # How far the shipped line actually moved from the literal anchor,
    # 0.0 = identical. This is the counterweight to invention_penalty:
    # that number only rises when the engine changes too much, so on its
    # own a pure translation scores perfectly. Reported together, the two
    # tell the real story — over-writing at one end, untouched
    # translation at the other, earned adaptation in between.
    adaptation_distance: float = 0.0
    # Measured, not judged (engine/rhyme.py) — the fraction of the shipped
    # line's end words that rhyme with another end word in the same
    # section. None when there are too few resolvable end words to mean
    # anything. Deliberately not tied to any pass/fail threshold: what
    # counts as "enough" rhyme varies by language and genre (a Hindi film
    # couplet and a traditional Japanese lyric have opposite defaults),
    # and no corpus exists yet to calibrate a per-genre expectation.
    rhyme_density: float | None = None
    # "sustainable"/"closed"/None (engine/rhythm.py::phrase_end_sustainability)
    # for the shipped line's last word - script-based, not tied to
    # target_language == "English" the way the CMU-dictionary checks are,
    # since it works for Latin-script, Hangul, Devanagari (Hindi, via
    # engine/g2p_hi.py's schwa-deletion heuristic), and - partially -
    # Perso-Arabic (Urdu, via engine/g2p_ur.py) output. Urdu still comes
    # back None for most real text: an unwritten trailing izafat vowel
    # can flip a stop-consonant ending open, so that one letter class
    # declines without a disambiguating diacritic rather than guessing.
    phrase_end_sustainability: str | None = None
    verifiable: bool = True  # False when no translator anchor exists

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]


class VerificationReport(BaseModel):
    sections: list[SectionVerification] = Field(default_factory=list)
    cross_section_findings: list[Finding] = Field(default_factory=list)
    # Sim_pho, adapted from Kim et al. 2023 (ISMIR) — see engine/rhyme.py's
    # module comment for exactly what's compared and why (the anchor's
    # phoneme-repetition density vs. the shipped line's, not source-
    # language vs. target-language, since CASTIA only has G2P for English).
    # Song-level, not per-section: a correlation needs a whole song's
    # worth of sections to mean anything. None when target_language isn't
    # English or too few sections have enough CMU-resolvable words on
    # both sides. Measured, never turned into pass/fail — same standard
    # as rhyme_density, and for the same reason: no corpus exists yet to
    # say what correlation is "enough."
    phoneme_repetition_similarity: float | None = None

    @property
    def all_findings(self) -> list[Finding]:
        out = list(self.cross_section_findings)
        for s in self.sections:
            out.extend(s.findings)
        return out

    @property
    def passed(self) -> bool:
        return not any(f.severity == "error" for f in self.all_findings)

    def summary(self) -> str:
        verifiable = [s for s in self.sections if s.verifiable]
        lines = ["CASTIA constitution verification", "=" * 34, ""]
        if not verifiable:
            lines.append("No verifiable sections (no translator anchor found).")
            return "\n".join(lines)

        mean_coverage = sum(s.ledger_coverage for s in verifiable) / len(verifiable)
        mean_computed = sum(s.computed_invention_penalty for s in verifiable) / len(verifiable)
        mean_reported = sum(s.reported_invention_penalty for s in verifiable) / len(verifiable)
        mean_distance = sum(s.adaptation_distance for s in verifiable) / len(verifiable)
        rhyme_values = [s.rhyme_density for s in verifiable if s.rhyme_density is not None]

        lines += [
            f"Sections verified:      {len(verifiable)}",
            f"Mean ledger coverage:   {mean_coverage:.0%}  [computed — exact "
            "diff against the ledger, not a claim]",
            f"Invention penalty:      {mean_computed:.2f} computed [evidence, "
            f"derived from the diff above] / {mean_reported:.2f} self-reported "
            "by the Judge [a claim by the same model being audited — read it "
            "as testimony, not as verified]",
            # Reported next to invention_penalty on purpose: one number
            # alone can only catch over-writing, and would score a
            # verbatim translation perfectly.
            f"Adaptation distance:    {mean_distance:.0%} moved from the "
            "literal anchor [computed]",
        ]
        if rhyme_values:
            mean_rhyme = sum(rhyme_values) / len(rhyme_values)
            lines.append(
                f"Rhyme density:          {mean_rhyme:.0%} of resolvable end "
                f"words rhyme ({len(rhyme_values)}/{len(verifiable)} sections "
                "measurable) [computed, NOT judged — no pass/fail threshold "
                "exists; what counts as 'enough' varies by language and genre]"
            )
        if self.phoneme_repetition_similarity is not None:
            lines.append(
                f"Phoneme repetition sim: {self.phoneme_repetition_similarity:+.2f} "
                "correlation between the anchor's and the shipped line's "
                "phoneme-repetition density across sections (Kim et al. 2023, "
                "adapted — see engine/rhyme.py) [computed, NOT judged — no "
                "pass/fail threshold exists; a negative value means the "
                "adaptation's repetition pattern runs opposite the literal "
                "anchor's, worth a listen]"
            )
        if mean_computed - mean_reported > 0.2:
            lines.append(
                "  ^ The Judge graded itself more leniently than the actual "
                "diff supports."
            )
        if mean_distance < TRANSLATION_FLOOR:
            lines.append(
                "  ^ Effectively a translation, not an adaptation — see the "
                "adaptation-floor finding below."
            )
        errors = [f for f in self.all_findings if f.severity == "error"]
        warnings = [f for f in self.all_findings if f.severity == "warning"]
        lines += [
            f"Errors:                 {len(errors)}",
            f"Warnings:               {len(warnings)}",
            "",
            "VERDICT: " + ("PASS" if self.passed else "FAIL"),
            "",
        ]
        for finding in errors + warnings:
            mark = "ERROR  " if finding.severity == "error" else "warning"
            lines.append(f"[{mark}] {finding.section} / {finding.law}")
            lines.append(f"          {finding.detail}")
            if finding.fragment:
                lines.append(f"          fragment: {finding.fragment!r}")
        return "\n".join(lines)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _changed_final_words(anchor: str, final: str) -> list[str]:
    """Words present in `final` that the diff marks as added or replaced —
    i.e. everything the shipped line says that the literal anchor didn't.
    """
    anchor_tokens = _tokens(anchor)
    final_tokens = _tokens(final)
    matcher = difflib.SequenceMatcher(None, anchor_tokens, final_tokens, autojunk=False)
    changed: list[str] = []
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert"):
            changed.extend(final_tokens[j1:j2])
    return changed


def _adaptation_distance(anchor: str, final: str) -> float:
    """0.0 when the shipped line is the literal anchor verbatim, rising
    toward 1.0 as it departs. Deliberately NOT a target to hit: a high
    number is not a goal, it is simply the other half of the picture that
    invention_penalty alone cannot show.
    """
    anchor_tokens, final_tokens = _tokens(anchor), _tokens(final)
    if not anchor_tokens and not final_tokens:
        return 0.0
    ratio = difflib.SequenceMatcher(
        None, anchor_tokens, final_tokens, autojunk=False
    ).ratio()
    return round(1.0 - ratio, 3)


def _function_word_ratio(text: str) -> float:
    tokens = _tokens(text)
    if not tokens:
        return 0.0
    return sum(1 for t in tokens if t in FUNCTION_WORDS) / len(tokens)


def _non_empty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


# Below this many extra (beyond-the-first) verbatim-repeated lines, the
# anchor's repetition is too thin for a drop to be worth flagging as its
# own error — a single incidental duplicate short line ("if you're here"
# appearing twice by coincidence, not as a device) is exactly the kind of
# borderline case LINE_COLLAPSE_RATIO above already has a say over;
# this check is for the more deliberate, larger repeat structures
# (a refrain, a couplet repeated twice) that a real production run
# showed being silently collapsed to one occurrence each while the
# section's overall line count still looked plausible.
MIN_REPEATED_LINES_FOR_CHECK = 2


def _check_repeated_line_preservation(
    section: str, anchor_lines: list[str], final_lines: list[str]
) -> list[Finding]:
    """A narrower, more sensitive signal than the LINE_COLLAPSE_RATIO check
    above. That check only fires when a section's line count roughly
    halves; a real production run (see docs/CAPABILITY_MATRIX.md's
    "Multi-line repeated block preservation" entry) showed a section
    keeping a normal-looking OVERALL line count while specifically
    dropping the anchor's repeat structure — a refrain or repeated
    couplet shipped only once each, with other lines running longer to
    fill the difference, hiding the loss from an aggregate count/length
    check.

    This does not try to match WORDING between anchor and final — CASTIA
    adapts, so a repeated line legitimately earns a different rendering
    each occurrence (see recurrence.py's module docstring). It checks a
    cruder but reliable structural proxy instead: if the anchor has
    verbatim-repeated lines, the shipped section's line count should
    exceed the anchor's DEDUPLICATED line count — the number of lines a
    "drop every repeat, ship the gist once" rewrite would produce. A
    shipped count at or below that number is exactly what that failure
    looks like, regardless of what the actual words are.
    """
    anchor_counts = Counter(_normalize(line) for line in anchor_lines)
    repeated_line_excess = sum(count - 1 for count in anchor_counts.values() if count >= 2)
    if repeated_line_excess < MIN_REPEATED_LINES_FOR_CHECK:
        return []

    distinct_anchor_lines = len(anchor_counts)
    if len(final_lines) > distinct_anchor_lines:
        return []

    return [
        Finding(
            law="Law 3 — Compression Floor (repetition)",
            severity="error",
            section=section,
            detail=(
                f"The literal anchor repeats {repeated_line_excess} line(s) "
                f"verbatim ({len(anchor_lines)} total lines, "
                f"{distinct_anchor_lines} distinct) but the shipped version "
                f"has only {len(final_lines)} line(s) — at or below the "
                "anchor's distinct-line count, consistent with every "
                "repeat being collapsed to a single occurrence instead of "
                "preserved."
            ),
        )
    ]


def repeated_lines_preserved(anchor: str, final: str) -> bool:
    """True unless `anchor` has meaningfully repeated verbatim lines that
    `final`'s line count fails to plausibly preserve — see
    _check_repeated_line_preservation's docstring for the exact
    reasoning and false-positive guardrails (MIN_REPEATED_LINES_FOR_CHECK,
    no wording match required). Exposed as a plain boolean, separate from
    the Finding-producing check above, so engine/pipeline.py can test
    individual Creative Adapter candidates BEFORE a Judge ruling exists —
    specifically, to tell "the Judge picked a repeat-dropping candidate
    when a better one was available" (re-judging fixes this) apart from
    "every candidate already dropped the repeat" (re-judging cannot fix
    this; the candidates themselves need to be regenerated).
    """
    return not _check_repeated_line_preservation(
        "_", _non_empty_lines(anchor), _non_empty_lines(final)
    )


def line_structure_preserved(anchor: str, final: str) -> bool:
    """False when `final` has collapsed `anchor`'s lyric lines into running
    prose — the same condition verify_section reports as a Law 3
    Compression Floor error, exposed as a plain boolean for the same
    reason repeated_lines_preserved above is.

    engine/pipeline.py uses this to tell two situations apart that need
    different corrections: the Judge picked a prose-y candidate when a
    line-preserving one was sitting right there (re-judging the existing
    pool fixes that), versus every candidate in the pool already
    flattened the verse (re-judging cannot fix that — there is nothing
    left to pick, so the candidates themselves have to be regenerated).
    """
    anchor_lines = _non_empty_lines(anchor)
    final_lines = _non_empty_lines(final)
    if len(anchor_lines) < MIN_LINES_FOR_COLLAPSE_CHECK:
        return True
    return len(final_lines) >= len(anchor_lines) * LINE_COLLAPSE_RATIO


def _stress_pattern_for_clash_detection(line: str) -> str:
    """Like rhythm.stress_pattern_word/_line, but every FUNCTION_WORDS
    token is forced to '0' regardless of its CMU citation-form stress.

    The CMU dictionary marks an isolated monosyllabic word as stressed —
    a single syllable always carries its own word's primary stress in
    citation form — but in connected natural speech, closed-class function
    words ("is", "of", "for", "to", "this", "that"...) are conventionally
    UNSTRESSED (function-word reduction, a basic fact about English
    prosody). Using raw citation-form stress produced clash counts of
    7-11 on ordinary sentences in testing — every real line has several
    function words, each wrongly counted as "stressed". This is the fix,
    not a refinement: without it the check is not measuring anything real.
    """
    chars = []
    for word in _tokens(line):
        if word in FUNCTION_WORDS:
            chars.append("0")
            continue
        pattern = stress_pattern_word(word)
        chars.append(pattern if pattern is not None else STRESS_UNKNOWN)
    return "".join(chars)


def _max_stress_runs(pattern: str) -> tuple[int, int]:
    """(longest run of consecutive stressed syllables, longest run of
    consecutive unstressed). An unknown-word marker ('x') breaks both
    runs — an unresolved word is missing information, not evidence that
    the run continues.
    """
    max_stressed = current_stressed = 0
    max_unstressed = current_unstressed = 0
    for char in pattern:
        if char == "1":
            current_stressed += 1
            current_unstressed = 0
        elif char == "0":
            current_unstressed += 1
            current_stressed = 0
        else:
            current_stressed = 0
            current_unstressed = 0
        max_stressed = max(max_stressed, current_stressed)
        max_unstressed = max(max_unstressed, current_unstressed)
    return max_stressed, max_unstressed


def _covered_by_ledger(word: str, deviations: list[Deviation]) -> bool:
    return any(word in _tokens(d.fragment_adapted) for d in deviations)


def _is_tautological(justification: str) -> bool:
    text = justification.strip().lower()
    if len(text) < 12:
        return True
    return any(re.search(p, text) for p in TAUTOLOGICAL_PATTERNS)


def _translator_anchor(result: SectionResultV1) -> str | None:
    for candidate in result.candidates:
        if candidate.agent == "translator":
            return candidate.text
    return None


# Below this fraction of the creative_adapter candidates' own median length,
# a shipped final_line is flagged as suspiciously incomplete rather than a
# legitimately terse choice among its own siblings.
_COMPLETENESS_RATIO = 0.35
# Candidates shorter than this (chars) are too small for length comparison
# to mean anything - skip the check rather than flag noise.
_COMPLETENESS_MIN_MEDIAN = 40


def _creative_candidate_median_length(result: SectionResultV1) -> int | None:
    lengths = sorted(
        len(c.text) for c in result.candidates if c.agent == "creative_adapter" and c.text
    )
    if not lengths:
        return None
    mid = len(lengths) // 2
    if len(lengths) % 2:
        return lengths[mid]
    return (lengths[mid - 1] + lengths[mid]) // 2


def verify_section(result: SectionResultV1, target_language: str = "English") -> SectionVerification:
    section = result.section
    ruling = result.ruling
    findings: list[Finding] = []

    anchor = _translator_anchor(result)
    if anchor is None:
        return SectionVerification(
            section=section,
            findings=[
                Finding(
                    law="verifiability",
                    severity="warning",
                    section=section,
                    detail=(
                        "No translator anchor in this section's candidates, so "
                        "the deviation ledger cannot be checked against anything. "
                        "(Expected for full-room results, which have no anchor.)"
                    ),
                )
            ],
            ledger_coverage=0.0,
            computed_invention_penalty=0.0,
            reported_invention_penalty=ruling.invention_penalty,
            changed_word_count=0,
            verifiable=False,
        )

    final = ruling.final_line
    deviations = ruling.deviations
    norm_anchor, norm_final = _normalize(anchor), _normalize(final)

    # --- Completeness: is the shipped line a fragment of its own siblings? -
    # Deliberately compared against the Creative Adapter's OWN candidates
    # (same target language, same script) rather than the Translator's
    # anchor (usually written in English regardless of target_language) -
    # a legitimately dense target script (e.g. CJK) can make a complete
    # line look short next to an English anchor, but it can't make it look
    # short next to its own siblings in the same script. Caught a real
    # production failure: a Japanese final_line of ~20 characters shipped
    # from a section whose creative_adapter candidates ran ~300+ characters
    # each, silently dropping the entire sacred refrain and a full stanza -
    # nothing upstream (schema-valid JSON, a plausible-looking why-sentence)
    # would have caught it without this check.
    median_len = _creative_candidate_median_length(result)
    if median_len is not None and median_len >= _COMPLETENESS_MIN_MEDIAN:
        ratio = len(final) / median_len
        if ratio < _COMPLETENESS_RATIO:
            findings.append(
                Finding(
                    law="completeness",
                    severity="error",
                    section=section,
                    detail=(
                        f"The shipped final line is {len(final)} character(s), "
                        f"only {ratio:.0%} of its own creative_adapter "
                        f"candidates' median length ({median_len} characters). "
                        "This looks like truncated or dropped content, not a "
                        "deliberately terse choice."
                    ),
                    fragment=final[:120],
                )
            )

    # --- Law 1: is every real change accounted for? ------------------------
    # This diffs the Translator's anchor against final_line word-by-word,
    # but the anchor is written in English regardless of target_language
    # (confirmed empirically: AGENT_BRIEFS["translator"]/generation_prompt_v1
    # never instruct it otherwise). Diffing English anchor tokens against a
    # non-English final line finds near-zero overlap by construction, not
    # because nothing was preserved - it would flag virtually the ENTIRE
    # final line as an unlogged, unjustified change on every single
    # non-English run. Since this check is severity="error", that isn't
    # just a cosmetic false positive - it would trigger a corrective retry
    # (engine/pipeline.py) on every non-English section regardless of
    # actual quality, and it would drown any genuine Law 1 finding
    # underneath. Only run the real diff-based check for an English
    # target; decline honestly for everything else rather than report a
    # number that looks measured but isn't.
    can_diff_against_anchor = target_language == "English"
    if can_diff_against_anchor:
        changed = _changed_final_words(anchor, final)
        uncovered = [w for w in changed if not _covered_by_ledger(w, deviations)]
        coverage = 1.0 if not changed else 1.0 - (len(uncovered) / len(changed))

        if changed and not deviations:
            findings.append(
                Finding(
                    law="Law 1 — No Invention",
                    severity="error",
                    section=section,
                    detail=(
                        f"The shipped line differs from the literal anchor in "
                        f"{len(changed)} word(s), but the deviation ledger is empty. "
                        "Every change is unaudited."
                    ),
                )
            )
        elif uncovered:
            sample = " ".join(dict.fromkeys(uncovered))[:120]
            findings.append(
                Finding(
                    law="Law 1 — No Invention",
                    severity="error" if coverage < 0.5 else "warning",
                    section=section,
                    detail=(
                        f"{len(uncovered)} of {len(changed)} changed word(s) "
                        f"({1 - coverage:.0%}) appear in the final line but in no "
                        "deviation entry — unlogged, therefore unjustified."
                    ),
                    fragment=sample,
                )
            )
    else:
        changed = []
        coverage = 1.0
        findings.append(
            Finding(
                law="Law 1 — No Invention",
                severity="warning",
                section=section,
                detail=(
                    "Word-level diffing against the literal anchor is "
                    "English-only (the anchor itself is always written in "
                    "English) and was skipped for this "
                    f"{target_language} final line. The ledger-integrity and "
                    "justification-quality checks below still run against "
                    "logged deviations directly, but 'every change accounted "
                    "for' coverage was not computed here - do not read this "
                    "section's ledger_coverage/computed_invention_penalty as "
                    "a real measurement of completeness."
                ),
            )
        )

    # --- The Burden of Change, enforced in the other direction --------------
    # Everything in Law 1 above asks "did you justify what you changed?"
    # This asks the inverse: "you logged a change - did you actually make
    # one?" The Judge's own standing rule is that when no candidate earns
    # a real improvement it ships the Translator's anchor as-is. Shipping
    # the anchor is therefore never a failure; shipping the anchor while
    # CLAIMING an improvement is, because the deviation ledger is the
    # product's entire audit trail and a "why" the reader can see through
    # devalues every genuine one next to it.
    #
    # Caught in a real production run: a section shipped token-identical
    # to its anchor apart from one inserted comma, with a ledger entry
    # justifying it as "for clearer rhythm and flow."
    #
    # Deliberately requires BOTH conditions - materially unchanged AND a
    # vacuous justification. Distance alone would punish a small but real
    # change that a token diff can't see (a statement turned into a
    # question, say), which is exactly the kind of precise, defensible
    # edit this engine is supposed to make; such an edit carries a
    # specific reason and so never trips the tautology half.
    if can_diff_against_anchor and _adaptation_distance(anchor, final) <= _HOLLOW_CHANGE_DISTANCE:
        hollow = [d for d in deviations if _is_tautological(d.justification)]
        if hollow:
            findings.append(
                Finding(
                    law="Law 1 — Burden of Change",
                    severity="error",
                    section=section,
                    detail=(
                        f"The shipped line is materially the literal anchor "
                        f"(adaptation distance "
                        f"{_adaptation_distance(anchor, final):.2f}), yet the "
                        f"ledger logs {len(hollow)} change(s) whose stated reason "
                        "does not name anything specific: "
                        f"{hollow[0].justification!r}. Either make a real, "
                        "defensible change to this line, or ship the anchor "
                        "with an empty deviation ledger - do not dress an "
                        "unchanged line up as an adapted one."
                    ),
                    fragment=hollow[0].fragment_adapted,
                )
            )

    # --- Is the ledger itself real? ----------------------------------------
    for deviation in deviations:
        if deviation.fragment_adapted.strip() and _normalize(
            deviation.fragment_adapted
        ) not in norm_final:
            findings.append(
                Finding(
                    law="ledger integrity",
                    severity="error",
                    section=section,
                    detail=(
                        "A deviation claims the final line says this, but it "
                        "does not appear there. The audit trail is fabricated."
                    ),
                    fragment=deviation.fragment_adapted,
                )
            )
        if deviation.fragment_original.strip() and _normalize(
            deviation.fragment_original
        ) not in norm_anchor:
            findings.append(
                Finding(
                    law="ledger integrity",
                    severity="warning",
                    section=section,
                    detail=(
                        "A deviation cites literal wording that does not appear "
                        "in the translator's anchor."
                    ),
                    fragment=deviation.fragment_original,
                )
            )
        if _is_tautological(deviation.justification):
            findings.append(
                Finding(
                    law="Law 1 — justification quality",
                    severity="warning",
                    section=section,
                    detail=(
                        "Justification restates the conclusion instead of giving "
                        f"a specific reason: {deviation.justification!r}"
                    ),
                    fragment=deviation.fragment_adapted,
                )
            )

    # --- Law 4: Restraint Ceiling -----------------------------------------
    anchor_set = set(_tokens(anchor))
    for word in dict.fromkeys(_tokens(final)):
        if word in anchor_set:
            continue
        if word in EMOTION_WORDS:
            findings.append(
                Finding(
                    law="Law 4 — Restraint Ceiling",
                    severity="warning",
                    section=section,
                    detail=(
                        f"The final line names a feeling ({word!r}) that the "
                        "literal anchor never states."
                    ),
                    fragment=word,
                )
            )
        elif word in INTENSIFIERS:
            findings.append(
                Finding(
                    law="Law 4 — Restraint Ceiling",
                    severity="warning",
                    section=section,
                    detail=(
                        f"The final line adds an intensifier ({word!r}) absent "
                        "from the literal anchor."
                    ),
                    fragment=word,
                )
            )
        elif word in EXPLANATORY_CONNECTIVES:
            findings.append(
                Finding(
                    law="Law 3 — Compression Floor",
                    severity="warning",
                    section=section,
                    detail=(
                        f"The final line adds an explanatory connective "
                        f"({word!r}) the anchor did not use — the source left "
                        "that relationship implicit."
                    ),
                    fragment=word,
                )
            )

    # --- The counterweight: signatures of translation left un-adapted ---
    # Everything above this point only fires when the engine changed too
    # much. These fire when it produced prose where the source had lyric
    # — the failure the Compression Floor exists to prevent, which no
    # amount of restraint-checking can detect.
    anchor_lines = _non_empty_lines(anchor)
    final_lines = _non_empty_lines(final)
    if (
        len(anchor_lines) >= MIN_LINES_FOR_COLLAPSE_CHECK
        and len(final_lines) < len(anchor_lines) * LINE_COLLAPSE_RATIO
    ):
        findings.append(
            Finding(
                law="Law 3 — Compression Floor",
                severity="error",
                section=section,
                detail=(
                    f"The literal anchor has {len(anchor_lines)} lines; the "
                    f"shipped version has {len(final_lines)}. Lyric lines "
                    "were merged into running sentences — the line breaks "
                    "are part of the form, not formatting."
                ),
            )
        )

    findings.extend(_check_repeated_line_preservation(section, anchor_lines, final_lines))

    anchor_ratio = _function_word_ratio(anchor)
    final_ratio = _function_word_ratio(final)
    if final_ratio - anchor_ratio > 0.10:
        findings.append(
            Finding(
                law="Law 3 — Compression Floor",
                severity="warning",
                section=section,
                detail=(
                    f"Function words rose from {anchor_ratio:.0%} of the "
                    f"literal anchor to {final_ratio:.0%} of the shipped "
                    "line — connective tissue was added, which is what "
                    "explaining looks like mechanically."
                ),
            )
        )

    weak = sum(1 for d in deviations if _is_tautological(d.justification))
    weak_ratio = weak / len(deviations) if deviations else 0.0
    computed = round(min(1.0, 0.7 * (1.0 - coverage) + 0.3 * weak_ratio), 3)

    # --- Singability, Stress, and Rhyme: all three lean on the CMU
    # Pronouncing Dictionary (engine/rhythm.py, engine/rhyme.py), which
    # only knows English. Run against non-English shipped text, the
    # syllable counter's out-of-dictionary fallback (a Latin vowel-cluster
    # heuristic) would silently under/over-count Devanagari, Hangul, or
    # kana "words" — a fabricated number, not a measured one, the exact
    # failure this module exists to avoid elsewhere (see rhythm.py's
    # STRESS_UNKNOWN). Skipped entirely, not approximated, for any other
    # target_language until each has its own real prosody/rhyme analysis.
    rhyme_density_value: float | None = None
    if target_language == "English":
        # --- Singability: check the Judge's dimension_scores claim against
        # the one number that was actually computed, not just asserted ---
        source_count = result.source_syllable_count
        if source_count:
            shipped_count = count_syllables_text(final)
            delta_ratio = abs(shipped_count - source_count) / source_count
            if delta_ratio > SYLLABLE_DELTA_WARN_RATIO:
                findings.append(
                    Finding(
                        law="Singability check",
                        severity="warning",
                        section=section,
                        detail=(
                            f"Source is ~{source_count} syllables/morae; the "
                            f"shipped line is ~{shipped_count} English syllables — "
                            f"a {delta_ratio:.0%} gap. Not proof of a rhythm "
                            "problem (languages differ in syllable structure), "
                            "but worth a human read, especially if the ruling's "
                            "singability_rhythm score claims this is strong."
                        ),
                    )
                )

        # --- Stress: clash/lapse in the shipped line, English-internal, no
        # source or melody needed (Phase 3A) ------------------------------
        stress_pattern = _stress_pattern_for_clash_detection(final)
        max_stressed_run, max_unstressed_run = _max_stress_runs(stress_pattern)
        if max_stressed_run >= MIN_STRESS_CLASH_RUN:
            findings.append(
                Finding(
                    law="Stress check",
                    severity="warning",
                    section=section,
                    detail=(
                        f"{max_stressed_run} consecutive stressed syllables in the "
                        "shipped line — a likely stress clash. Provisional "
                        "threshold from general English prosody, not corpus-"
                        "calibrated per genre; a prompt to listen to the line, "
                        "not a verdict."
                    ),
                )
            )
        if max_unstressed_run >= MIN_STRESS_LAPSE_RUN:
            findings.append(
                Finding(
                    law="Stress check",
                    severity="warning",
                    section=section,
                    detail=(
                        f"{max_unstressed_run} consecutive unstressed syllables — "
                        "a likely stress lapse (a rhythmically flat stretch). "
                        "Same disclosed-limits caveat as the clash check above."
                    ),
                )
            )

        # --- Rhyme: measured, not judged (Phase 3B) — see engine/rhyme.py -
        rhyme_density_value = _compute_rhyme_density(_non_empty_lines(final))

    # --- Phrase-end sustainability: script-based (Latin, Hangul,
    # Devanagari, and - partially - Perso-Arabic), not target_language ==
    # "English"-gated the way the CMU-dictionary checks above are. Urdu
    # reports None rather than a guess whenever the ending is ambiguous
    # without a diacritic (engine/g2p_ur.py).
    non_empty_final_lines = _non_empty_lines(final)
    sustainability = (
        _phrase_end_sustainability(non_empty_final_lines[-1]) if non_empty_final_lines else None
    )
    if sustainability == "closed":
        findings.append(
            Finding(
                law="Phrase-end sustainability check",
                severity="warning",
                section=section,
                detail=(
                    "This section's last line ends on a stop consonant "
                    "(or its Hangul/Devanagari-coda equivalent) - "
                    "physically impossible to hold for a sustained note. "
                    "Worth a listen if this is meant to land on a held "
                    "final note. Only checked for Latin-script, Hangul, "
                    "and Devanagari output; not evaluated here for "
                    "Perso-Arabic (Urdu) targets."
                ),
            )
        )

    return SectionVerification(
        section=section,
        findings=findings,
        ledger_coverage=round(coverage, 3),
        computed_invention_penalty=computed,
        reported_invention_penalty=ruling.invention_penalty,
        changed_word_count=len(changed),
        adaptation_distance=_adaptation_distance(anchor, final),
        rhyme_density=rhyme_density_value,
        phrase_end_sustainability=sustainability,
    )


_WH_WORD_RE = re.compile(r"\b(what|why|how|who|when|where)\b", re.IGNORECASE)
_COPULA_RE = re.compile(r"\b(is|are|was|were|am)\b|'s\b", re.IGNORECASE)


def _terminal_features(line: str) -> tuple[bool, bool, bool]:
    """Three cheap, independent syntactic facts about a line's ending, used
    only to compare sections against each other — never to judge a line on
    its own. (ends in '?', contains a wh-word, contains a copula.)
    """
    stripped = line.strip()
    return (
        stripped.endswith("?"),
        bool(_WH_WORD_RE.search(stripped)),
        bool(_COPULA_RE.search(stripped)),
    )


def _check_structural_recurrence(
    source_sections: list[tuple[str, str]],
    sections_by_name: dict[str, SectionResultV1],
) -> list[Finding]:
    """Independent of Song DNA's motif list entirely — detects a recurring
    source-side ending (engine/recurrence.py) and checks whether the
    sections it spans share a consistent TERMINAL SYNTACTIC PATTERN in
    their final lines, not identical wording (see recurrence.py's
    docstring for why identical wording is the wrong bar for a structural
    device like a radif).

    This is a narrow, disclosed-limits check: three boolean features,
    majority vote, flag the minority. It will catch a structural break
    that changes which of these features hold (e.g. a copular "what is X"
    question rewritten as a non-copular "why does X" question) but will
    miss a break that preserves all three features while still changing
    the underlying logical structure. That is a real limit, not a bug —
    recorded here rather than overclaimed.
    """
    findings: list[Finding] = []
    matches = detect_recurring_endings(source_sections)
    for match in matches:
        rows = [
            (name, sections_by_name[name].ruling.final_line)
            for name in match.sections
            if name in sections_by_name
        ]
        if len(rows) < 2:
            continue
        feature_vectors = [(_terminal_features(line)) for _, line in rows]
        # Majority per feature, independently.
        majority = tuple(
            sum(v[i] for v in feature_vectors) * 2 > len(feature_vectors)
            for i in range(3)
        )
        labels = ("ends in a question", "uses a wh-word", "uses a copula (is/are/was/were)")
        for (name, line), vector in zip(rows, feature_vectors):
            broken = [labels[i] for i in range(3) if vector[i] != majority[i]]
            if broken:
                findings.append(
                    Finding(
                        law="Structural recurrence",
                        severity="warning",
                        section=name,
                        detail=(
                            f"The source repeats the ending {match.shared_suffix!r} "
                            f"across {len(match.sections)} sections — a formal "
                            "device (e.g. a ghazal's radif), never tagged as a "
                            "motif by Song DNA. Most of those sections' final "
                            f"lines share this pattern: {', '.join(labels[i] for i in range(3) if majority[i])}. "
                            f"This one breaks it: {', '.join(broken)}."
                        ),
                        fragment=line,
                    )
                )
    return findings


# Valid engine/prompts.py::cross_language_fidelity_prompt responses that
# indicate a real concern - "preserved" means no finding.
_FIDELITY_BREAK_KINDS = frozenset({"flattened", "amplified", "inverted"})


def check_cross_language_fidelity(
    client: LLMClient,
    source_text: str,
    final_line: str,
    source_language: str,
    target_language: str,
    section_name: str,
) -> Finding | None:
    """The one check in this file that compares the shipped line against
    the actual SOURCE-LANGUAGE text directly - docs/CAPABILITY_MATRIX.md's
    "Cross-language emotional fidelity verification": every other check
    here only ever compares the shipped line against the Translator's own
    English literal anchor, so an anchor that was ALREADY emotionally
    wrong (flattened, amplified, or inverted relative to the true source)
    is silently treated as ground truth by everything downstream.

    Tier 2 (an LLM judgment, not a deterministic measurement) by
    necessity - real bilingual reading comprehension of the source
    language is not something a word-diff or dictionary lookup can
    substitute for. Returns None (not an error) on any call failure or
    unparseable response, same "decline honestly rather than fake a
    result" standard the rest of this file already holds itself to -
    engine/comics_vision.py's optional read pass is the same pattern.
    Always severity="warning": this is a probabilistic judgment call
    about something as genuinely ambiguous as emotional tone, not a
    fact - it should be visible, never auto-block or auto-retry a
    section the way a deterministic "error" finding does.
    """
    from . import prompts

    system, user = prompts.cross_language_fidelity_prompt(
        source_text, final_line, source_language, target_language, section_name
    )
    try:
        data = client.complete_json(
            system, user, max_tokens=300, stage="cross_language_fidelity"
        )
    except Exception as exc:  # noqa: BLE001 — deliberately broad; see docstring
        logger.warning(
            "Cross-language fidelity check failed for section %r, skipping: %s",
            section_name,
            exc,
        )
        return None

    kind = data.get("emotional_fidelity")
    if kind not in _FIDELITY_BREAK_KINDS:
        return None  # "preserved", or an unrecognized value - either way, no finding.

    concern = data.get("concern") or "No further explanation given."
    confidence = data.get("confidence")
    confidence_note = (
        f" (model confidence: {confidence:.0%})" if isinstance(confidence, (int, float)) else ""
    )
    return Finding(
        law="Cross-language emotional fidelity",
        severity="warning",
        section=section_name,
        detail=(
            f"Reading the actual {source_language} source directly (not the "
            f"Translator's English anchor), the shipped line's emotional tone "
            f"looks {kind.upper()} relative to the source{confidence_note}: {concern}"
        ),
        fragment=final_line[:120],
    )


def verify_result(result_dict: dict, client: LLMClient | None = None) -> VerificationReport:
    """Verifies a stored EngineResult dict (a .result.json).

    `client`, when given, additionally runs check_cross_language_fidelity
    against every section with real source text — one extra LLM call per
    section, so this is opt-in rather than the default: every OTHER check
    in this function is a deterministic, zero-cost computation, and this
    is the one exception. None (the default) reproduces the exact
    pre-existing behavior of this function with zero added cost/latency —
    every existing caller of verify_result is unaffected without passing
    this explicitly.
    """
    report = VerificationReport()

    sections: list[SectionResultV1] = []
    for raw in result_dict.get("sections", []):
        try:
            sections.append(SectionResultV1.model_validate(raw))
        except Exception:  # noqa: BLE001 — full-room results have another shape
            continue

    target_language = result_dict.get("target_language", "English")
    for section in sections:
        report.sections.append(verify_section(section, target_language=target_language))

    if target_language == "English":
        # Same anchor/final pairing verify_section already extracts per
        # section (_translator_anchor) - reused here at the song level,
        # since a correlation needs the whole song's sections, not one.
        pho_pairs: list[tuple[str, str]] = []
        for section in sections:
            anchor = _translator_anchor(section)
            if anchor is not None:
                pho_pairs.append((anchor, section.ruling.final_line))
        report.phoneme_repetition_similarity = _compute_pho_similarity(pho_pairs)

    source_sections = [
        (s["name"], s["source_text"])
        for s in result_dict.get("source_sections", [])
        if s.get("source_text")
    ]
    if source_sections:
        sections_by_name = {s.section: s for s in sections}
        report.cross_section_findings.extend(
            _check_structural_recurrence(source_sections, sections_by_name)
        )

        source_language = result_dict.get("source_language")
        if client is not None and source_language:
            for name, source_text in source_sections:
                result = sections_by_name.get(name)
                if result is None or result.skipped:
                    continue
                finding = check_cross_language_fidelity(
                    client,
                    source_text,
                    result.ruling.final_line,
                    source_language,
                    target_language,
                    name,
                )
                if finding is not None:
                    report.cross_section_findings.append(finding)

    # --- Was this an adaptation at all? ------------------------------------
    # Checked song-wide, never per line. A single section that legitimately
    # matches the literal anchor is correct and common — the constitution
    # says so outright ("an empty deviations list is a GOOD sign"). But a
    # whole song that never departs from the anchor is a translation, and
    # nothing else in this verifier can see that: every other check only
    # fires on changing too much, so a verbatim translation scores
    # perfectly. Firing at the song level is also what keeps this from
    # becoming a change quota the engine could game by manufacturing
    # deviations — exactly what the Burden of Change exists to prevent.
    verifiable = [s for s in report.sections if s.verifiable]
    if verifiable:
        mean_distance = sum(s.adaptation_distance for s in verifiable) / len(verifiable)
        if mean_distance < TRANSLATION_FLOOR:
            report.cross_section_findings.append(
                Finding(
                    law="Adaptation floor",
                    severity="error",
                    section=f"whole song ({len(verifiable)} sections)",
                    detail=(
                        f"Mean adaptation distance is {mean_distance:.1%} — the "
                        "shipped lyrics are, throughout, the Translator's "
                        "literal anchor. Every other check here passes on a "
                        "verbatim translation, so this is the one that will "
                        "not: CASTIA's output is supposed to be an adaptation "
                        "the original writer would recognize as their own "
                        "work, not a translation of it. Read the Creative "
                        "Adapter's candidates for this run — if none of them "
                        "earned their changes, that is a real finding about "
                        "the song; if the Judge simply defaulted to the "
                        "anchor, that is a finding about the Judge."
                    ),
                )
            )

    # --- Compensations: decided once, binding thereafter -------------------
    # A speaker the source marks as 俺 cannot be carried by blunt diction in
    # verse 1 and hedging diction in the chorus — that is the same
    # inconsistency Law 5 catches for phrases, applied to register.
    carriers: dict[str, tuple[str, str]] = {}  # feature -> (carrier, section)
    for section in sections:
        for compensation in getattr(section, "compensations", []):
            key = compensation.source_feature.strip().lower()
            if key not in carriers:
                carriers[key] = (compensation.english_carrier, section.section)
                continue
            first_carrier, first_section = carriers[key]
            if _normalize(compensation.english_carrier) != _normalize(first_carrier):
                report.cross_section_findings.append(
                    Finding(
                        law="Compensation consistency",
                        severity="error",
                        section=f"{first_section} vs {section.section}",
                        detail=(
                            f"{compensation.source_feature!r} was carried by "
                            f"{first_carrier!r} in {first_section} but "
                            f"{compensation.english_carrier!r} in "
                            f"{section.section}. The channel English uses to "
                            "carry an untranslatable source feature is a "
                            "property of the speaker, not of the line — it is "
                            "decided once and holds for the song."
                        ),
                        fragment=compensation.source_feature,
                    )
                )

    # --- Cultural anchors: one disposition per term, song-wide -------------
    # (docs/MULTILINGUAL_V2.md §6.) Deciding to preserve "ishq" in the first
    # chorus and translate it in the second is the same failure the
    # Ambiguity Lock exists to prevent, so it is checked the same way.
    anchors: dict[str, tuple[str, str]] = {}  # term -> (disposition, section)
    for section in sections:
        for anchor in section.ruling.cultural_anchors:
            key = anchor.term.strip().lower()
            if key not in anchors:
                anchors[key] = (anchor.disposition, section.section)
                continue
            first_disposition, first_section = anchors[key]
            if anchor.disposition != first_disposition:
                report.cross_section_findings.append(
                    Finding(
                        law="Cultural anchor consistency",
                        severity="error",
                        section=f"{first_section} vs {section.section}",
                        detail=(
                            f"The term {anchor.term!r} was handled as "
                            f"{first_disposition!r} in {first_section} but "
                            f"{anchor.disposition!r} in {section.section}. A "
                            "culturally dense term must be handled the same "
                            "way at every recurrence."
                        ),
                        fragment=anchor.term,
                    )
                )

    # --- Law 5: Ambiguity Lock, across sections ----------------------------
    renderings: dict[str, tuple[str, str]] = {}  # motif -> (rendering, section)
    for section in sections:
        for motif, rendering in section.ruling.motif_renderings.items():
            if motif not in renderings:
                renderings[motif] = (rendering, section.section)
                continue
            first_rendering, first_section = renderings[motif]
            if _normalize(rendering) != _normalize(first_rendering):
                report.cross_section_findings.append(
                    Finding(
                        law="Law 5 — Ambiguity Lock",
                        severity="error",
                        section=f"{first_section} vs {section.section}",
                        detail=(
                            f"The motif {motif!r} is rendered two different "
                            f"ways: {first_rendering!r} then {rendering!r}. A "
                            "deliberately repeated phrase must keep identical "
                            "wording on every recurrence."
                        ),
                    )
                )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify a finished CASTIA run against the Burden of Change "
            "constitution. Deterministic; no LLM calls, no API key."
        )
    )
    parser.add_argument("result_file", type=Path, help="A .result.json from engine.cli")
    parser.add_argument("--json", action="store_true", help="Emit the full report as JSON")
    args = parser.parse_args(argv)

    report = verify_result(json.loads(args.result_file.read_text()))

    if args.json:
        print(json.dumps(report.model_dump(), indent=2, ensure_ascii=False))
    else:
        print(report.summary())
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
