"""System adapters. Each takes a SongInput and returns per-section output
text. The engine is imported and *used*, never modified.

Systems:
  castia            — the full engine (Song DNA + V1 Writers' Room).
  gpt_single      — one bare prompt to the same OpenAI model CASTIA uses.
                    This is the critical ablation: it isolates the value
                    of CASTIA's process from the value of its model.
  claude_single   — the same bare prompt to Anthropic's model.
  google_translate— machine translation floor (deep-translator's free
                    endpoint; no API key, may be rate-limited/blocked —
                    falls back to a manual file if present).
  manual:<name>   — hand-collected reference translations (Bollynook,
                    FilmyQuotes, human literary versions). These sites
                    have no APIs and scraping them is fragile and legally
                    murky, so they enter the benchmark as pasted files:
                    benchmark/manual/<song_id>/<name>.txt, sections
                    separated by blank lines. Missing file = system
                    skipped for that song, logged, never faked.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Protocol

from engine.llm_client import LLMClient
from engine.models import SongInput
from engine.pipeline import run_engine

logger = logging.getLogger(__name__)

MANUAL_DIR = Path(__file__).parent / "manual"

# The single-prompt baseline. Deliberately a *good* prompt — beating a
# strawman proves nothing. It asks for exactly what CASTIA promises.
SINGLE_PROMPT = (
    "Translate these {source_language} song lyrics into English. "
    "Do not translate literally: preserve the emotional impact, imagery, "
    "tone, and artistic intent so it reads like a real English lyric. "
    "Return ONLY the translated lyrics, keeping the same section structure "
    "separated by blank lines, with no commentary, no headers, no notes.\n\n"
    "{sections}"
)


class System(Protocol):
    name: str

    def run(self, song: SongInput) -> list[str] | None: ...


class CastiaSystem:
    """The engine exactly as production runs it.

    `apply_corrective_pass` defaults to True because that is what
    server/main.py::_run_adaptation always passes, and a benchmark that
    measures a different configuration from the one that ships is not
    measuring the product. This was previously omitted, so the benchmark
    would have run the engine with NO verification and NO corrective
    pass - stripping out the most distinctive part of the system in the
    one experiment meant to decide whether that part earns its cost, and
    understating Castia against the single-prompt baseline it is being
    compared to.

    Kept as a parameter rather than hardcoded so the no-verify
    configuration can be registered alongside as a deliberate ablation
    (name it "castia_no_verify"), which would measure what the verifier
    and corrective pass actually contribute. That is a genuinely useful
    comparison; it is just not what "castia" means.
    """

    def __init__(
        self,
        client_factory: Callable[[], LLMClient],
        apply_corrective_pass: bool = True,
        name: str = "castia",
    ):
        self.name = name
        self._client_factory = client_factory
        self._apply_corrective_pass = apply_corrective_pass

    def run(self, song: SongInput) -> list[str] | None:
        result = run_engine(
            song,
            client=self._client_factory(),
            room_version="v1",
            apply_corrective_pass=self._apply_corrective_pass,
        )
        return [r.ruling.final_line for r in result.section_results]


class SinglePromptSystem:
    """One bare LLM call, no Song DNA, no room, no judge — the ablation."""

    def __init__(self, name: str, client_factory: Callable[[], LLMClient]):
        self.name = name
        self._client_factory = client_factory

    def run(self, song: SongInput) -> list[str] | None:
        client = self._client_factory()
        joined = "\n\n".join(s.source_text for s in song.sections)
        prompt = SINGLE_PROMPT.format(
            source_language=song.source_language, sections=joined
        )
        # complete_json expects JSON; ask for one field to stay uniform
        # with the engine's client interface instead of adding a raw-text
        # path to it (which would mean modifying the engine).
        system = (
            "You translate song lyrics. Respond with ONLY a JSON object: "
            '{"lyrics": "the full translated lyrics, sections separated by '
            'blank lines"}.'
        )
        data = client.complete_json(system, prompt, max_tokens=4000)
        text = data.get("lyrics", "")
        if not text:
            return None
        sections = [b.strip() for b in text.split("\n\n") if b.strip()]
        return sections


class GoogleTranslateSystem:
    name = "google_translate"

    def run(self, song: SongInput) -> list[str] | None:
        try:
            from deep_translator import GoogleTranslator
        except ImportError:
            logger.warning(
                "deep-translator not installed; falling back to manual file "
                "for google_translate (pip install -r requirements-benchmark.txt)."
            )
            return _read_manual(song, "google_translate")
        try:
            translator = GoogleTranslator(source="auto", target="en")
            return [translator.translate(s.source_text) for s in song.sections]
        except Exception as exc:  # noqa: BLE001 — network service, fail soft
            logger.warning(
                "Google Translate failed (%s); falling back to manual file.", exc
            )
            return _read_manual(song, "google_translate")


class ManualSystem:
    """Reference translations pasted by hand into benchmark/manual/."""

    def __init__(self, name: str):
        self.name = name

    def run(self, song: SongInput) -> list[str] | None:
        return _read_manual(song, self.name)


def _read_manual(song: SongInput, system_name: str) -> list[str] | None:
    song_id = song.title or "untitled"
    path = MANUAL_DIR / _slug(song_id) / f"{system_name}.txt"
    if not path.exists():
        logger.info(
            "No manual file for system=%s song=%s (expected %s) — skipped.",
            system_name, song_id, path,
        )
        return None
    blocks = [b.strip() for b in path.read_text().split("\n\n") if b.strip()]
    return blocks or None


def _slug(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def default_systems() -> list[System]:
    """Everything the benchmark runs by default. LLM clients are built
    lazily per run so a missing ANTHROPIC_API_KEY only skips
    claude_single instead of blocking the whole benchmark.
    """
    from engine.llm_client import AnthropicLLMClient, OpenAILLMClient

    return [
        CastiaSystem(OpenAILLMClient),
        SinglePromptSystem("gpt_single", OpenAILLMClient),
        SinglePromptSystem("claude_single", AnthropicLLMClient),
        GoogleTranslateSystem(),
        ManualSystem("bollynook"),
        ManualSystem("filmyquotes"),
    ]
