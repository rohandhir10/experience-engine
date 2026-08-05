"""Runs every system over a corpus of songs and stores normalized outputs.

Layout it produces:

    benchmark/runs/<run_id>/outputs/<song_id>/<system>.json

Each output file is a SystemOutput. A system that fails or has no data
for a song is logged and skipped — never silently faked, never allowed
to sink the whole run.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from engine.models import SongInput

from .normalize import normalize_sections
from .schema import SystemOutput
from .systems import System, _slug

logger = logging.getLogger(__name__)

RUNS_DIR = Path(__file__).parent / "runs"


EXCLUDE_FILE = ".benchmarkignore"


def load_exclusions(corpus_dir: Path) -> set[str]:
    """Stems listed in the corpus directory's .benchmarkignore, one per
    line, blank lines and #-comments skipped.

    Lives in the repo rather than in a --exclude flag on purpose: a flag
    is something the next person has to remember, and a corpus that
    silently includes the wrong songs produces a confidently wrong
    number. The file travels with the corpus and is reviewable in a diff.
    """
    path = corpus_dir / EXCLUDE_FILE
    if not path.exists():
        return set()
    stems = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            stems.add(line.removesuffix(".json"))
    return stems


def load_corpus(corpus_dir: Path) -> list[SongInput]:
    """Every song JSON in `corpus_dir`, minus anything .benchmarkignore
    excludes.

    Not every file that is useful to have around belongs in a quality
    measurement: a synthetic fixture used by the CLI docs, or a
    single-section fragment kept for a repro, would both dilute every
    mean they touched while looking like real evidence in the report.
    """
    excluded = load_exclusions(corpus_dir)
    songs = []
    skipped = []
    for path in sorted(corpus_dir.glob("*.json")):
        if path.stem in excluded:
            skipped.append(path.stem)
            continue
        songs.append(SongInput.model_validate(json.loads(path.read_text())))
    if skipped:
        logger.info(
            "Corpus %s: excluded %d file(s) per %s - %s",
            corpus_dir, len(skipped), EXCLUDE_FILE, ", ".join(skipped),
        )
    if not songs:
        raise ValueError(f"No song JSON files found in {corpus_dir}")
    return songs


def run_benchmark(
    songs: list[SongInput],
    systems: list[System],
    run_id: str,
    runs_dir: Path = RUNS_DIR,
) -> dict[str, list[SystemOutput]]:
    """Returns {song_id: [SystemOutput, ...]} and writes everything to disk."""
    outputs_by_song: dict[str, list[SystemOutput]] = {}

    for song in songs:
        song_id = _slug(song.title or "untitled")
        song_dir = runs_dir / run_id / "outputs" / song_id
        song_dir.mkdir(parents=True, exist_ok=True)
        outputs_by_song[song_id] = []

        for system in systems:
            out_path = song_dir / f"{system.name}.json"
            if out_path.exists():
                output = SystemOutput.model_validate(json.loads(out_path.read_text()))
                outputs_by_song[song_id].append(output)
                logger.info("[%s] %s: already done, reusing.", song_id, system.name)
                continue

            logger.info("[%s] running %s ...", song_id, system.name)
            try:
                sections = system.run(song)
            except Exception as exc:  # noqa: BLE001 — one system must not sink the run
                logger.error("[%s] %s FAILED: %s", song_id, system.name, exc)
                continue

            if not sections:
                logger.warning("[%s] %s produced nothing — skipped.", song_id, system.name)
                continue

            output = SystemOutput(
                song_id=song_id,
                system=system.name,
                sections=normalize_sections(sections),
            )
            out_path.write_text(json.dumps(output.model_dump(), ensure_ascii=False, indent=2))
            outputs_by_song[song_id].append(output)

    return outputs_by_song
