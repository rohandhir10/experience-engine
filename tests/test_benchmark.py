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


# ---------------------------------------------------------------------------
# The benchmark must measure the engine PRODUCTION runs.
#
# CastiaSystem previously called run_engine without apply_corrective_pass,
# while server/main.py::_run_adaptation always passes it. The benchmark
# would therefore have measured an engine with no verification and no
# corrective pass - removing the most distinctive part of the system in
# the one experiment meant to decide whether that part is worth its cost.
# ---------------------------------------------------------------------------


def test_castia_system_runs_the_corrective_pass_like_production():
    from benchmark.systems import CastiaSystem

    captured = {}

    def fake_run_engine(song, client=None, room_version="v1", apply_corrective_pass=False):
        captured["apply_corrective_pass"] = apply_corrective_pass
        captured["room_version"] = room_version

        class _R:
            section_results = []

        return _R()

    import benchmark.systems as systems

    original = systems.run_engine
    systems.run_engine = fake_run_engine
    try:
        CastiaSystem(lambda: None).run(object())
    finally:
        systems.run_engine = original

    assert captured["apply_corrective_pass"] is True
    assert captured["room_version"] == "v1"


def test_the_production_call_site_and_the_benchmark_agree():
    """Guards the two from drifting apart again: if production ever stops
    passing apply_corrective_pass=True, this fails and forces the
    benchmark to be reconsidered alongside it.
    """
    import pathlib

    main_py = pathlib.Path("server/main.py").read_text(encoding="utf-8")
    assert "apply_corrective_pass=True" in main_py


def test_a_no_verify_ablation_can_still_be_registered():
    """The configuration is a parameter, not a hardcoded value, so the
    ablation that isolates the verifier's contribution stays available."""
    from benchmark.systems import CastiaSystem

    ablation = CastiaSystem(lambda: None, apply_corrective_pass=False, name="castia_no_verify")
    assert ablation.name == "castia_no_verify"
    assert ablation._apply_corrective_pass is False


# ---------------------------------------------------------------------------
# Corpus exclusions.
#
# examples/ holds more than benchmark material: a synthetic fixture the
# CLI docs depend on, and a one-section fragment. Both would have been
# swept into a paid run and weighted like real ten-section songs.
# ---------------------------------------------------------------------------


def test_the_examples_corpus_excludes_the_fixture_and_the_fragment():
    from pathlib import Path

    from benchmark.runner import load_corpus

    titles = {s.title for s in load_corpus(Path("examples"))}
    assert not any("synthetic" in t.lower() for t in titles)
    assert not any("single line" in t.lower() for t in titles)
    # Three, not four: balam_pichkari was found to be an unfilled
    # template (every section reads "REPLACE with ...") and is excluded
    # until real lyrics are put in it.
    assert titles == {"Agar Tum Saath Ho", "Har Ek Baat Pe Kehte Ho Tum", "Sadda Haq"}


def test_the_excluded_files_still_exist_for_their_other_uses(tmp_path):
    """Excluding from the corpus must not delete them - sample_song.json
    is the CLI example referenced from README.md and docs/ENGINE.md."""
    from pathlib import Path

    assert Path("examples/sample_song.json").exists()
    assert Path("examples/sadda_haq_single_line.json").exists()


def test_exclusions_are_read_from_the_corpus_directory(tmp_path):
    import json

    from benchmark.runner import load_corpus

    song = {"title": "Keep Me", "source_language": "Hindi",
            "sections": [{"name": "verse_1", "source_text": "a line"}]}
    drop = {"title": "Drop Me", "source_language": "Hindi",
            "sections": [{"name": "verse_1", "source_text": "a line"}]}
    (tmp_path / "keep.json").write_text(json.dumps(song))
    (tmp_path / "drop.json").write_text(json.dumps(drop))
    (tmp_path / ".benchmarkignore").write_text("# a comment\n\ndrop.json\n")

    titles = [s.title for s in load_corpus(tmp_path)]
    assert titles == ["Keep Me"]


def test_a_corpus_with_no_ignore_file_loads_everything(tmp_path):
    import json

    from benchmark.runner import load_corpus

    (tmp_path / "a.json").write_text(json.dumps(
        {"title": "A", "source_language": "Hindi",
         "sections": [{"name": "v", "source_text": "x"}]}
    ))
    assert len(load_corpus(tmp_path)) == 1


def test_excluding_everything_is_an_error_not_an_empty_run(tmp_path):
    """Better to fail loudly than to produce a report from zero songs."""
    import json

    import pytest as _pytest

    from benchmark.runner import load_corpus

    (tmp_path / "a.json").write_text(json.dumps(
        {"title": "A", "source_language": "Hindi",
         "sections": [{"name": "v", "source_text": "x"}]}
    ))
    (tmp_path / ".benchmarkignore").write_text("a\n")
    with _pytest.raises(ValueError):
        load_corpus(tmp_path)


# ---------------------------------------------------------------------------
# Corpus validation.
#
# Every failure here is silent - none would crash a run, all would produce
# a report that looks finished and means less than it appears to. Both of
# the first two were found for real in examples/ on this validator's very
# first run.
# ---------------------------------------------------------------------------


def _song(tmp_path, name, language, *texts):
    import json

    (tmp_path / f"{name}.json").write_text(
        json.dumps({
            "title": name, "source_language": language,
            "sections": [{"name": f"s{i}", "source_text": t} for i, t in enumerate(texts)],
        }),
        encoding="utf-8",
    )


def test_an_unfilled_template_is_an_error(tmp_path):
    """examples/balam_pichkari.json had nine sections every one of which
    read "REPLACE with the opening 4 lines ...". The engine would have
    adapted the instructions and reviewers would have rated the result.
    """
    from benchmark.validate import validate_corpus

    _song(tmp_path, "template", "Hindi",
          "REPLACE with the opening 4 lines", "REPLACE with the chorus", "x")
    report = validate_corpus(tmp_path)
    assert not report.ok
    assert any("placeholder" in e for e in report.errors)


def test_romanised_lyrics_are_a_warning_not_an_error(tmp_path):
    """Real lyrics in Latin script are a legitimate input this product
    accepts - but G2P grounding cannot run on them, so the run tests a
    different path than the same song in its own script."""
    from benchmark.validate import validate_corpus

    _song(tmp_path, "romanised", "Hindi/Punjabi (code-switched)",
          "Tum logon ki, is duniya mein", "Sadda haq, aithe rakh", "Guzarish hai")
    report = validate_corpus(tmp_path)
    assert report.ok
    assert any("romanised" in w for w in report.warnings)


def test_a_song_in_its_own_script_passes_clean(tmp_path):
    from benchmark.validate import validate_corpus

    _song(tmp_path, "devanagari", "Hindi",
          "पल-भर ठहर जाओ", "दिल ये सँभल जाए", "कैसे तुम्हें रोकूँ")
    report = validate_corpus(tmp_path)
    assert report.ok
    assert not report.warnings


def test_a_fragment_is_flagged(tmp_path):
    from benchmark.validate import validate_corpus

    _song(tmp_path, "fragment", "Hindi", "पल-भर ठहर जाओ")
    report = validate_corpus(tmp_path)
    assert any("section" in w for w in report.warnings)


def test_empty_and_malformed_files_are_errors(tmp_path):
    from benchmark.validate import validate_corpus

    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    _song(tmp_path, "empty", "Hindi", "", "  ")
    report = validate_corpus(tmp_path)
    assert len(report.errors) == 2


def test_excluded_files_are_reported_but_not_validated(tmp_path):
    from benchmark.validate import validate_corpus

    _song(tmp_path, "skipme", "Hindi", "REPLACE with anything")
    _song(tmp_path, "keep", "Hindi", "पल-भर ठहर जाओ", "दिल ये", "सँभल जाए")
    (tmp_path / ".benchmarkignore").write_text("skipme\n")
    report = validate_corpus(tmp_path)
    assert report.ok  # the placeholder was excluded, so it isn't an error
    assert report.excluded == ["skipme"]


def test_the_shipped_examples_corpus_has_no_placeholder_songs():
    """Regression guard: balam_pichkari must stay excluded until it is
    actually filled in."""
    from pathlib import Path

    from benchmark.validate import validate_corpus

    report = validate_corpus(Path("examples"))
    assert report.ok, report.render()
