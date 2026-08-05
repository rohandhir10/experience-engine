"""Adapts comic dialogue bubbles through the existing V1 Writers' Room
(engine/writers_room_v1.py) — item #4 of the chapter-level-context
roadmap (docs/CAPABILITY_MATRIX.md), the first proof that ChapterDNA
(engine/chapter_dna.py) can actually drive a real adaptation, not just
sit there as an analysis nobody consumes.

The approach, stated plainly: rather than duplicating ~500 lines of
SongDNA-shaped prompt-building logic (engine/prompts.py's
_song_dna_context calls `dna.section(name)` and reads per-section
motifs/ambiguities/symbols that ChapterDNA has no equivalent of) for a
proof of concept, this wraps one bubble + the chapter's DNA into a
single-section SongDNA (_bubble_song_dna below) that the existing
Translator -> Creative Adapter -> Judge machinery already knows how to
consume unchanged. This is a real bridge, not a fabrication — every
field it fills is either a genuine ChapterDNA value or an honestly
neutral placeholder, never an invented per-bubble analysis Chapter DNA
was never asked to produce.

What this does NOT do: no batching (one full Writers' Room run per
bubble — a real chapter with dozens of bubbles means dozens of runs,
same per-section cost a song already has, just applied to much shorter
units), and no motif/ambiguity/symbol tracking (ChapterDNA has none of
these yet). Voice consistency DOES work correctly, for free: bubble
voices thread through exactly the way SectionInput.voice already does
for a song's duet/dialogue sections.

Honorific/speech-register tracking (item #6 of the chapter-level-
context roadmap) IS wired here now: `adapt_chapter` seeds
RoomMemory.honorific_state from each CharacterVoice's
honorific_register snapshot, and after every bubble attributed to a
voice, updates that character's entry from JudgeRuling.honorific_note
— the Judge's own report of that character's register after ruling on
this bubble (engine/prompts.py's `_ruling_schema` only asks for this
field when the section has an attributed voice, so unattributed
bubbles and ordinary songs are unaffected). RoomMemory.summary_for_prompt()
already surfaces the running state to every stage (Translator, Creative
Adapter, Judge) automatically, the same way it already does for
compensations — no new prompt wiring was needed beyond that field.
"""
from __future__ import annotations

import logging

from .language_profile import NEUTRAL_PROFILE, LanguageProfile
from .llm_client import LLMClient
from .models import (
    BubbleInput,
    ChapterDNA,
    ChapterInput,
    DensityItem,
    EmotionalArcPoint,
    NarrativeFunctionItem,
    RoomMemory,
    SectionProfile,
    SectionResultV1,
    SongDNA,
    StyleProfile,
)
from .verify import verify_section
from .writers_room_v1 import retry_section_with_finding, run_section

logger = logging.getLogger(__name__)


def _bubble_song_dna(dna: ChapterDNA, bubble: BubbleInput) -> SongDNA:
    """Wraps a chapter-wide ChapterDNA + one bubble into a single-section
    SongDNA — see this module's docstring for why. `tone` fills
    `poetic_register` (both are "the work's rhetorical register, a
    handful of words, not musical/visual genre" - the same axis, just
    named differently per medium); `ongoing_plot_context` fills both
    `arc_shape` and `songwriter_intention`, since a chapter's "what's
    happening" and "why it's built this way" collapse into the same
    answer for a single dramatic beat, unlike a whole song's arc.

    The single SectionProfile is an honestly neutral placeholder, not a
    real per-bubble analysis — Chapter DNA was never asked to produce
    one (see this module's docstring). `dominant_feeling` is the one
    field that gets a real value (the chapter's tone) rather than
    "unspecified", since it costs nothing and is directly known.
    """
    return SongDNA(
        artistic_thesis=dna.artistic_thesis,
        genre_feel=dna.genre_feel,
        poetic_register=dna.tone,
        arc_shape=dna.ongoing_plot_context,
        songwriter_intention=dna.ongoing_plot_context,
        turn_points=[],
        sections=[
            SectionProfile(
                name=bubble.id,
                narrative_function=NarrativeFunctionItem(
                    section=bubble.id,
                    function="dialogue",
                    relation_to_adjacent=(
                        "not analyzed — Chapter DNA is chapter-wide only, no "
                        "per-bubble breakdown exists yet"
                    ),
                ),
                density=DensityItem(
                    section=bubble.id,
                    density="moderate",
                    note="not analyzed — no per-bubble density analysis exists yet",
                ),
                emotional_arc_point=EmotionalArcPoint(
                    section=bubble.id,
                    valence=0.0,
                    intensity=0.5,
                    dominant_feeling=dna.tone,
                ),
                imagery=[],
                vulnerability=[],
                rhythm=[],
            )
        ],
        motifs=[],
        ambiguities=[],
        symbols=[],
        repetition_patterns=[],
        style=StyleProfile(
            diction_register="unspecified",
            rhyme_type="n/a — dialogue, not verse",
            syntax_tendency="unspecified",
            signature_devices=[],
        ),
    )


def adapt_bubble(
    chapter: ChapterInput,
    dna: ChapterDNA,
    bubble: BubbleInput,
    room_memory: RoomMemory,
    client: LLMClient,
    profile: LanguageProfile = NEUTRAL_PROFILE,
) -> SectionResultV1:
    """Runs ONE bubble through the same Translator -> Creative Adapter ->
    Judge room a song section already uses. `bubble.voice` threads
    through to `run_section` exactly the way `SectionInput.voice` does,
    so voice consistency across bubbles attributed to the same
    character works via the existing machinery, unmodified.
    """
    wrapped_dna = _bubble_song_dna(dna, bubble)
    return run_section(
        client,
        bubble.source_text,
        wrapped_dna,
        bubble.id,
        room_memory,
        chapter.target_language,
        bubble.voice,
        profile,
    )


def adapt_chapter(
    chapter: ChapterInput,
    dna: ChapterDNA,
    client: LLMClient,
    profile: LanguageProfile = NEUTRAL_PROFILE,
) -> list[SectionResultV1]:
    """Runs every bubble in `chapter`, in order, through adapt_bubble —
    the comics-side equivalent of engine/pipeline.py::run_engine's
    section loop. Room memory carries forward exactly the way it does
    for song sections (prior rulings, compensations), so voice
    consistency and Hindi/Japanese/etc. structural-trap compensations
    actually hold across a whole chapter, not just within one bubble —
    plus honorific/speech-register state (see this module's docstring),
    seeded here from Chapter DNA's per-character snapshot and updated
    after every attributed bubble.

    No batching (see this module's docstring): N sequential full
    Writers' Room runs, not one call handling several bubbles at once.
    """
    room_memory = RoomMemory(
        honorific_state={c.name: c.honorific_register for c in dna.characters}
    )
    results: list[SectionResultV1] = []
    known_compensations = {c.source_feature for c in room_memory.compensations}

    for bubble in chapter.bubbles:
        result = adapt_bubble(chapter, dna, bubble, room_memory, client, profile)
        result = _verify_and_correct_bubble(
            result, chapter, dna, bubble, room_memory, client, profile
        )
        results.append(result)
        room_memory.prior_rulings.append(result.ruling)
        for compensation in getattr(result, "compensations", []):
            if compensation.source_feature not in known_compensations:
                room_memory.compensations.append(compensation)
                known_compensations.add(compensation.source_feature)
        if bubble.voice and result.ruling.honorific_note:
            room_memory.honorific_state[bubble.voice] = result.ruling.honorific_note

    return results


def _verify_and_correct_bubble(
    result: SectionResultV1,
    chapter: ChapterInput,
    dna: ChapterDNA,
    bubble: BubbleInput,
    room_memory: RoomMemory,
    client: LLMClient,
    profile: LanguageProfile,
) -> SectionResultV1:
    """Verifies one adapted bubble and, on an error-severity finding,
    re-judges it once with that finding as corrective context.

    This existed for songs (engine/pipeline.py::_apply_corrective_pass)
    and was simply never wired up here, so the comics path ran with NO
    verification at all - every deterministic constitution check in
    engine/verify.py was dead code for comics. Found from a real Korean
    panel whose shipped "why" both cited wording that was not in the
    literal anchor (a ledger-integrity error) and justified itself as
    "to maintain a formal tone" (a vacuous justification). Both are
    checks verify.py already performs and never got the chance to.

    Bounded to one retry per bubble and does not re-verify its own
    output, the same discipline the song path uses for the same reason:
    an uncapped loop can oscillate with no guaranteed termination.

    Degrades rather than raises. Verification is a quality gate, not a
    correctness precondition - if it or the retry fails, the original
    ruling ships and the human reviewing the panel still sees it.
    """
    try:
        verification = verify_section(result, chapter.target_language)
        errors = verification.errors
    except Exception as exc:  # noqa: BLE001 - a broken gate must not lose the adaptation
        logger.warning("Verification failed for bubble %s: %s", bubble.id, exc)
        return result

    if not errors:
        return result

    logger.warning(
        "Bubble %s: %d verify error(s), re-judging once - %s",
        bubble.id,
        len(errors),
        "; ".join(f.law for f in errors),
    )
    try:
        return retry_section_with_finding(
            client,
            result,
            bubble.source_text,
            _bubble_song_dna(dna, bubble),
            bubble.id,
            room_memory,
            "\n".join(f"- {f.detail}" for f in errors),
            chapter.target_language,
            bubble.voice,
            profile,
        )
    except Exception as exc:  # noqa: BLE001 - keep the original ruling
        logger.warning("Corrective retry failed for bubble %s: %s", bubble.id, exc)
        return result
