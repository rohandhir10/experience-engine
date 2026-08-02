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
import re
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .models import Deviation, SectionResultV1

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
)

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
    verifiable: bool = True  # False when no translator anchor exists

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]


class VerificationReport(BaseModel):
    sections: list[SectionVerification] = Field(default_factory=list)
    cross_section_findings: list[Finding] = Field(default_factory=list)

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
        lines = ["AURA constitution verification", "=" * 34, ""]
        if not verifiable:
            lines.append("No verifiable sections (no translator anchor found).")
            return "\n".join(lines)

        mean_coverage = sum(s.ledger_coverage for s in verifiable) / len(verifiable)
        mean_computed = sum(s.computed_invention_penalty for s in verifiable) / len(verifiable)
        mean_reported = sum(s.reported_invention_penalty for s in verifiable) / len(verifiable)
        mean_distance = sum(s.adaptation_distance for s in verifiable) / len(verifiable)

        lines += [
            f"Sections verified:      {len(verifiable)}",
            f"Mean ledger coverage:   {mean_coverage:.0%}",
            f"Invention penalty:      {mean_computed:.2f} computed / "
            f"{mean_reported:.2f} self-reported by the Judge",
            # Reported next to invention_penalty on purpose: one number
            # alone can only catch over-writing, and would score a
            # verbatim translation perfectly.
            f"Adaptation distance:    {mean_distance:.0%} moved from the "
            "literal anchor",
        ]
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


def verify_section(result: SectionResultV1) -> SectionVerification:
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

    # --- Law 1: is every real change accounted for? ------------------------
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

    return SectionVerification(
        section=section,
        findings=findings,
        ledger_coverage=round(coverage, 3),
        computed_invention_penalty=computed,
        reported_invention_penalty=ruling.invention_penalty,
        changed_word_count=len(changed),
        adaptation_distance=_adaptation_distance(anchor, final),
    )


def verify_result(result_dict: dict) -> VerificationReport:
    """Verifies a stored EngineResult dict (a .result.json)."""
    report = VerificationReport()

    sections: list[SectionResultV1] = []
    for raw in result_dict.get("sections", []):
        try:
            sections.append(SectionResultV1.model_validate(raw))
        except Exception:  # noqa: BLE001 — full-room results have another shape
            continue

    for section in sections:
        report.sections.append(verify_section(section))

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
                        "not: AURA's output is supposed to be an adaptation "
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
            "Verify a finished AURA run against the Burden of Change "
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
