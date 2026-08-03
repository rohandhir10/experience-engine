"""Byte-identical prompt regression guard.

This is the safety net for the V2 multilingual refactor
(docs/MULTILINGUAL_V2.md, Phase 1). Every prompt the engine can build is
hashed for a fixed fixture under the default (neutral) language profile.
If any refactor changes a single byte of any prompt, one of these fails.

The promise Phase 1 makes is that adding the Language Profile system
changes NOTHING until a real profile is supplied. That promise is only
worth anything if it is enforced mechanically — a human reading a diff
cannot verify "no prompt changed" across seven builders.

When a prompt is INTENTIONALLY changed, update the expected hash here in
the same commit, so the change is visible in review rather than silent.
"""
from __future__ import annotations

import hashlib

import pytest

from engine import prompts
from engine.models import (
    Candidate,
    Critique,
    RoomMemory,
    RoutingSignals,
    SectionInput,
    SongDNA,
    SongInput,
)

FIXTURE_DNA = SongDNA.model_validate(
    {
        "artistic_thesis": "Holding on can be its own form of loyalty.",
        "genre_feel": "sparse acoustic ballad",
        "poetic_register": "melancholic-intimate",
        "arc_shape": "slow ambivalence resolving into release",
        "songwriter_intention": "justify an act of letting go",
        "turn_points": [{"section": "chorus", "cause": "the drawer opens"}],
        "sections": [
            {
                "name": "verse_1",
                "narrative_function": {
                    "section": "verse_1",
                    "function": "establish the withheld object",
                    "relation_to_adjacent": "sets up the chorus turn",
                },
                "density": {"section": "verse_1", "density": "sparse", "note": "few images"},
                "emotional_arc_point": {
                    "section": "verse_1",
                    "valence": -0.3,
                    "intensity": 0.4,
                    "dominant_feeling": "guarded attachment",
                },
                "imagery": [
                    {
                        "section": "verse_1",
                        "image": "a locked drawer",
                        "sensory_channel": "tactile",
                        "stands_in_for": "a memory kept deliberately unexamined",
                    }
                ],
                "vulnerability": [
                    {
                        "section": "verse_1",
                        "what_is_admitted": "she has not moved on",
                        "directness": "buried_in_imagery",
                        "felt_cost": "admitting the years were wasted",
                    }
                ],
                "rhythm": [],
            }
        ],
        "motifs": [
            {
                "motif": "the drawer",
                "first_occurrence": "verse_1",
                "occurrences": [
                    {"section": "verse_1", "how_meaning_shifted": "introduced as closed"}
                ],
            }
        ],
        "ambiguities": [
            {
                "section": "verse_1",
                "ambiguous_element": "whether the drawer is ever opened",
                "competing_readings": ["she opens it", "she never does"],
                "is_the_ambiguity_the_point": True,
            }
        ],
        "symbols": [
            {
                "section": "verse_1",
                "symbol": "the drawer",
                "concrete_form": "a bedside drawer with a key",
                "symbolic_meaning": "withheld grief",
                "register": "archetypal",
            }
        ],
        "repetition_patterns": [],
        "style": {
            "diction_register": "plain, unliterary",
            "rhyme_type": "slant",
            "syntax_tendency": "short declaratives",
            "signature_devices": ["understatement"],
        },
    }
)

FIXTURE_SONG = SongInput(
    title="Locked Drawer",
    source_language="Hindi",
    context_note="A woman sorting a dead partner's things.",
    sections=[SectionInput(name="verse_1", source_text="मैंने दराज़ बंद रखी")],
)

FIXTURE_CANDIDATES = [
    Candidate(
        id="a1",
        agent="translator",
        text="I kept the drawer closed",
        leans_into="the literal fact",
        round="generation",
        syllable_count=6,
    ),
    Candidate(
        id="c1",
        agent="creative_adapter",
        text="The drawer stayed shut.",
        leans_into="restraint",
        confidence=0.9,
        philosophy="maximum_fidelity",
        round="generation",
        syllable_count=5,
    ),
]

FIXTURE_MEMORY = RoomMemory()
FIXTURE_SIGNALS = RoutingSignals(
    culturally_specific_symbol_count=0,
    suggested_specialists=[],
    reasons=[],
)
FIXTURE_CRITIQUES = [
    Critique(
        candidate_id="c1",
        agent="native_speaker",
        verdict="strong",
        strength="reads naturally",
        failure="",
    )
]


def _hash(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()[:16]


def _v1_prompts() -> dict[str, tuple[str, str]]:
    """Every prompt the V1 room can build, for the fixture above."""
    return {
        "song_dna": prompts.song_dna_prompt(FIXTURE_SONG),
        "generation_translator": prompts.generation_prompt_v1(
            "translator", "मैंने दराज़ बंद रखी", FIXTURE_DNA, "verse_1", FIXTURE_MEMORY
        ),
        "creative_adapter": prompts.creative_adapter_prompt(
            "मैंने दराज़ बंद रखी", FIXTURE_DNA, "verse_1", FIXTURE_MEMORY
        ),
        "judge_triage": prompts.judge_triage_prompt(
            FIXTURE_CANDIDATES,
            FIXTURE_SIGNALS,
            "मैंने दराज़ बंद रखी",
            FIXTURE_DNA,
            "verse_1",
            FIXTURE_MEMORY,
        ),
        "judge_final": prompts.judge_final_prompt(
            FIXTURE_CANDIDATES,
            FIXTURE_CRITIQUES,
            FIXTURE_SIGNALS,
            "मैंने दराज़ बंद रखी",
            FIXTURE_DNA,
            "verse_1",
            FIXTURE_MEMORY,
        ),
        "diagnosis_native_speaker": prompts.diagnosis_prompt(
            "native_speaker",
            FIXTURE_CANDIDATES,
            "मैंने दराज़ बंद रखी",
            FIXTURE_DNA,
            "verse_1",
        ),
    }


# Captured from the pre-refactor engine. A failure here means a prompt
# changed — intentional or not.
#
# creative_adapter/judge_triage/judge_final updated deliberately: added
# explicit instructions to preserve repetition count, rhetorical questions,
# metaphor/imagery, and to reject "sounds smoother/more relatable/more
# natural" as sufficient justification for dropping a source device —
# following a real production run that collapsed a triple-repeated phrase
# ("then who is right") to a single occurrence, justified exactly that way.
#
# song_dna/creative_adapter/judge_triage/judge_final updated again:
# song_dna now extracts poetic_register (the song's rhetorical/spiritual
# register, distinct from genre_feel); creative_adapter gained a 9th
# constraint requiring register-matching via the TARGET language's own
# equivalent tradition, never an untranslated source-culture reference;
# judge prompts gained a third gate, Tonal Coherence (a source metaphor
# whose concrete image survives translation but reads as unintentionally
# grotesque or literal in the target language) and reference
# poetic_register in genre_authenticity.
#
# judge_triage/judge_final updated again, following real production
# outputs showing two distinct failures the existing rules didn't cover:
# (1) the Authenticity gate now explicitly covers connotation/polarity,
# not just structural naturalness - a word choice that's structurally
# accurate but flips the source's actual emotional charge (a rejection
# reading as an endorsement, e.g. a wrong-answer buzzer landing as a
# success chime) now fails this gate even though no dictionary would
# call it wrong; (2) the Burden of Change ledger now explicitly protects
# specific/marked/thematically loaded WORDS, not just structural devices
# (repeated phrases, rhetorical questions, images) - replacing a
# deliberately loaded word ("consumption") with a safer generic synonym
# ("use") needs the same real justification dropping a repeated phrase
# would. Also fixed two pre-existing, unrelated bugs found while editing
# this text: the Tonal Coherence gate's own {target_language} placeholder
# was never actually being substituted (missing f-string prefix on two
# lines) - it had been sending the Judge the literal, unsubstituted
# string "{target_language}" since the gate was first added.
#
# generation_translator updated: a real production run on a long, highly
# repetitive qawwali section (a chanted refrain repeated ~14 times, two
# couplets each repeated twice) came back with a literal anchor that
# mentioned every image once but collapsed all the repetition down to a
# single occurrence - a summary, not a transcription. Nothing downstream
# could recover the lost repetition (the Creative Adapter/Judge only ever
# diff against this anchor), and the Creative Adapter's constraint #7
# already protects exactly this for ITS OWN output but the Translator had
# no equivalent instruction for its own literal anchor. Added one:
# render every line, in order, including exact repeats at the same count
# the source uses - devotional/chant repetition is usually the point of
# the passage, not filler to compress.
#
# creative_adapter/judge_triage/judge_final updated again: after the
# translator-anchor fix above, a real production run (Kun Faya Kun,
# Hindi -> Japanese) showed the refrain now preserved correctly, but two
# OTHER couplets that the source repeats twice each (a verse and a
# bridge) were shipped only once each in the final Japanese line -
# constraint #7 and the judge's equivalent language only mentioned a
# repeated "phrase" or "line," and the model was reading a two-line
# couplet as two individually-droppable lines rather than one repeated
# unit. All three prompts now explicitly name repeated multi-line blocks
# (a couplet, verse, or stanza the source restates verbatim) alongside
# single repeated phrases/lines, with the same burden-of-proof standard.
#
# song_dna updated again: a real production run returned poetic_register
# as a full descriptive sentence with its own reasoning ("The song uses a
# Persianized Urdu register, with vocabulary choices such as 'maula' and
# 'rangreza' that suggest a devotional and emotionally resonant tone.")
# instead of a short label - web/components/LoreStoryline.tsx interpolates
# this field verbatim into a fixed template ("This song moves in a {X}
# register"), so a sentence-length value produced garbled, doubled-up
# prose. SONG_DNA_SYSTEM now explicitly requires a short label (a handful
# of words, e.g. "sacred and devotional") and says where the reasoning
# belongs instead (per-section analysis, songwriter_intention).
#
# creative_adapter/judge_triage/judge_final updated again: a real
# production run (a reggaeton song, Spanish -> Hindi) showed an entire
# second occurrence of a call-and-response block dropped from the shipped
# line - the source restates the same setup twice, each time landing on a
# deliberately different final line/punchline (a common device in rap/
# reggaeton, distinct from the verbatim-repeat couplets tested so far).
# Constraint #7's "restates verbatim" wording didn't cover a near-repeat
# that diverges on its own ending, so the model treated the second
# occurrence as droppable. All three prompts now explicitly protect a
# call-and-response/setup-and-twist block (same lead-in, different
# landing each time) with the same burden-of-proof standard as a verbatim
# repeat - the contrast between the two endings is the device's whole
# point, so losing the second occurrence is a worse loss, not a smaller
# one.
EXPECTED_HASHES = {
    "song_dna": "a801b39c3ce19679",
    "generation_translator": "b0632fd76613a7ba",
    "creative_adapter": "60d65edb0a025127",
    "judge_triage": "a73f58003a532894",
    "judge_final": "7bdb60f54ec1cc9c",
    "diagnosis_native_speaker": "9452b56158c2d859",
}


@pytest.mark.parametrize("name", sorted(EXPECTED_HASHES))
def test_prompt_is_byte_identical(name: str):
    system, user = _v1_prompts()[name]
    assert _hash(system, user) == EXPECTED_HASHES[name], (
        f"The {name!r} prompt changed. If that was intentional, update "
        "EXPECTED_HASHES in the same commit so the change is reviewable."
    )


def test_every_v1_prompt_is_covered():
    """A new prompt builder must be added to this guard, not skipped."""
    assert set(_v1_prompts()) == set(EXPECTED_HASHES)


def test_agent_briefs_have_no_unresolved_placeholders():
    for agent in prompts.AGENT_BRIEFS:
        brief = prompts.agent_brief(agent, "English")
        assert "{" not in brief, f"{agent} brief has an unrendered placeholder"
