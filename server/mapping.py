"""Maps engine.pipeline.EngineResult onto the frontend's ExperienceResult
contract (web/lib/types.ts). This is a translation layer, not a change to
the engine or its prompts: the Writers' Room's internal reasoning
(deviations, dimension scores, priority tradeoffs) is written for an
engineer auditing a ruling, not a listener, so this layer's one real job
is turning that internal reasoning into one plain sentence per section
with zero implementation vocabulary - never touching engine/prompts.py.
"""
from __future__ import annotations

from engine.llm_client import LLMClient
from engine.models import SectionResultV1
from engine.pipeline import EngineResult
from engine.rhythm import count_syllables_text
from engine.verify import SYLLABLE_DELTA_WARN_RATIO

_WHY_SYSTEM = (
    "You explain, in ONE plain sentence, what a reader gains from a rewritten "
    "song lyric compared to a literal translation of it. Never use any of "
    "these words or their synonyms for internal machinery: compression, "
    "transformation, constitutional, law, dimension, fidelity, invention, "
    "deviation, adapter, judge, philosophy, artistic, engine. Talk only about "
    "what the reader notices and feels when reading the second version "
    "instead of the first - as if a thoughtful friend were pointing out why "
    "the phrasing choice matters. Respond with ONLY a JSON object: "
    '{"why": str}.'
)


def _explain_why(
    client: LLMClient,
    thesis: str,
    literal: str,
    aura: str,
    priority_tradeoffs_made: str,
) -> str:
    user = (
        f"What this song is really about: {thesis}\n\n"
        f"Literal version:\n{literal}\n\n"
        f"Rewritten version:\n{aura}\n\n"
        f"Internal notes on why the rewrite differs (for your context only, "
        f"don't quote this back): {priority_tradeoffs_made}\n\n"
        "Give me the one-sentence explanation now."
    )
    data = client.complete_json(_WHY_SYSTEM, user, max_tokens=300, stage="explain_why")
    return data.get("why", "").strip()


def _translator_text(result: SectionResultV1) -> str:
    for candidate in result.candidates:
        if candidate.agent == "translator":
            return candidate.text
    return result.candidates[0].text if result.candidates else ""


def _dominant_feeling(dna, section_name: str) -> str | None:
    """SongDNA.sections[n].emotional_arc_point.dominant_feeling, the real
    per-section field the consumer "Lore Storyline" surface anchors on -
    None only if the section name can't be found (a stored/cached result
    from before a schema change, not a normal case for a fresh run)."""
    try:
        return dna.section(section_name).emotional_arc_point.dominant_feeling
    except KeyError:
        return None


def _deviations_payload(result: SectionResultV1) -> list[dict]:
    """Fragment-level Burden-of-Change ledger, for positioning consumer-
    facing underlines - NOT for the popup's prose. `justification` is
    written for an engineer auditing a ruling (see this module's opening
    docstring), the same reason `why` below goes through an LLM paraphrase
    before shipping; the consumer surface must reuse that already-
    paraphrased `why` sentence, not render `justification` verbatim.
    """
    return [
        {
            "fragmentOriginal": d.fragment_original,
            "fragmentAdapted": d.fragment_adapted,
            "justification": d.justification,
        }
        for d in result.ruling.deviations
    ]


def _singability(result: SectionResultV1, aura: str, target_language: str) -> dict | None:
    """The same measurement engine/verify.py's Singability check already
    computes, surfaced to the reader instead of staying backend-log-only.
    Only meaningful for an English shipped line (count_syllables_text is
    CMU-dictionary-backed - see engine/rhythm.py) and only when there's a
    real source count to compare against (Latin-script source only, or a
    counted script like Japanese morae) - None means "nothing to report,"
    never a fabricated 0.
    """
    if target_language != "English":
        return None
    source_count = result.source_syllable_count
    if not source_count:
        return None
    shipped_count = count_syllables_text(aura)
    delta_ratio = abs(shipped_count - source_count) / source_count
    return {
        "sourceCount": source_count,
        "shippedCount": shipped_count,
        "closeMatch": delta_ratio <= SYLLABLE_DELTA_WARN_RATIO,
    }


def to_experience_result(
    client: LLMClient,
    engine_result: EngineResult,
    result_id: str,
    explain_why_client: LLMClient | None = None,
) -> dict:
    """`explain_why_client`, if given, handles the _explain_why calls
    instead of `client` — presentation text, not adaptation reasoning, so
    it's the one place worth a cheaper model (see engine/config.py's
    EXPLAIN_WHY_MODEL). Defaults to `client` so existing callers that
    don't pass this keep working unchanged.
    """
    why_client = explain_why_client or client
    source_by_name = {s.name: s.source_text for s in engine_result.song.sections}

    sections = []
    original = []
    for result in engine_result.section_results:
        if not isinstance(result, SectionResultV1):
            raise TypeError("to_experience_result only supports room_version='v1' results.")

        literal = _translator_text(result)
        aura = result.ruling.final_line
        why = _explain_why(
            why_client,
            engine_result.dna.artistic_thesis,
            literal,
            aura,
            result.ruling.priority_tradeoffs_made,
        )
        sections.append(
            {
                "id": result.section,
                "literal": literal,
                "aura": aura,
                "why": why,
                "singability": _singability(result, aura, engine_result.song.target_language),
                "dominantFeeling": _dominant_feeling(engine_result.dna, result.section),
                "deviations": _deviations_payload(result),
            }
        )
        original.append(
            {"id": result.section, "text": source_by_name.get(result.section, "")}
        )

    return {
        "id": result_id,
        "hook": engine_result.dna.artistic_thesis,
        "sourceLanguage": engine_result.song.source_language,
        "targetLanguage": engine_result.song.target_language,
        "sections": sections,
        "original": original,
        "poeticRegister": engine_result.dna.poetic_register,
    }
