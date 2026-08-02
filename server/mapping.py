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


def to_experience_result(client: LLMClient, engine_result: EngineResult, result_id: str) -> dict:
    source_by_name = {s.name: s.source_text for s in engine_result.song.sections}

    sections = []
    original = []
    for result in engine_result.section_results:
        if not isinstance(result, SectionResultV1):
            raise TypeError("to_experience_result only supports room_version='v1' results.")

        literal = _translator_text(result)
        aura = result.ruling.final_line
        why = _explain_why(
            client,
            engine_result.dna.artistic_thesis,
            literal,
            aura,
            result.ruling.priority_tradeoffs_made,
        )
        sections.append(
            {"id": result.section, "literal": literal, "aura": aura, "why": why}
        )
        original.append(
            {"id": result.section, "text": source_by_name.get(result.section, "")}
        )

    return {
        "id": result_id,
        "hook": engine_result.dna.artistic_thesis,
        "sourceLanguage": engine_result.song.source_language,
        "sections": sections,
        "original": original,
    }
