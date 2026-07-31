"""Deterministic routing signals for the V1 minimal Writers' Room
(docs/WRITERS_ROOM_V1.md §3).

These three signals are computed for free from data already sitting in the
SongDNA plus the two generative agents' self-reported confidence — no LLM
call is spent deciding whether a specialist *might* be relevant. The
fourth signal (conflicting interpretations between the two candidates)
cannot be computed here; it requires actually reading both candidates and
is left entirely to the Judge's own reasoning during its triage call.

The Judge still makes the actual invocation decision every time — this
module only assembles the free evidence the Judge reasons from.
"""
from __future__ import annotations

from .models import Candidate, RoutingSignals, SongDNA

CONFIDENCE_THRESHOLD = 0.7

_UNCERTAINTY_TO_SPECIALIST = {
    "cultural": "cultural_historian",
    "authenticity": "native_speaker",
    "emotional": "psychologist",
}

_GUARDED_DIRECTNESS = ("buried_in_imagery", "undercut_by_irony")


def compute_routing_signals(
    dna: SongDNA, section_name: str, candidates: list[Candidate]
) -> RoutingSignals:
    section = dna.section(section_name)
    reasons: list[str] = []
    suggested: set[str] = set()

    culturally_specific_symbols = [
        s
        for s in dna.symbols
        if s.section == section_name and s.symbol_register == "culturally_specific"
    ]
    if culturally_specific_symbols:
        suggested.add("cultural_historian")
        reasons.append(
            f"Song DNA flags {len(culturally_specific_symbols)} culturally-"
            "specific symbol(s) in this section."
        )

    deliberate_ambiguities = [
        a
        for a in dna.ambiguities
        if a.section == section_name and a.is_the_ambiguity_the_point
    ]
    if deliberate_ambiguities:
        suggested.add("psychologist")
        reasons.append(
            "Song DNA flags a deliberate ambiguity in this section that must "
            "survive, not resolve."
        )

    guarded_vulnerability = [
        v for v in section.vulnerability if v.directness in _GUARDED_DIRECTNESS
    ]
    if guarded_vulnerability:
        suggested.add("psychologist")
        reasons.append(
            "Song DNA flags vulnerability that is guarded/indirect here, at "
            "risk of being flattened or over-explained."
        )

    # One agent (creative_adapter) can now produce several candidates
    # (docs/WRITERS_ROOM_V1.md §8) — dedupe per agent so a low-confidence
    # signal is reported once, not once per stylistic variant.
    low_confidence_agents_seen: set[str] = set()
    uncertainty_reasons_seen: set[tuple[str, str]] = set()
    for c in candidates:
        if c.confidence < CONFIDENCE_THRESHOLD:
            low_confidence_agents_seen.add(c.agent)
            specialist = _UNCERTAINTY_TO_SPECIALIST.get(c.uncertainty_type)
            if specialist and (c.agent, c.uncertainty_type) not in uncertainty_reasons_seen:
                uncertainty_reasons_seen.add((c.agent, c.uncertainty_type))
                suggested.add(specialist)
                reasons.append(
                    f"{c.agent} reported low confidence on at least one "
                    f"candidate, attributed to {c.uncertainty_type} uncertainty."
                )
    low_confidence_agents = sorted(low_confidence_agents_seen)

    return RoutingSignals(
        culturally_specific_symbol_count=len(culturally_specific_symbols),
        deliberate_ambiguity_present=bool(deliberate_ambiguities),
        guarded_vulnerability_present=bool(guarded_vulnerability),
        low_confidence_agents=low_confidence_agents,
        suggested_specialists=sorted(suggested),
        reasons=reasons,
    )
