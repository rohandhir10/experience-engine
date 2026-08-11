"""server/genre_corpus.py — corpus collection for docs/CAPABILITY_MATRIX.md's
"Genre-aware calibration" deferred gap. This module deliberately does NOT
calibrate anything (see its own module docstring) — these tests verify
classification, best-effort persistence, and honest aggregation, not any
pass/fail threshold (there isn't one).
"""
from __future__ import annotations

import pytest

import server.db as db
from engine.verify import SectionVerification, VerificationReport
from server import genre_corpus


# ---------------------------------------------------------------------------
# classify_genre_bucket — pure, no database
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "genre_feel,expected",
    [
        ("melancholic pop ballad", "ballad"),  # ballad is checked before pop
        ("upbeat bubblegum pop anthem", "pop"),
        ("hip-hop banger with trap influences", "hip_hop_rap"),
        ("sacred devotional qawwali", "devotional_spiritual"),
        ("driving electronic dance track", "electronic_dance"),
        ("smooth R&B slow jam", "rnb_soul"),
        ("traditional Korean folk trot", "folk_traditional"),
        ("angry punk rock anthem", "rock"),
        ("a genuinely indescribable art-song experiment", "other"),
    ],
)
def test_classify_genre_bucket(genre_feel, expected):
    assert genre_corpus.classify_genre_bucket(genre_feel) == expected


def test_classify_is_case_insensitive():
    assert genre_corpus.classify_genre_bucket("HIP HOP ANTHEM") == "hip_hop_rap"


def test_classify_checks_more_specific_genres_before_generic_pop():
    # "ballad" is checked before the generic "pop" keyword, so a "pop
    # ballad" buckets as the more specific ballad, not plain pop.
    assert genre_corpus.classify_genre_bucket("a slow pop ballad") == "ballad"


# ---------------------------------------------------------------------------
# record_calibration_sample / summarize_corpus — real sqlite database
# ---------------------------------------------------------------------------


@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/genre_corpus_test.db"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    db.create_all()
    yield url
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)


def _report(rhyme_densities: list[float | None], pho_similarity: float | None) -> VerificationReport:
    sections = [
        SectionVerification(
            section=f"s{i}",
            ledger_coverage=1.0,
            computed_invention_penalty=0.0,
            reported_invention_penalty=0.0,
            changed_word_count=0,
            rhyme_density=density,
        )
        for i, density in enumerate(rhyme_densities)
    ]
    return VerificationReport(sections=sections, phoneme_repetition_similarity=pho_similarity)


def test_record_without_database_is_a_silent_noop(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Must not raise, even though there's nowhere to write.
    genre_corpus.record_calibration_sample(
        "r1", "pop anthem", "English", "English", _report([0.5], 0.1)
    )
    assert genre_corpus.summarize_corpus() == []


def test_record_then_summarize_round_trips(sqlite_db):
    genre_corpus.record_calibration_sample(
        "r1", "upbeat pop anthem", "Korean", "English", _report([0.6, 0.8], 0.3)
    )
    summary = genre_corpus.summarize_corpus()
    assert len(summary) == 1
    row = summary[0]
    assert row["genre_bucket"] == "pop"
    assert row["sample_count"] == 1
    assert row["mean_rhyme_density"] == pytest.approx(0.7)
    # This song contributed ONE mean_rhyme_density value (averaged from
    # its own 2 sections at write time) - rhyme_density_sample_count here
    # counts contributing SONGS, not sections.
    assert row["rhyme_density_sample_count"] == 1
    assert row["mean_phoneme_repetition_similarity"] == pytest.approx(0.3)


def test_none_rhyme_density_values_are_excluded_from_the_mean_not_treated_as_zero(sqlite_db):
    genre_corpus.record_calibration_sample(
        "r1", "pop song", "English", "English", _report([0.8, None, None], None)
    )
    summary = genre_corpus.summarize_corpus()
    row = summary[0]
    # Only the one real value counts - averaging in the Nones as 0 would
    # give 0.267, not 0.8.
    assert row["mean_rhyme_density"] == pytest.approx(0.8)
    assert row["rhyme_density_sample_count"] == 1
    assert row["mean_phoneme_repetition_similarity"] is None
    assert row["phoneme_repetition_sample_count"] == 0


def test_summarize_groups_multiple_samples_by_bucket(sqlite_db):
    genre_corpus.record_calibration_sample(
        "r1", "pop anthem", "English", "English", _report([0.4], 0.2)
    )
    genre_corpus.record_calibration_sample(
        "r2", "another pop track", "English", "English", _report([0.6], 0.4)
    )
    genre_corpus.record_calibration_sample(
        "r3", "sacred devotional hymn", "Hindi", "English", _report([1.0], None)
    )
    summary = {row["genre_bucket"]: row for row in genre_corpus.summarize_corpus()}
    assert summary.keys() == {"pop", "devotional_spiritual"}
    assert summary["pop"]["sample_count"] == 2
    assert summary["pop"]["mean_rhyme_density"] == pytest.approx(0.5)
    assert summary["devotional_spiritual"]["sample_count"] == 1


def test_summarize_never_returns_a_pass_fail_field(sqlite_db):
    genre_corpus.record_calibration_sample(
        "r1", "pop anthem", "English", "English", _report([0.1], 0.1)
    )
    row = genre_corpus.summarize_corpus()[0]
    # Descriptive statistics only - this module must never manufacture a
    # threshold or verdict field, see its own module docstring.
    forbidden = {"pass", "fail", "passed", "threshold", "verdict", "ok"}
    assert not (set(row.keys()) & forbidden)


def test_record_never_raises_on_a_broken_database(monkeypatch):
    # Points at a DB that will fail to connect - record_calibration_sample
    # must swallow this, same discipline server/main.py's history
    # recording already holds itself to, since this is piggybacking on a
    # real user's request.
    monkeypatch.setenv("DATABASE_URL", "postgresql://nonexistent-host-xyz/db")
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_SessionLocal", None)
    genre_corpus.record_calibration_sample(
        "r1", "pop anthem", "English", "English", _report([0.5], 0.1)
    )  # must not raise
