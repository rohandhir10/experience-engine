"""Prompt construction for every stage of the engine.

Each function returns a (system, user) pair for LLMClient.complete_json.
The instructions here are a direct compression of docs/SONG_DNA.md and
docs/WRITERS_ROOM.md — this module is the one place those documents'
rules become model instructions.
"""
from __future__ import annotations

import json

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

Never discuss translation. Never propose English wording. Analyze the song on \
its own terms, in its own language, the way a songwriter would break down a \
song they admire.

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
habits, signature devices), and songwriter intention (a synthesizing \
hypothesis, built from the other dimensions' evidence, about why the song is \
built the way it is).

Respond with ONLY a single JSON object matching this shape (omit no top-level \
key; use empty lists where a dimension genuinely doesn't apply to this song):

{
  "artistic_thesis": str,
  "genre_feel": str,
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


def song_dna_prompt(song: SongInput) -> tuple[str, str]:
    sections_text = "\n\n".join(f"[{s.name}]\n{s.source_text}" for s in song.sections)
    context = f"\nContext: {song.context_note}" if song.context_note else ""
    user = (
        f"Source language: {song.source_language}{context}\n\n"
        f"Full song, section by section:\n\n{sections_text}\n\n"
        "Analyze this song's artistic DNA as instructed."
    )
    return SONG_DNA_SYSTEM, user


# ---------------------------------------------------------------------------
# Writers' Room agent role briefs — condensed from docs/WRITERS_ROOM.md §2
# ---------------------------------------------------------------------------

AGENT_BRIEFS: dict[str, str] = {
    "translator": (
        "You are the Translator. Your core question: what does this line actually "
        "say, and are we keeping or knowingly departing from it? Produce a "
        "literal-anchor candidate — not meant to win, meant to be the floor "
        "everyone else departs from deliberately, not by accident."
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
        "You are the Creative Adapter — literary craft and songwriting craft "
        "merged into one voice (docs/WRITERS_ROOM_V1.md §1.2). Your core "
        "question: what is the single best way to say this line so it reads as "
        "real literary language (image, metaphor, economy) AND survives being "
        "sung once at tempo (scansion, hook, singability)? Produce one candidate "
        "that satisfies both as well as you can.\n\n"
        "You will be shown a Translator's literal-anchor candidate elsewhere in "
        "this room, but it is not shown to you here, precisely so you do not "
        "anchor on its clause structure. Do not translate clause by clause in "
        "the original's order. Read the whole passage, understand the feeling "
        "and image whole, then write it the way a native English songwriter "
        "would write that feeling from scratch — different sentence count, "
        "different clause order, different line breaks are all expected and "
        "good, not a deviation to avoid. A candidate that maps one-to-one onto "
        "the source's clauses, joined by commas in the same sequence, has "
        "failed at this job even if every word is accurate — that shape reads "
        "as translation no matter how nice the individual words are.\n\n"
        "If the two crafts genuinely pull against each other and you can't "
        "fully satisfy both, say plainly which one you favored and why, rather "
        "than settling for a candidate that's mediocre at both without saying "
        "so. Your known blind spot: with no second independent voice checking "
        "your work the way Poet and Songwriter used to check each other, you "
        "can drift toward whichever craft you personally favor, or toward "
        "quietly mirroring the source's structure because it's the easiest "
        "path, without noticing either — be honest in your confidence score "
        "specifically when you're unsure you've actually broken from the "
        "source's shape."
    ),
    "native_speaker": (
        "You are the Native Speaker. Your core question: would someone who "
        "actually grew up feeling this language ever say it this way in English "
        "— does this feel authentic, or does it feel translated? Give a gut "
        "authenticity verdict per candidate. You carry a VETO: if a candidate "
        "fails this test, say so plainly regardless of its other merits."
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
) -> tuple[str, str]:
    system = (
        AGENT_BRIEFS[agent]
        + "\n\nRespond with ONLY a JSON object: "
        '{"text": str, "leans_into": str} — text is your one candidate English '
        "line (or lines, matching the source line count); leans_into names "
        "which part of the emotional core your candidate leans into hardest."
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
) -> tuple[str, str]:
    system = (
        AGENT_BRIEFS[agent]
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
) -> tuple[str, str]:
    system = (
        AGENT_BRIEFS[agent]
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
) -> tuple[str, str]:
    system = (
        AGENT_BRIEFS[agent]
        + "\n\nRespond with ONLY a JSON object: {\"text\": str, \"leans_into\": "
        'str, "confidence": float (0-1, how confident you are this candidate '
        'captures the intended effect), "uncertainty_type": '
        '"cultural"|"authenticity"|"emotional"|"none" (if confidence is below '
        "0.7, name what kind of uncertainty is driving it; \"none\" if you're "
        "confident)}."
    )
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        f"Song DNA context:\n{_song_dna_context(dna, section_name)}\n\n"
        f"{room_memory.summary_for_prompt()}\n\n"
        "Give your one candidate now."
    )
    return system, user


_JUDGE_PRIORITY_ORDER = (
    "(1) emotional truth and specificity, (2) narrative fit against the "
    "song's arc (use the Song DNA's narrative_function for this section "
    "directly — there is no Film Critic in this room), (3) cultural "
    "integrity, (4) poetic/aesthetic craft, (5) singability/hook quality, "
    "(6) literal proximity to the source — lowest priority, a tiebreaker only."
)


def judge_triage_prompt(
    candidates: list[Candidate],
    routing_signals: RoutingSignals,
    source_text: str,
    dna: SongDNA,
    section_name: str,
    room_memory: RoomMemory,
) -> tuple[str, str]:
    system = (
        "You are the Judge, running the minimal V1 room. You have two "
        "candidates — a Translator's literal anchor and a Creative Adapter's "
        "re-expression. You alone decide whether this section can be ruled on "
        "now, or whether one or more specialist consultants "
        "(cultural_historian, native_speaker, psychologist) must weigh in "
        "first. You are given free routing signals (computed from the Song "
        "DNA and the candidates' own reported confidence) as input, not as a "
        "command — decide for yourself, but do not ignore a fired signal "
        "without a stated reason.\n\n"
        "Specifically watch for CONFLICTING INTERPRETATIONS: if the "
        "Translator's literal anchor and the Creative Adapter's candidate "
        "imply meaningfully different readings of what the line is doing "
        "emotionally, that alone is reason to consult a specialist (usually "
        "native_speaker or psychologist) even if no precomputed signal fired "
        "— this judgment is yours alone, nothing upstream can compute it for "
        "you.\n\n"
        "If you can rule now with real confidence, set ready_to_rule true and "
        "fill in ruling using the priority order " + _JUDGE_PRIORITY_ORDER + " "
        "Note that at this stage you do not yet have a Native Speaker "
        "authenticity verdict or a confirmed factual-inversion check — if you "
        "suspect either issue, that is itself a reason to consult "
        "native_speaker before ruling, not a reason to guess.\n\n"
        'Respond with ONLY a JSON object: {"ready_to_rule": bool, "ruling": '
        '{"final_line": str, "sources_used": [{"agent": str, "contribution": '
        'str}], "vetoes_applied": [str], "priority_tradeoffs_made": str, '
        '"disagreements_overruled": [{"agents": str, "disagreement": str, '
        '"ruling": str, "why": str}]} or null, "specialists_needed": '
        '["cultural_historian"|"native_speaker"|"psychologist", ...], "why": '
        'str}. If ready_to_rule is false, ruling must be null and '
        "specialists_needed must be non-empty."
    )
    candidates_text = "\n".join(
        f"[{c.id}] ({c.agent}, confidence={c.confidence:.2f}, "
        f"uncertainty={c.uncertainty_type}): {c.text}"
        for c in candidates
    )
    section = dna.section(section_name)
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        f"Song DNA — thesis: {dna.artistic_thesis}; arc shape: {dna.arc_shape}; "
        f"this section's narrative function: {section.narrative_function.function}\n\n"
        f"Candidates:\n{candidates_text}\n\n"
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
) -> tuple[str, str]:
    system = (
        "You are the Judge. You previously requested specialist input before "
        "ruling on this section; that input is now available. Apply the two "
        "hard vetoes first: if native_speaker flagged a candidate as failing "
        "authenticity, or if an issue amounts to inverting the underlying "
        "fact of the line (who did what to whom), that candidate is "
        "disqualified regardless of other merits. Among what survives, use "
        "the priority order " + _JUDGE_PRIORITY_ORDER + "\n\n"
        "You are not limited to picking one of the two candidates verbatim. "
        "If a specialist flagged a real concern (e.g. native_speaker noting a "
        "candidate still reads as translated, even short of an outright "
        "authenticity failure) and neither candidate actually resolves it, "
        "rewrite final_line yourself to address it — do not ship a line you "
        "know has a named, unresolved problem just because it was the least "
        "flawed of the two options. A specific warning sign: if both "
        "candidates mirror the source's clause order and commas rather than "
        "reading as something an English songwriter would write from "
        "scratch, that is exactly the kind of concern worth a real rewrite, "
        "not a shrug.\n\n"
        'Respond with ONLY a JSON object: {"final_line": str, "sources_used": '
        '[{"agent": str, "contribution": str}], "vetoes_applied": [str], '
        '"priority_tradeoffs_made": str, "disagreements_overruled": '
        '[{"agents": str, "disagreement": str, "ruling": str, "why": str}]}.'
    )
    candidates_text = "\n".join(f"[{c.id}] ({c.agent}): {c.text}" for c in candidates)
    critiques_text = (
        "\n".join(
            f"[{c.agent} on {c.candidate_id}] verdict={c.verdict}: "
            f"strength={c.strength} failure={c.failure}"
            for c in specialist_critiques
        )
        or "No specialists were consulted."
    )
    user = (
        f"Original ({section_name}):\n{source_text}\n\n"
        f"Song DNA — thesis: {dna.artistic_thesis}; arc shape: {dna.arc_shape}\n\n"
        f"Candidates:\n{candidates_text}\n\n"
        f"Specialist consultations:\n{critiques_text}\n\n"
        f"Routing signals: {routing_signals.summary_for_prompt()}\n\n"
        f"{room_memory.summary_for_prompt()}\n\n"
        "Render your final ruling now."
    )
    return system, user
