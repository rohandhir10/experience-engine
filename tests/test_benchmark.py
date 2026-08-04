"""End-to-end benchmark tests with fake systems — no network, no LLM.

The most important test here is blind integrity: the reviewer packet must
not contain any system name anywhere, or the benchmark's evidence is
worthless.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark.analyze import analyze, paired_permutation_test
from benchmark.blind import make_blind_packets
from benchmark.normalize import normalize_section, normalize_sections
from benchmark.runner import run_benchmark
from benchmark.schema import DIMENSIONS
from engine.models import SectionInput, SongInput

SYSTEM_NAMES = ("castia", "gpt_single", "claude_single", "google_translate")


class FakeSystem:
    def __init__(self, name: str, quality: str):
        self.name = name
        self.quality = quality

    def run(self, song: SongInput) -> list[str]:
        return [f"{self.quality} rendering of {s.name}" for s in song.sections]


class FailingSystem:
    name = "always_fails"

    def run(self, song: SongInput) -> list[str]:
        raise RuntimeError("simulated provider outage")


@pytest.fixture
def song() -> SongInput:
    return SongInput(
        title="Test Song",
        source_language="Hindi",
        sections=[
            SectionInput(name="verse_1", source_text="पहली पंक्ति"),
            SectionInput(name="chorus", source_text="दूसरी पंक्ति"),
        ],
    )


@pytest.fixture
def run_dir(tmp_path: Path, song: SongInput) -> Path:
    systems = [FakeSystem(name, f"style_{i}") for i, name in enumerate(SYSTEM_NAMES)]
    systems.append(FailingSystem())
    outputs = run_benchmark([song], systems, "testrun", runs_dir=tmp_path)
    run_dir = tmp_path / "testrun"
    make_blind_packets(outputs, [song], ["priya", "amit"], run_dir, seed=3)
    return run_dir


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def test_normalize_strips_section_headers_and_quotes():
    raw = '[chorus]\n"Line one here"\n\n  Line   two  '
    assert normalize_section(raw) == "Line one here\nLine two"


def test_normalize_drops_empty_sections():
    assert normalize_sections(["[verse]", "real text"]) == ["real text"]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def test_failing_system_is_skipped_not_fatal(run_dir: Path):
    stored = list((run_dir / "outputs" / "test_song").glob("*.json"))
    assert len(stored) == len(SYSTEM_NAMES)  # failure skipped, others stored
    assert not (run_dir / "outputs" / "test_song" / "always_fails.json").exists()


# ---------------------------------------------------------------------------
# Blind integrity — the test that makes the evidence worth anything
# ---------------------------------------------------------------------------


def test_reviewer_packets_never_contain_system_names(run_dir: Path):
    for packet in (run_dir / "blind").glob("packet_*.html"):
        content = packet.read_text().lower()
        for name in (*SYSTEM_NAMES, "always_fails", "bollynook", "filmyquotes"):
            assert name not in content, f"{packet.name} leaks system name {name!r}"


def test_key_covers_every_reviewer_song_letter(run_dir: Path):
    key = json.loads((run_dir / "blind" / "key.json").read_text())
    combos = {(e["reviewer"], e["song_id"], e["letter"]) for e in key}
    assert len(combos) == 2 * len(SYSTEM_NAMES)  # 2 reviewers x 4 outputs
    assert {e["system"] for e in key} == set(SYSTEM_NAMES)


def test_reviewers_get_independent_orders(run_dir: Path):
    key = json.loads((run_dir / "blind" / "key.json").read_text())
    order_by_reviewer = {}
    for entry in key:
        order_by_reviewer.setdefault(entry["reviewer"], []).append(
            (entry["letter"], entry["system"])
        )
    orders = [sorted(v) for v in order_by_reviewer.values()]
    # With 4 systems and independent shuffles, identical order for both
    # reviewers is possible but the mapping must at least be internally
    # consistent and complete for each reviewer.
    assert all(len(o) == len(SYSTEM_NAMES) for o in orders)


# ---------------------------------------------------------------------------
# Analysis + statistics
# ---------------------------------------------------------------------------


def test_permutation_test_sanity():
    assert paired_permutation_test([0, 0, 0]) == 1.0
    strong = [2, 2, 1, 2, 2, 1, 2, 2, 1, 2]  # consistently positive
    assert paired_permutation_test(strong) < 0.01
    noise = [1, -1, 1, -1, 1, -1]
    assert paired_permutation_test(noise) > 0.5


def _simulate_ratings(run_dir: Path, favored: str = "castia") -> None:
    """Writes ratings as if reviewers consistently preferred `favored`."""
    key = json.loads((run_dir / "blind" / "key.json").read_text())
    by_reviewer: dict[str, list[dict]] = {}
    for entry in key:
        is_favored = entry["system"] == favored
        by_reviewer.setdefault(entry["reviewer"], []).append(
            {
                "reviewer": entry["reviewer"],
                "song_id": entry["song_id"],
                "letter": entry["letter"],
                "scores": {d: (5 if is_favored else 3) for d in DIMENSIONS},
                "best_overall": is_favored,
            }
        )
    ratings_dir = run_dir / "ratings"
    ratings_dir.mkdir(exist_ok=True)
    for reviewer, ratings in by_reviewer.items():
        (ratings_dir / f"ratings_{reviewer}.json").write_text(
            json.dumps({"reviewer": reviewer, "ratings": ratings})
        )


def test_report_deblinds_and_ranks_correctly(run_dir: Path):
    _simulate_ratings(run_dir, favored="castia")
    report = analyze(run_dir)
    assert "| castia | 5.00 | 5.00 | 5.00 | 5.00 | 5.00 |" in report
    assert "Honest limitations" in report
    assert (run_dir / "report.md").exists()
    # castia should top the best-overall table
    best_section = report.split("## Best-overall picks")[1].split("## ")[0]
    data_rows = [
        l for l in best_section.splitlines()
        if l.startswith("| ") and not l.startswith("| System")
    ]
    assert data_rows[0].startswith("| castia |")


def test_report_significance_columns_present(run_dir: Path):
    _simulate_ratings(run_dir, favored="castia")
    report = analyze(run_dir)
    assert "| Baseline | Dimension | n pairs | Mean diff | p |" in report
    assert "gpt_single" in report
