"""Language Profiles (docs/MULTILINGUAL_V2.md §7).

A profile carries **only what is genuinely unique to one source
language**. Everything universal — the six constitution laws, the five
scored dimensions, the five adaptation philosophies, the agent roster —
stays in the shared prompts and is identical in every language.

The load-bearing design decision is the **neutral default**: a profile
whose every field is empty. Every prompt renders profile content through
helpers that return "" for empty fields, so a song with no profile
produces prompts byte-identical to the pre-V2 engine. That is what makes
Phase 1 safe, and tests/test_golden_prompts.py enforces it mechanically.

Profiles are data (engine/profiles/*.json), not code, so a linguist can
correct one without touching Python.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

PROFILE_DIR = Path(
    os.environ.get("CASTIA_PROFILE_DIR", Path(__file__).parent / "profiles")
)


class CulturalAnchorEntry(BaseModel):
    """A culturally dense term the Judge may need to decide about
    (docs/MULTILINGUAL_V2.md §6). A hint source, never the decision —
    the Judge still rules, using Song DNA and rhythmic fit alongside this.
    """

    term: str
    meaning: str
    # How much currency the term already has in the target language.
    # "high" (saudade, hygge) argues for preserving it untranslated;
    # "none" (pasoori) argues for a gloss or an adaptation.
    target_recognizability: str = "none"


class LanguageProfile(BaseModel):
    code: str = ""
    name: str = ""
    scripts: list[str] = Field(default_factory=list)

    # --- Song DNA guidance: the four fields that need tradition
    # knowledge to fill well (docs/MULTILINGUAL_V2.md §1). ---
    genre_traditions: str = ""
    register_axis: str = ""
    rhyme_convention: str = ""
    symbol_calibration: str = ""

    # --- Translator: grammar that silently loses information in English.
    structural_traps: list[str] = Field(default_factory=list)

    # --- Constitution calibration. The LAW TEXT never changes; these
    # only tell the Judge where this tradition's baseline sits. ---
    grammatical_scaffolding_note: str = ""  # Law 3, Compression Floor
    emotional_baseline: str = ""  # Law 4, Restraint Ceiling

    # --- Grounding + routing ---
    grounding_language_code: str = ""  # key into engine.grounding
    cultural_density_baseline: int | None = None

    anchor_lexicon: list[CulturalAnchorEntry] = Field(default_factory=list)

    @property
    def is_neutral(self) -> bool:
        """True for the default profile — no language-specific content, so
        every prompt block renders empty and behavior is pre-V2 exactly.
        """
        return not any(
            [
                self.genre_traditions,
                self.register_axis,
                self.rhyme_convention,
                self.symbol_calibration,
                self.structural_traps,
                self.grammatical_scaffolding_note,
                self.emotional_baseline,
                self.anchor_lexicon,
            ]
        )

    # --- Prompt fragments. Each returns "" when its data is absent, the
    # same pattern _voice_line() already uses for optional voice. ---

    def song_dna_block(self) -> str:
        parts = []
        if self.genre_traditions:
            parts.append(f"- Genre traditions: {self.genre_traditions}")
        if self.register_axis:
            parts.append(f"- Register axis: {self.register_axis}")
        if self.rhyme_convention:
            parts.append(f"- Rhyme convention: {self.rhyme_convention}")
        if self.symbol_calibration:
            parts.append(f"- Symbol calibration: {self.symbol_calibration}")
        if not parts:
            return ""
        return (
            f"\nWhat is specific to {self.name} — use this when filling "
            "genre_feel, style.rhyme_type, style.diction_register, and "
            "symbols[].register. Note that symbol register is judged "
            "relative to THIS tradition, not to an English reader:\n"
            + "\n".join(parts)
            + "\n"
        )

    def translator_block(self) -> str:
        if not self.structural_traps:
            return ""
        traps = "\n".join(f"- {t}" for t in self.structural_traps)
        return (
            f"\n{self.name} encodes things English does not, and dropping "
            "them silently is the failure mode to avoid here. Where the "
            "source leaves something grammatically implicit that English "
            "forces you to make explicit, say so in leans_into rather than "
            f"choosing one reading as though it were stated:\n{traps}\n"
        )

    def constitution_block(self) -> str:
        parts = []
        if self.grammatical_scaffolding_note:
            parts.append(
                "- Compression Floor (Law 3): connectives required for "
                "grammaticality are exempt; connectives that only explain "
                "an implicit relationship are not. For this source "
                f"language: {self.grammatical_scaffolding_note}"
            )
        if self.emotional_baseline:
            parts.append(
                "- Restraint Ceiling (Law 4): the ceiling is measured from "
                "this tradition's own baseline, not from a neutral one. "
                f"For {self.name}: {self.emotional_baseline}"
            )
        if not parts:
            return ""
        return (
            "\nThe laws below are unchanged; these notes only calibrate "
            "where this tradition's baseline sits:\n" + "\n".join(parts) + "\n"
        )

    def anchor_block(self) -> str:
        if not self.anchor_lexicon:
            return ""
        entries = "\n".join(
            f'- "{a.term}" ({a.meaning}) — currency in the target language: '
            f"{a.target_recognizability}"
            for a in self.anchor_lexicon
        )
        return (
            "\nCulturally dense terms known for this language. For any that "
            "appear, decide one of: preserve untranslated, preserve with a "
            "light in-line gloss, adapt to a target-language equivalent, or "
            "translate plainly. Preserve untranslated only when the term is "
            "load-bearing AND already has real currency in the target "
            "language; otherwise comprehensibility wins. Whatever you "
            "choose must be used identically at every recurrence:\n"
            + entries
            + "\n"
        )


NEUTRAL_PROFILE = LanguageProfile()

_CACHE: dict[str, LanguageProfile] = {}


def _load_all() -> dict[str, LanguageProfile]:
    if _CACHE:
        return _CACHE
    if PROFILE_DIR.exists():
        for path in sorted(PROFILE_DIR.glob("*.json")):
            profile = LanguageProfile.model_validate(json.loads(path.read_text()))
            if profile.code:
                _CACHE[profile.code.lower()] = profile
    return _CACHE


def resolve_profile(
    language_code: str | None = None, language_name: str | None = None
) -> LanguageProfile:
    """Finds a profile by code, else by a loose match on the free-text
    source_language string, else returns the neutral profile.

    Falling back to neutral is deliberate: an unknown language must
    behave exactly like the pre-V2 engine rather than half-applying
    someone else's tradition.
    """
    profiles = _load_all()
    if language_code and language_code.lower() in profiles:
        return profiles[language_code.lower()]
    if language_name:
        needle = language_name.lower()
        for profile in profiles.values():
            if profile.name and profile.name.lower() in needle:
                return profile
    return NEUTRAL_PROFILE


def available_profiles() -> list[str]:
    return sorted(_load_all())
