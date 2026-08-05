"""Checks a corpus directory before a paid run touches it.

A benchmark run costs real money and real reviewer time, and the failures
this catches are all silent: a file that is valid JSON but missing the
field the runner reads, a one-section fragment that will be weighted like
a ten-section song in the paired tests, or — the one that actually bites
— a song whose text is not in the script its own `source_language`
claims, which is how a mislabelled or already-translated file gets into a
corpus without anyone noticing.

None of these would crash the run. They would produce a report that looks
finished and means less than it appears to.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from engine.youtube_ingest import _SCRIPT_RANGES

# Below this many sections a song is a fragment, not a work. The paired
# permutation tests weight every song equally, so a one-section entry
# carries the same influence as a full ten-section lyric while giving a
# reviewer almost nothing to judge.
MIN_SECTIONS = 3

# Below this fraction of a song's letters falling in its declared
# script, the declaration is not credible. Deliberately lenient: real
# lyrics code-switch heavily (a J-pop chorus in English, Hindi film
# lyrics with English words), so this only fires on a file that is
# substantially not the language it claims.
MIN_SCRIPT_FRACTION = 0.35

# Markers of a corpus file that was scaffolded and never filled in. Found
# for real: examples/balam_pichkari.json had nine sections every one of
# which read "REPLACE with the opening 4 lines ...". Nothing downstream
# would have objected - the engine would have dutifully adapted the
# instructions, and reviewers would have rated the result.
_PLACEHOLDER_MARKERS = ("replace with", "todo", "tk tk", "lorem ipsum", "<paste")

# Scripts written in Latin letters. A song declaring a non-Latin language
# whose text is Latin is usually romanised rather than mislabelled -
# a real input this product accepts, but one where the deterministic
# syllable grounding (engine/g2p_hi.py, g2p_ur.py) cannot run, so it
# tests a different code path than the same song in its own script.
_LATIN_CODES = {"es", "en"}


@dataclass
class CorpusReport:
    songs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        lines = [f"Corpus: {len(self.songs)} song(s) usable"]
        if self.excluded:
            lines.append(f"Excluded by .benchmarkignore: {', '.join(self.excluded)}")
        for song in self.songs:
            lines.append(f"  - {song}")
        if self.errors:
            lines.append("")
            lines.append("ERRORS (a run would be measuring something broken):")
            lines.extend(f"  ! {e}" for e in self.errors)
        if self.warnings:
            lines.append("")
            lines.append("WARNINGS (usable, but read them before paying for a run):")
            lines.extend(f"  ~ {w}" for w in self.warnings)
        if self.ok and not self.warnings:
            lines.append("")
            lines.append("No problems found.")
        return "\n".join(lines)


def script_fraction(text: str, code: str) -> float | None:
    """Fraction of `text`'s letters that fall in `code`'s script ranges,
    or None when the script isn't one this can check.

    Counts letters only — digits, punctuation and whitespace are shared
    across scripts and would dilute the signal toward whichever script
    the file happens to have more spaces in.
    """
    ranges = _SCRIPT_RANGES.get(code)
    if not ranges:
        return None
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    in_script = sum(
        1 for c in letters if any(lo <= ord(c) <= hi for lo, hi in ranges)
    )
    return in_script / len(letters)


def _language_code(song: dict) -> str | None:
    """The declared code, or a guess from the free-text language name.

    `source_language` is free text in this project ("Hindi/Punjabi
    (code-switched)"), so an exact lookup fails on most real files;
    substring matching is what actually works against the corpus that
    exists.
    """
    code = song.get("source_language_code")
    if isinstance(code, str) and code.strip():
        return code.strip().lower()

    name = (song.get("source_language") or "").lower()
    for candidate, keyword in (
        ("ja", "japanese"), ("ko", "korean"), ("hi", "hindi"),
        ("ur", "urdu"), ("es", "spanish"), ("pa", "punjabi"), ("en", "english"),
    ):
        if keyword in name:
            return candidate
    return None


def validate_corpus(corpus_dir: Path) -> CorpusReport:
    from .runner import load_exclusions

    report = CorpusReport()
    if not corpus_dir.exists():
        report.errors.append(f"{corpus_dir} does not exist")
        return report

    excluded = load_exclusions(corpus_dir)
    paths = sorted(corpus_dir.glob("*.json"))
    if not paths:
        report.errors.append(f"No song JSON files in {corpus_dir}")
        return report

    for path in paths:
        if path.stem in excluded:
            report.excluded.append(path.stem)
            continue

        try:
            song = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            report.errors.append(f"{path.name}: not readable JSON ({exc})")
            continue
        if not isinstance(song, dict):
            report.errors.append(f"{path.name}: top level is not an object")
            continue

        title = song.get("title") or path.stem
        sections = song.get("sections")
        if not isinstance(sections, list) or not sections:
            report.errors.append(f"{path.name}: no sections")
            continue

        texts = [
            s.get("source_text", "") for s in sections if isinstance(s, dict)
        ]
        if not any(t.strip() for t in texts):
            report.errors.append(f"{path.name}: every section's source_text is empty")
            continue

        joined_lower = "\n".join(texts).lower()
        placeholder_hits = [m for m in _PLACEHOLDER_MARKERS if m in joined_lower]
        if placeholder_hits:
            report.errors.append(
                f"{path.name}: contains placeholder text ({placeholder_hits[0]!r}) - "
                "this is an unfilled template, not a song. The engine would adapt the "
                "instructions and reviewers would rate the result."
            )
            continue

        report.songs.append(f"{title} ({len(sections)} sections)")

        if len(sections) < MIN_SECTIONS:
            report.warnings.append(
                f"{path.name}: only {len(sections)} section(s) - a fragment carries the "
                f"same weight as a full song in the paired tests"
            )

        code = _language_code(song)
        if code is None:
            report.warnings.append(
                f"{path.name}: could not tell which language {song.get('source_language')!r} "
                "is, so its script was not checked"
            )
            continue

        fraction = script_fraction("\n".join(texts), code)
        if fraction is None:
            continue
        if fraction >= MIN_SCRIPT_FRACTION:
            continue

        latin = script_fraction("\n".join(texts), "en") or 0.0
        if code not in _LATIN_CODES and latin >= MIN_SCRIPT_FRACTION:
            # Real lyrics, romanised. Usable, but a different code path:
            # G2P grounding needs the native script.
            report.warnings.append(
                f"{path.name}: declares {song.get('source_language')!r} but the text is "
                f"{latin:.0%} Latin letters - romanised. Usable, but deterministic "
                "syllable grounding (G2P) cannot run on it, so it does not test the "
                "same path as the same song in its own script."
            )
        else:
            report.errors.append(
                f"{path.name}: declares {song.get('source_language')!r} but only "
                f"{fraction:.0%} of its letters are in that script - mislabelled or "
                "already translated?"
            )

    return report
