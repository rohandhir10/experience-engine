"""Prompt construction for every stage of the engine.

Each function returns a (system, user) pair for LLMClient.complete_json.
The instructions here are a direct compression of docs/SONG_DNA.md and
docs/WRITERS_ROOM.md — this module is the one place those documents'
rules become model instructions.
"""
from __future__ import annotations

import json
from collections import Counter

from .language_profile import LanguageProfile
from .models import (
    Candidate,
    Critique,
    Rebuttal,
    RoomMemory,
    RoutingSignals,
    SongDNA,
    SongInput,
)

# ---------------------------------------------------------------------------
# Song DNA  (docs/SONG_DNA.md)
# ---------------------------------------------------------------------------

SONG_DNA_SYSTEM = """\
You are a songwriting analyst, not a translator. Your job is to reverse-engineer \
a song's craft — not to explain what its words mean, but to describe what it is \
built to make a listener feel, and by what specific devices.

Never discuss translation. Never propose {target_language} wording. Analyze \
the song on its own terms, in its own language, the way a songwriter would \
break down a song they admire.

Cover, for the whole song and for every section: emotional arc (the shape of \
feeling over time, with turn points), imagery (concrete sensory pictures and \
what feeling each one stands in for), recurring motifs (elements that return \
and change meaning each time), ambiguity (places left deliberately open, and \
whether the openness is the point), symbolism (deeper meaning layered onto \
concrete objects/images, and whether it's archetypal, culturally specific, or \
invented for this song), vulnerability (what is being admitted, how directly \
or how guardedly, and at what emotional cost), rhythm (where lines rush or \
stretch and why), repetition (structural recurrence and its function: hook, \
hypnosis, insistence), narrative function (what job each section does: setup, \
escalation, hook, turn, release, resolution), lyrical density (sparse vs \
dense, and what that pacing does), poetic style (diction, rhyme type, syntax \
habits, signature devices), poetic register (the song's rhetorical/spiritual \
register — e.g. sacred or devotional, street or vernacular, melodramatic or \
romantic, playful, elegiac, defiant — independent of musical genre: a "sacred" \
register can carry a rock arrangement just as easily as a ballad), and \
songwriter intention (a synthesizing hypothesis, built from the other \
dimensions' evidence, about why the song is built the way it is).

poetic_register specifically MUST be a short label, a handful of words at \
most (e.g. "Persianized Urdu devotional register", "sacred and devotional", \
"street vernacular") — never a full sentence, and never one that explains \
its own reasoning ("...suggests a devotional tone" is reasoning; "sacred and \
devotional" is the label that reasoning would support). This field is shown \
to the end user verbatim inside a fixed template ("This song moves in a \
{poetic_register} register") — a sentence-length value breaks that template's \
grammar, not just its brevity. Put the reasoning, evidence, and specific \
vocabulary that led you to this label in your per-section analysis and \
songwriter_intention instead; this field is the label alone.

The "sections" array MUST contain exactly one entry per section given below, \
in the same order, using the exact section name shown in brackets — never \
fewer. This includes short or wordless sections (a vocal refrain, an "oh oh" \
hook, a single repeated line) — analyze what that section is doing musically \
and emotionally even if it has no literal semantic content; never skip a \
section because it seems too brief or non-lexical to analyze.

Respond with ONLY a single JSON object matching this shape (omit no top-level \
key; use empty lists where a dimension genuinely doesn't apply to this song):

{
  "artistic_thesis": str,
  "genre_feel": str,
  "poetic_register": str,
  "arc_shape": str,
  "songwriter_intention": str,
  "turn_points": [{"section": str, "cause": str}],
  "sections": [
    {
      "name": str,
      "narrative_function": {"section": str, "function": str, "relation_to_adjacent": str},
      "density": {"section": str, "density": "sparse|moderate|dense", "note": str},
      "emotional_arc_point": {"section": str, "valence": float, "intensity": float, "dominant_feeling": str},
      "imagery": [{"section": str, "image": str, "sensory_channel": str, "stands_in_for": str}],
      "vulnerability": [{"section": str, "what_is_admitted": str, "directness": "stated_plainly|deflected_through_humor|buried_in_imagery|undercut_by_irony", "felt_cost": str}],
      "rhythm": [{"section": str, "line": str, "scansion_note": str, "rhythmic_function": str}]
    }
  ],
  "motifs": [{"motif": str, "first_occurrence": str, "occurrences": [{"section": str, "how_meaning_shifted": str}], "resolves_or_breaks_at_end": str}],
  "ambiguities": [{"section": str, "ambiguous_element": str, "competing_readings": [str], "is_the_ambiguity_the_point": bool}],
  "symbols": [{"section": str, "symbol": str, "concrete_form": str, "symbolic_meaning": str, "register": "archetypal|culturally_specific|invented_for_this_song"}],
  "repetition_patterns": [{"repeated_element": str, "occurrences": int, "exact_or_varied": str, "craft_function": str}],
  "style": {"diction_register": str, "rhyme_type": str, "syntax_tendency": str, "signature_devices": [str]}
}
"""


def song_dna_prompt(
    song: SongInput, profile: "LanguageProfile | None" = None
) -> tuple[str, str]:
    sections_text = "\n\n".join(f"[{s.name}]\n{s.source_text}" for s in song.sections)
    context = f"\nContext: {song.context_note}" if song.context_note else ""
    # Empty string for the neutral profile, so prompts stay byte-identical
    # to the pre-V2 engine unless a real profile is supplied.
    profile_block = profile.song_dna_block() if profile else ""
    user = (
        f"Source language: {song.source_language}{context}\n"
        f"{profile_block}\n"
        f"Full song, section by section:\n\n{sections_text}\n\n"
        "Analyze this song's artistic DNA as instructed."
    )
    # A targeted replace, not .format() — SONG_DNA_SYSTEM embeds a full JSON
    # schema example full of literal {}, which .format() would misparse.
    system = SONG_DNA_SYSTEM.replace("{target_language}", song.target_language)
    return system, user


# ---------------------------------------------------------------------------
# Writers' Room agent role briefs — condensed from docs/WRITERS_ROOM.md §2
# ---------------------------------------------------------------------------

AGENT_BRIEFS: dict[str, str] = {
    "translator": (
        "You are the Translator. Your core question: what does this line actually "
        "say, and are we keeping or knowingly departing from it? Produce a "
        "literal-anchor candidate — not meant to win, meant to be the floor "
        "everyone else departs from deliberately, not by accident.\n\n"
        "This is a transcription, not a summary: render EVERY line of the "
        "source, in order, including exact repeats — a couplet, refrain, "
        "mantra, or chant that appears N times in the source must appear N "
        "times in your candidate too, even if the section is long or highly "
        "repetitive. Collapsing ten repetitions of the same line into one "
        "mention, or a twice-repeated couplet into a single occurrence, is "
        "not a more efficient literal anchor - it is a different, shorter "
        "text that everyone downstream will now (wrongly) treat as "
        "complete. Devotional or trance-inducing repetition in particular "
        "is usually the point of the passage, not filler to compress."
    ),
    "poet": (
        "You are the Poet. Your core question: what is the most powerful way to "
        "say this as literary language — image, metaphor, sound, economy? Produce "
        "a candidate optimized for language quality on its own terms, independent "
        "of pop-song convention. Your known blind spot: you can be too written, "
        "too dense to land on first hearing — don't self-censor for that here, "
        "that correction is the room's job, not yours."
    ),
    "songwriter": (
        "You are the Songwriter. Your core question: does this work as something "
        "sung — does it scan, does it hook, does it survive being heard once at "
        "tempo? Produce a candidate optimized for singability, rhythm, and hook "
        "quality. Your known blind spot: you can flatten nuance for catchiness — "
        "don't let this candidate go generic."
    ),
    "creative_adapter": (
        "You are the Creative Adapter. Your job is NOT to write the most "
        "beautiful or expressive {target_language} you can produce, and it is "
        "NOT to improve on the songwriter. The test for every candidate you "
        "write: if the original lyricist had written this song in "
        "{target_language}, would they recognize this as their own work? "
        "(docs/WRITERS_ROOM_V1.md §9, \"Burden of Change.\")\n\n"
        "THE BURDEN OF CHANGE: every word that differs from a plain literal "
        "reading of the source carries a burden of proof. You must be able to "
        "name, for every deviation, which specific problem it solves — "
        "closer natural {target_language}, a genre convention the literal "
        "wording breaks, a rhythm/performance need, a voice consistency need. "
        "'It sounds better this way' is NEVER a sufficient justification on "
        "its own. If you cannot justify a change, do not make it — revert to "
        "the plainer, more literal wording instead.\n\n"
        "Eight constraints still govern every candidate, and violating any of "
        "them costs you regardless of how well-written the result reads:\n"
        "1. Preserve the songwriter's intention — what the line is actually "
        "doing, not a more impressive idea of what it could be doing.\n"
        "2. Preserve ambiguity — a deliberately unresolved original must "
        "stay unresolved.\n"
        "3. Never introduce imagery, metaphor, or symbol not reasonably "
        "inferable from the source and Song DNA.\n"
        "4. Never intensify emotion beyond what's present in the source.\n"
        "5. Never simplify complexity the original holds.\n"
        "6. Never explain what the songwriter intentionally left implicit.\n"
        "7. Never collapse a deliberately repeated phrase, line, "
        "rhetorical question, or repeated MULTI-LINE BLOCK (a couplet, "
        "verse, or stanza the source restates verbatim, not just a single "
        "line) into fewer occurrences than the source uses. If the source "
        "says something three times, it is said three times here too — "
        "the repetition is doing insistence or hook work, not padding, and "
        "cutting it to one occurrence because 'it already made the point' "
        "or 'saying it twice reads redundant here' is exactly the failure "
        "this constraint exists to stop. A block is not exempt just "
        "because it spans more than one line — a couplet the source sings "
        "twice in a row is one repeated unit, not two independent lines "
        "you may each state once. This protection is NOT limited to "
        "word-for-word repeats: a block the source restates with the same "
        "setup but a deliberately DIFFERENT final line or punchline — a "
        "call-and-response or setup-and-twist device (same lead-in stated "
        "twice, each time landing on a different last line) — carries "
        "its meaning specifically in the contrast between the two "
        "landings. Dropping the second occurrence because it 'isn't an "
        "exact repeat' loses the twist the device exists to deliver, "
        "which is a worse loss than dropping a verbatim repeat, not a "
        "smaller one — ship both occurrences, each with its own ending "
        "intact. The same applies to a rhetorical question: it stays a "
        "question, it does not get flattened into a statement.\n"
        "8. Change the WORDING of a line only when the literal rendering "
        "would read as unnatural, foreign-sounding {target_language} — "
        "never merely to make an already-natural line sound smoother, "
        "more polished, or more 'relatable.' A human translator reading "
        "your candidate should think 'yes — that is exactly what the "
        "original author meant, just written naturally in "
        "{target_language},' not 'that's a great {target_language} "
        "lyric.' The second reaction is a warning sign that you improved "
        "on the songwriter instead of recreating their experience.\n"
        "9. Match Song DNA's poetic_register using {target_language}'s OWN "
        "equivalent tradition for that register, never the source "
        "culture's specific references left untranslated. A sacred/"
        "devotional register calls for whatever actually carries sacred "
        "weight in {target_language} — its own devotional or mystical "
        "poetic tradition, its own vocabulary for reverence and longing — "
        "not a transliterated source-language term, and not generic "
        "'poetic {target_language}' with the register flattened out. The "
        "same applies to any register: street/vernacular, melodramatic, "
        "elegiac, playful. If you genuinely don't know {target_language}'s "
        "own equivalent tradition for this register, say so in your "
        "confidence score rather than guessing at one.\n\n"
        "Generate exactly 5 candidates — one for each of these adaptation "
        "philosophies. Every philosophy is still fully bound by the burden "
        "of change and all eight constraints above; they differ in which "
        "fidelity-compatible dimension they prioritize when a real tradeoff "
        "exists, never in how much license to invent they get:\n\n"
        "- maximum_fidelity: the most literal rendering that still reads as "
        "real {target_language}. The floor, made presentable — minimal "
        "deviation from a plain reading, justified only by what "
        "{target_language} grammar requires.\n"
        "- native_english_lyricist: reads exactly like something a songwriter "
        "in this genre would write from scratch in {target_language}, still "
        "bound by every constraint above — natural idiom, not invented "
        "content.\n"
        "- performance_first: prioritizes how it lands sung — breath, hook, "
        "momentum — among options that are otherwise equally faithful.\n"
        "- emotion_first: prioritizes landing the SOURCE'S OWN emotional beat "
        "with maximum precision — not more intensely, more precisely.\n"
        "- genre_first: prioritizes matching the Song DNA's genre/style "
        "conventions as closely as possible within the same constraints.\n\n"
        "If two philosophies would converge on the same wording for this "
        "specific line, say so honestly rather than inventing an artificial "
        "difference — do not manufacture variety the source doesn't support.\n\n"
        "Your known blind spot: without a second independent voice pushing "
        "back, you can drift toward invented imagery or intensified emotion "
        "because it reads as 'better writing' — resist that pull "
        "specifically. Be honest in each candidate's confidence score when "
        "you're not sure it stayed within every constraint."
    ),
    "native_speaker": (
        "You are the Native Speaker. Your core question: would someone who "
        "actually grew up feeling this language ever say it this way in "
        "{target_language} — does this feel authentic, or does it feel "
        "translated? Give a gut authenticity verdict per candidate. You carry "
        "a VETO: if a candidate fails this test, say so plainly regardless of "
        "its other merits."
    ),
    "cultural_historian": (
        "You are the Cultural Historian. Your core question: what specific "
        "cultural, historical, generational, or religious weight does the "
        "original carry here, and did each candidate keep it, deliberately "
        "transform it, or lose it without noticing? Your known blind spot: you "
        "can over-intellectualize and push for explanatory weight that kills "
        "emotional immediacy — flag that tension explicitly when you feel it."
    ),
    "film_critic": (
        "You are the Film Critic. Your core question: what is this line doing "
        "dramatically right now in the arc of the whole song — is it a setup, "
        "escalation, release — and is the emotional volume of each candidate "
        "right for that role? Your known blind spot: you can push for more "
        "legible drama than the song's actual tone calls for."
    ),
    "psychologist": (
        "You are the Psychologist. Your core question: what is the speaker "
        "actually feeling, specifically — not 'sad' or 'happy' but the precise "
        "emotional logic — and does each candidate carry that precision or "
        "flatten it into something generic? Your known blind spot: you can "
        "over-explain psychology a good lyric should leave implicit — don't "
        "demand the candidates spell out what should stay felt."
    ),
}


def agent_brief(agent: str, target_language: str) -> str:
    """Formats an agent's brief with the current target language. Locked to
    "English" today (SongInput.target_language's default) — this is the one
    place a brief's wording is actually assembled, so a future target
    language never requires touching AGENT_BRIEFS itself.
    """
    return AGENT_BRIEFS[agent].replace("{target_language}", target_language)


def _song_dna_context(dna: SongDNA, section_name: str) -> str:
    section = dna.section(section_name)
    return json.dumps(
        {
            "artistic_thesis": dna.artistic_thesis,
            "arc_shape": dna.arc_shape,
            "songwriter_intention": dna.songwriter_intention,
            "style": dna.style.model_dump(),
            "this_section": section.model_dump(),
            "motifs_touching_this_section": [
                m.model_dump()
                for m in dna.motifs
                if m.first_occurrence == section_name
                or any(o.section == section_name for o in m.occurrences)
            ],
            "ambiguities_in_this_section": [
                a.model_dump() for a in dna.ambiguities if a.section == section_name
            ],
            "symbols_in_this_section": [
                s.model_dump(by_alias=True) for s in dna.symbols if s.section == section_name
            ],
        },
        indent=2,
    )


def generation_prompt(
    agent: str,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str = "English",
) -> tuple[str, str]:
    system = (
        agent_brief(agent, target_language)
        + "\n\nRespond with ONLY a JSON object: "
        '{"text": str, "leans_into": str} — text is your one candidate '
        f"{target_language} line (or lines, matching the source line count); "
        "leans_into names which part of the emotional core your candidate "
        "leans into hardest."
    )
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        f"Song DNA context:\n{_song_dna_context(dna, section_name)}\n\n"
        f"{room_memory.summary_for_prompt()}\n\n"
        "Give your one candidate now."
    )
    return system, user


def diagnosis_prompt(
    agent: str,
    candidates: list[Candidate],
    source_text: str,
    dna: SongDNA,
    section_name: str,
    target_language: str = "English",
) -> tuple[str, str]:
    system = (
        agent_brief(agent, target_language)
        + "\n\nYou are reviewing all candidates independently — you have not "
        "seen any other diagnostic agent's critique. Comment ONLY from your "
        "own expertise; do not comment on dimensions outside your lens (e.g. "
        "the Psychologist should not comment on scansion).\n\n"
        'Respond with ONLY a JSON object: {"critiques": [{"candidate_id": str, '
        '"verdict": "strong|workable|fails", "strength": str, "failure": str, '
        '"suggested_fix": str or null}]} — one critique per candidate given.'
    )
    candidates_text = "\n".join(f"[{c.id}] ({c.agent}): {c.text}" for c in candidates)
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        f"Song DNA context:\n{_song_dna_context(dna, section_name)}\n\n"
        f"Candidates to review:\n{candidates_text}\n\n"
        "Give your critique of every candidate now."
    )
    return system, user


def cross_critique_prompt(
    agent: str,
    candidates: list[Candidate],
    critiques: list[Critique],
    dna: SongDNA,
    section_name: str,
    target_language: str = "English",
) -> tuple[str, str]:
    system = (
        agent_brief(agent, target_language)
        + "\n\nYou now see every candidate and every critique from the room, "
        "including critiques of your own contribution and, if you are a "
        "diagnostic agent, other diagnostic agents' critiques. You get "
        "exactly one rebuttal turn. If you are a generative agent whose "
        "candidate was critiqued: concede, defend, or propose one specific "
        "revision. If you are a diagnostic agent and another diagnostic "
        "agent's critique genuinely conflicts with your own expertise's "
        "read: say so plainly, do not soften it into agreement.\n\n"
        'Respond with ONLY a JSON object: {"rebuttals": [{"target_agent": str, '
        '"about_candidate_id": str or null, "text": str}]} — as many '
        "rebuttals as you actually have something to say about; an empty "
        "list is fine if you have no rebuttal."
    )
    candidates_text = "\n".join(f"[{c.id}] ({c.agent}): {c.text}" for c in candidates)
    critiques_text = "\n".join(
        f"[{c.agent} on {c.candidate_id}] verdict={c.verdict}: {c.failure}"
        for c in critiques
    )
    user = (
        f"Song DNA thesis: {dna.artistic_thesis}\n\n"
        f"Candidates:\n{candidates_text}\n\n"
        f"Critiques so far:\n{critiques_text}\n\n"
        "Give your one rebuttal pass now."
    )
    return system, user


def recombination_prompt(
    candidates: list[Candidate],
    critiques: list[Critique],
    rebuttals: list[Rebuttal],
    source_text: str,
    dna: SongDNA,
    section_name: str,
) -> tuple[str, str]:
    system = (
        "You are the Songwriter, now doing a recombination pass. Given the "
        "full critique and rebuttal transcript, produce one or two revised "
        "candidates that deliberately incorporate specific, fixable feedback "
        "from the room — grafting strengths from different candidates "
        "together rather than just picking one. This is a genuine rewrite "
        "pass; new phrasing is expected.\n\n"
        'Respond with ONLY a JSON object: {"candidates": [{"text": str, '
        '"leans_into": str, "rationale": str}]}.'
    )
    candidates_text = "\n".join(f"[{c.id}] ({c.agent}): {c.text}" for c in candidates)
    critiques_text = "\n".join(
        f"[{c.agent} on {c.candidate_id}] verdict={c.verdict}: {c.failure}"
        + (f" Fix: {c.suggested_fix}" if c.suggested_fix else "")
        for c in critiques
    )
    rebuttals_text = "\n".join(
        f"[{r.responding_agent} -> {r.target_agent}]: {r.text}" for r in rebuttals
    )
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        f"Song DNA thesis: {dna.artistic_thesis}\n\n"
        f"Round 1 candidates:\n{candidates_text}\n\n"
        f"Critiques:\n{critiques_text}\n\n"
        f"Rebuttals:\n{rebuttals_text}\n\n"
        "Produce your recombined candidate(s) now."
    )
    return system, user


def judge_prompt(
    all_candidates: list[Candidate],
    critiques: list[Critique],
    rebuttals: list[Rebuttal],
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
) -> tuple[str, str]:
    system = (
        "You are the Judge. You are not a vote-counter or an averager — you "
        "make the final, binding creative decision for this section and must "
        "produce an auditable rationale.\n\n"
        "Check two hard vetoes first, in order:\n"
        "1. Did the Native Speaker call any candidate a failure on "
        "authenticity? If so it is disqualified regardless of other merits.\n"
        "2. Did the Translator flag any candidate as inverting the "
        "underlying fact of the line (who did what to whom)? If so it is "
        "disqualified.\n\n"
        "Among surviving candidates, decide using this priority order, "
        "matching the mission of emotional recreation over linguistic "
        "accuracy: (1) emotional truth and specificity, (2) narrative fit "
        "within the song's arc, (3) cultural integrity, (4) poetic/aesthetic "
        "craft, (5) singability/hook quality, (6) literal proximity to the "
        "source — lowest priority, a tiebreaker only.\n\n"
        "You may select a candidate as-is, or make a small final edit "
        "yourself if it clearly improves the winning candidate without "
        "introducing a new creative direction the room never debated.\n\n"
        'Respond with ONLY a JSON object: {"final_line": str, "sources_used": '
        '[{"agent": str, "contribution": str}], "vetoes_applied": [str], '
        '"priority_tradeoffs_made": str, "disagreements_overruled": '
        '[{"agents": str, "disagreement": str, "ruling": str, "why": str}]}.'
    )
    candidates_text = "\n".join(
        f"[{c.id}] ({c.agent}): {c.text}" for c in all_candidates
    )
    critiques_text = "\n".join(
        f"[{c.agent} on {c.candidate_id}] verdict={c.verdict}: "
        f"strength={c.strength} failure={c.failure}"
        for c in critiques
    )
    rebuttals_text = "\n".join(
        f"[{r.responding_agent} -> {r.target_agent}]: {r.text}" for r in rebuttals
    )
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        f"Song DNA — thesis: {dna.artistic_thesis}; arc shape: {dna.arc_shape}; "
        f"intention: {dna.songwriter_intention}\n\n"
        f"All candidates:\n{candidates_text}\n\n"
        f"Critiques:\n{critiques_text}\n\n"
        f"Rebuttals:\n{rebuttals_text}\n\n"
        f"{room_memory.summary_for_prompt()}\n\n"
        "Render your ruling now."
    )
    return system, user


# ---------------------------------------------------------------------------
# V1 minimal room  (docs/WRITERS_ROOM_V1.md)
# ---------------------------------------------------------------------------


def generation_prompt_v1(
    agent: str,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str = "English",
    voice: str | None = None,
    profile: LanguageProfile | None = None,
) -> tuple[str, str]:
    wants_compensations = bool(
        profile and agent == "translator" and profile.structural_traps
    )
    compensation_field = (
        ', "compensations": [{"source_feature": str, "what_it_encodes": str, '
        '"english_carrier": str, "carried": bool}] (ONLY for things the '
        "source encodes that English has no channel for — the traps listed "
        "above. For each, name the English channel that will carry the same "
        "effect: diction, sentence length, contraction level, formality of "
        "vocabulary, how much is left unsaid. The carrier must be a REGISTER "
        "the line is written in, never extra words bolted on to signal it — "
        "adding an adjective to convey bluntness is invention, not "
        "compensation. Set carried=false and say so where English genuinely "
        "cannot carry it. Omit the list if the source encodes nothing of the "
        "kind. This is decided ONCE for the song and becomes binding.)"
        if wants_compensations
        else ""
    )
    system = (
        agent_brief(agent, target_language)
        + (profile.translator_block() if profile and agent == "translator" else "")
        + "\n\nRespond with ONLY a JSON object: {\"text\": str, \"leans_into\": "
        'str, "confidence": float (0-1, how confident you are this candidate '
        'captures the intended effect), "uncertainty_type": '
        '"cultural"|"authenticity"|"emotional"|"none" (if confidence is below '
        "0.7, name what kind of uncertainty is driving it; \"none\" if you're "
        "confident)" + compensation_field + "}."
    )
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        + _voice_line(voice)
        + f"Song DNA context:\n{_song_dna_context(dna, section_name)}\n\n"
        f"{room_memory.summary_for_prompt()}\n\n"
        "Give your one candidate now."
    )
    return system, user


def _voice_line(voice: str | None) -> str:
    """One prompt line attributing this section to a named voice, when the
    work has more than one (duets, dialogue). Empty string when unattributed
    so single-voice prompts are byte-identical to before the field existed.
    """
    if not voice:
        return ""
    return (
        f"Voice for this section: {voice}. Stay consistent with what THIS "
        "voice has already established in prior sections — different voices "
        "in the same work are allowed to sound different from each other.\n\n"
    )


def _repeated_source_lines_note(source_text: str) -> str:
    """Deterministically counts verbatim-repeated lines in `source_text`
    and, if any exist, hands the exact count back as a concrete fact —
    rather than trusting the model to notice and count a repeat on its
    own while also holding constraint #7's abstract rule in mind. Same
    technique this module already uses elsewhere (Song DNA context,
    room memory): compute what's checkable in code, state it as a fact,
    and let the model's job be following the instruction rather than
    also doing the counting.

    Returns "" when the source has no verbatim-repeated line — byte-
    identical to the prompt before this note existed, so a section with
    no repetition to protect sees no change at all (confirmed by
    tests/test_golden_prompts.py's fixture, which has none).
    """
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    counts = Counter(line.lower() for line in lines)
    repeated = [(line, counts[line.lower()]) for line in dict.fromkeys(lines) if counts[line.lower()] >= 2]
    if not repeated:
        return ""
    listed = "; ".join(f"{text!r} appears {count} times" for text, count in repeated)
    return (
        "\n\nMechanical count, not a stylistic note: the source repeats the "
        f"following line(s) verbatim — your candidate must include each at "
        f"the SAME count, not fewer: {listed}. Dropping any of these "
        "occurrences is exactly the failure constraint #7 above exists to "
        "stop."
    )


def creative_adapter_prompt(
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str = "English",
    voice: str | None = None,
    profile: LanguageProfile | None = None,
) -> tuple[str, str]:
    """The Creative Adapter's call, producing exactly 5 candidates — one per
    named adaptation philosophy — in one shot (docs/WRITERS_ROOM_V1.md §9,
    "Burden of Change"). Philosophies differ in which fidelity-compatible
    dimension they prioritize, never in how much license to invent.
    """
    system = (
        agent_brief("creative_adapter", target_language)
        + (profile.anchor_block() if profile else "")
        + "\n\nRespond with ONLY a JSON object: {\"candidates\": [{\"text\": "
        'str, "philosophy": "maximum_fidelity"|"native_english_lyricist"|'
        '"performance_first"|"emotion_first"|"genre_first", "leans_into": '
        'str, "confidence": float (0-1, how confident you are this candidate '
        "stayed within every constraint), \"uncertainty_type\": "
        '"cultural"|"authenticity"|"emotional"|"none" (if confidence is below '
        "0.7, name what kind of uncertainty is driving it; \"none\" if "
        "you're confident)}, ... exactly 5 items, one per philosophy, in "
        "the order listed above]}."
    )
    user = (
        f"Original ({section_name}):\n{source_text}"
        + _repeated_source_lines_note(source_text)
        + "\n\n"
        + _voice_line(voice)
        + f"Song DNA context:\n{_song_dna_context(dna, section_name)}\n\n"
        f"{room_memory.summary_for_prompt()}\n\n"
        "Give your 5 candidates now, one per philosophy."
    )
    return system, user


def _judge_core_question(target_language: str) -> str:
    return (
        "The test for every ruling is not 'which candidate is most "
        f"beautiful' — it is: if the original lyricist had written this "
        f"song in {target_language}, would they recognize this as their "
        "own work? (docs/WRITERS_ROOM_V1.md §9, \"Burden of Change.\") "
        "Your mission is not to improve the songwriter. It is to recreate "
        "their experience.\n\n"
        "Preserve, by default, not as an afterthought: a metaphor or image "
        "that already works (if the source shows a feeling through an "
        "image, keep the image — don't explain what it means instead), "
        "emotional intensity at the level the source actually chose "
        "(neither softened nor amplified), ambiguity the source left open "
        "(resolving it is a loss, not a clarification), a rhetorical "
        "question AS a question, and a phrase or line the source "
        "deliberately repeats — the same number of times, not fewer. "
        "Change the WORDING only when the literal rendering would read as "
        f"unnatural, foreign-sounding {target_language} — never to make an "
        "already-natural line sound smoother, more polished, or more "
        "'relatable.' A human translator reading final_line should think "
        "'yes — that is exactly what the original author meant, just "
        f"written naturally in {target_language}' — not 'that's a great "
        f"{target_language} lyric.' The second reaction is a warning sign, "
        "not a compliment: it means the winning candidate improved on the "
        "songwriter instead of recreating their experience."
    )


def _judge_gates_and_dimensions(target_language: str) -> str:
    return (
    "Three GATES apply before anything else, pass/fail, not scored:\n"
    "- Literal Accuracy: did this candidate invert who-did-what-to-whom? If "
    "so, disqualified regardless of everything else.\n"
    "- Authenticity: would a native speaker actually say this, or does it "
    "read as translated? This covers connotation, not just structure: an "
    "interjection, sound-word, or slang term must carry the same emotional "
    "charge and polarity a native speaker would actually hear it as - "
    "mocking vs. celebratory, dismissal vs. affirmation, a wrong-answer "
    "buzzer vs. a success chime. A word choice that is structurally "
    "accurate but flips the source's actual charge (a rejection landing "
    "as an endorsement, an insult landing as a compliment) is exactly the "
    "kind of failure that reads as translated, even when no dictionary "
    "would call it wrong - dictionary-level correctness is not the bar "
    "here, how a native listener actually feels the word is. If "
    "native_speaker calls a candidate a failure on this, disqualified "
    "regardless of everything else.\n"
    "- Tonal Coherence: does a deep metaphor, sacred image, or emotionally "
    "loaded figure of speech from the source resolve, in this candidate, "
    "into something that reads as unintentionally grotesque, comedically "
    f"literal, or culturally jarring in {target_language} — the kind of "
    "image that gets a laugh, a wince, or a 'wait, what?' instead of the "
    "source's actual weight? This is not about literal accuracy (the "
    "image can be a faithful rendering of the source and still fail this "
    "gate) or about softening real intensity the source intends — a "
    "genuinely violent or visceral source image should stay visceral. It "
    "catches the specific failure where a metaphor's VEHICLE (the "
    "concrete image carrying the meaning) survives translation but its "
    "TENOR (what it actually means to a native listener) doesn't, so the "
    "surviving image now reads as literal instead of figurative. If this "
    "gate fails, disqualify the candidate and name, in your reasoning, "
    f"what metaphorical equivalent in {target_language} would carry the "
    "same weight without the unintended reading — don't just reject "
    "without saying what would have worked.\n\n"
    "Among candidates that clear all three gates, judge on five dimensions "
    "(dimension_scores must cover all five for the winner, 0-1 each):\n"
    "1. artistic_fidelity — would the lyricist recognize this as their own "
    "intention, imagery, ambiguity, and restraint? This subsumes emotional "
    "fidelity: don't score emotional truth separately, it's part of this. "
    "It also covers rhetorical form: a candidate that flattens a rhetorical "
    "question into a statement, or collapses a phrase — or a whole couplet/"
    "verse/stanza the source restates verbatim more than once — down to "
    "fewer occurrences than the source uses, has NOT earned equal marks "
    "just because it reads more smoothly, tighter, or less redundant — "
    "that is exactly the failure this dimension exists to catch, not a "
    "stylistic improvement. A multi-line repeated block is one repeated "
    "unit, not several lines each individually allowed to appear once. "
    "This also covers a call-and-response/setup-and-twist block — the "
    "same lead-in the source restates with a deliberately DIFFERENT final "
    "line each time — dropping the second occurrence because it isn't a "
    "word-for-word repeat loses the contrast the device exists to "
    "deliver, which is a worse loss than dropping a verbatim repeat.\n"
    "2. genre_authenticity — does this read as a real lyric in this genre/"
    f"tradition and poetic register (per Song DNA's genre_feel/"
    f"poetic_register/style), using {target_language}'s own equivalent "
    f"tradition for that register rather than generic 'poetic "
    f"{target_language}' or an untranslated source-culture reference?\n"
    f"3. natural_target_language — is it fluent, unstilted {target_language}, "
    "independent of fidelity? A faithful candidate can still read clunky; "
    "score that here, not by inflating or deflating artistic_fidelity.\n"
    "4. voice_consistency — does it match the established narrator/"
    "character voice and prior decisions already made this song (room "
    "memory)? When sections are attributed to different named voices, "
    "consistency applies WITHIN each voice — two different singers are "
    "allowed, and often required, to sound different from each other.\n"
    "5. singability_rhythm — does it scan/perform, and does it keep the "
    "source's actual rhythmic character (rushed vs. held), not just "
    "singability in the abstract?\n\n"
    "THE BURDEN OF CHANGE, made mechanical: for the winning candidate, "
    "diff it against the Translator's literal anchor and produce one "
    "`deviations` entry per fragment that differs meaningfully, each with a "
    "specific justification tied to one of the five dimensions above. "
    "'Sounds smoother,' 'reads more naturally,' or 'feels more relatable' "
    "are NOT, by themselves, real justifications for dropping a source "
    "device (a repeated phrase, a repeated multi-line couplet/verse/"
    "stanza, a call-and-response block whose repeated setup lands on a "
    "different final line each time, a rhetorical question, a working "
    "image) OR "
    "for replacing a specific, marked, or thematically loaded word with a "
    "safer, more generic synonym. A word the source chose deliberately for "
    "its particular weight - 'consumption' for something used up and "
    "discarded, not just 'used'; 'scraps' for what's left after being "
    "stolen from, not just 'left' - loses exactly what made the line worth "
    "writing that way when it's flattened to the blander synonym, even "
    "though nothing was literally deleted and the sentence still parses "
    "fine. Treat this the same as dropping a repeated phrase: it needs a "
    "real, specific reason (rhythm, rhyme, a genuine unnaturalness in "
    f"{target_language}), not 'the plainer word reads better.' — "
    "they explain why a line is easier, not why the change earns its "
    "place. If the literal wording is genuinely unnatural, name "
    "specifically what fails about it (a syntax construction, an idiom, a "
    "false cognate) — not just that a smoother alternative exists. If "
    "you cannot write a real justification for a fragment's deviation — "
    "not 'it sounds better,' an actual reason tied to a dimension — do not "
    "let that deviation stand: revise final_line to use the more literal "
    "wording for that fragment instead of shipping an unjustified change. "
    "An empty or near-empty deviations list is a GOOD sign, not a sign you "
    "did too little work — it means the winning candidate mostly agrees "
    "with the literal anchor, which is what fidelity should usually look "
    "like. Do not manufacture deviations to look thorough."
)

_RULING_SCHEMA = (
    '{"final_line": str, "sources_used": [{"agent": str, "contribution": '
    'str}], "vetoes_applied": [str], "deviations": [{"fragment_original": '
    'str, "fragment_adapted": str, "justification": str, "dimension": '
    '"artistic_fidelity"|"genre_authenticity"|"natural_target_language"|'
    '"voice_consistency"|"singability_rhythm"}], "dimension_scores": '
    '[{"dimension": "artistic_fidelity"|"genre_authenticity"|'
    '"natural_target_language"|"voice_consistency"|"singability_rhythm", "score": '
    'float, "note": str}, ... all five], "invention_penalty": float (0-1: '
    '0 if no deviation anywhere in the candidate set leaned on a weak or '
    'borderline justification, higher the more of the deviation ledger '
    'relied on "sounds better" reasoning rather than a real, specific '
    'reason), "motif_renderings": {motif: "the exact rendered phrase this '
    'ruling used for that motif", ... one entry per Song DNA motif that '
    "appears in this section — this is how later sections keep a recurring "
    "phrase's wording IDENTICAL rather than paraphrasing it, so record the "
    'phrase exactly as it appears in final_line}, '
    '"priority_tradeoffs_made": str, "disagreements_overruled": '
    '[{"agents": str, "disagreement": str, "ruling": str, "why": str}]}'
)


_CULTURAL_ANCHORS_FIELD = (
    ', "cultural_anchors": [{"term": str, "disposition": "preserve"|'
    '"preserve_with_gloss"|"adapt"|"translate_plainly", "rationale": str}] '
    "(one entry per culturally dense term that actually appears in THIS "
    "section — omit the list entirely if none do. Whatever you choose must "
    "be used identically at every recurrence of that term in the song)"
)


def _ruling_schema(profile: LanguageProfile | None = None) -> str:
    """The ruling schema, plus the cultural-anchor field only when the
    source language actually has an anchor lexicon. Asking every song to
    reason about culturally dense terms when none are known would spend
    Judge attention on nothing — and would break the Phase 1 guarantee
    that a neutral profile leaves prompts byte-identical.
    """
    if profile and profile.anchor_lexicon:
        return _RULING_SCHEMA[:-1] + _CULTURAL_ANCHORS_FIELD + "}"
    return _RULING_SCHEMA


def judge_triage_prompt(
    candidates: list[Candidate],
    routing_signals: RoutingSignals,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str = "English",
    source_syllables: int | None = None,
    voice: str | None = None,
    profile: LanguageProfile | None = None,
) -> tuple[str, str]:
    system = (
        "You are the Judge, running the minimal V1 room. You have a "
        "Translator's literal anchor plus 5 candidates from the Creative "
        "Adapter, one per adaptation philosophy. Each candidate's "
        "syllable_count below is computed deterministically (a real G2P/"
        "dictionary-based count, not a model guess) — use it as actual "
        "grounding for the singability_rhythm dimension instead of an "
        "unverified opinion; a source_syllable_estimate is given when "
        "available as a rough reference point for how much may need to "
        "compress or expand to stay singable, not a hard target.\n\n"
        + _judge_core_question(target_language) + "\n\n"
        + _judge_gates_and_dimensions(target_language)
        + (profile.constitution_block() if profile else "")
        + "\n\n"
        "You alone decide whether this section can be ruled on now, or "
        "whether one or more specialist consultants (cultural_historian, "
        "native_speaker, psychologist) must weigh in first — they exist "
        "specifically to arbitrate contested entries in the deviation "
        "ledger, not to give generic critique. You are given free routing "
        "signals (computed from the Song DNA and the candidates' own "
        "reported confidence) as input, not as a command — decide for "
        "yourself, but do not ignore a fired signal without a stated "
        "reason.\n\n"
        "Specifically watch for CONFLICTING INTERPRETATIONS: if candidates "
        "imply meaningfully different readings of what the line is doing, "
        "that alone is reason to consult a specialist even if no "
        "precomputed signal fired — this judgment is yours alone.\n\n"
        "If you can rule now with real confidence, set ready_to_rule true "
        "and fill in ruling as specified below. Note that at this stage you "
        "do not yet have a Native Speaker authenticity verdict or a "
        "confirmed factual-inversion check — if you suspect either issue, "
        "that is itself a reason to consult native_speaker before ruling, "
        "not a reason to guess.\n\n"
        'Respond with ONLY a JSON object: {"ready_to_rule": bool, "ruling": '
        + _ruling_schema(profile) + ' or null, "specialists_needed": '
        '["cultural_historian"|"native_speaker"|"psychologist", ...], "why": '
        'str}. If ready_to_rule is false, ruling must be null and '
        "specialists_needed must be non-empty."
    )
    candidates_text = "\n".join(
        f"[{c.id}] ({c.agent}"
        + (f", philosophy={c.philosophy}" if c.philosophy else "")
        + f", confidence={c.confidence:.2f}, uncertainty={c.uncertainty_type}"
        + (f", syllable_count={c.syllable_count}" if c.syllable_count is not None else "")
        + f"): {c.text}"
        for c in candidates
    )
    syllable_reference = (
        f"Source syllable estimate (rough, computed only because the source "
        f"is Latin-script/transliterated): {source_syllables}\n\n"
        if source_syllables is not None
        else ""
    )
    section = dna.section(section_name)
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        + _voice_line(voice)
        + f"Song DNA — thesis: {dna.artistic_thesis}; arc shape: {dna.arc_shape}; "
        f"this section's narrative function: {section.narrative_function.function}\n\n"
        f"Candidates:\n{candidates_text}\n\n"
        f"{syllable_reference}"
        "Routing signals (free, computed from Song DNA + candidate self-"
        f"reports):\n{routing_signals.summary_for_prompt()}\n\n"
        f"{room_memory.summary_for_prompt()}\n\n"
        "Decide now."
    )
    return system, user


def judge_final_prompt(
    candidates: list[Candidate],
    specialist_critiques: list[Critique],
    routing_signals: RoutingSignals,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
    target_language: str = "English",
    source_syllables: int | None = None,
    voice: str | None = None,
    profile: LanguageProfile | None = None,
) -> tuple[str, str]:
    system = (
        "You are the Judge. You previously requested specialist input before "
        "ruling on this section; that input is now available. You are "
        "choosing among a Translator's literal anchor plus 5 Creative "
        "Adapter candidates, one per adaptation philosophy. Each "
        "candidate's syllable_count is computed deterministically (real "
        "G2P/dictionary-based, not a guess) — ground singability_rhythm in "
        "that instead of an unverified opinion. "
        + _judge_core_question(target_language) + "\n\n"
        + _judge_gates_and_dimensions(target_language)
        + (profile.constitution_block() if profile else "")
        + "\n\n"
        "You are not limited to picking one candidate verbatim. If a "
        "specialist flagged a real concern and no candidate actually "
        "resolves it, rewrite final_line yourself to address it — do not "
        "ship a line you know has a named, unresolved problem just because "
        "it was the least flawed option available. A specific warning sign: "
        "if the surviving candidates mirror the source's clause order and "
        f"commas rather than reading as something a {target_language} "
        "songwriter would write from scratch, or if they add imagery/"
        "intensity beyond the source to compensate for feeling 'plain', "
        "that is exactly the kind of concern worth a real rewrite, not a "
        "shrug — and either way, the deviation ledger for whatever you ship "
        "must still hold up.\n\n"
        f"Respond with ONLY a JSON object: {_ruling_schema(profile)}."
    )
    candidates_text = "\n".join(
        f"[{c.id}] ({c.agent}"
        + (f", philosophy={c.philosophy}" if c.philosophy else "")
        + (f", syllable_count={c.syllable_count}" if c.syllable_count is not None else "")
        + f"): {c.text}"
        for c in candidates
    )
    critiques_text = (
        "\n".join(
            f"[{c.agent} on {c.candidate_id}] verdict={c.verdict}: "
            f"strength={c.strength} failure={c.failure}"
            for c in specialist_critiques
        )
        or "No specialists were consulted."
    )
    syllable_reference = (
        f"Source syllable estimate (rough, computed only because the source "
        f"is Latin-script/transliterated): {source_syllables}\n\n"
        if source_syllables is not None
        else ""
    )
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        + _voice_line(voice)
        + f"Song DNA — thesis: {dna.artistic_thesis}; arc shape: {dna.arc_shape}\n\n"
        f"Candidates:\n{candidates_text}\n\n"
        f"Specialist consultations:\n{critiques_text}\n\n"
        f"{syllable_reference}"
        f"Routing signals: {routing_signals.summary_for_prompt()}\n\n"
        f"{room_memory.summary_for_prompt()}\n\n"
        "Render your final ruling now."
    )
    return system, user
