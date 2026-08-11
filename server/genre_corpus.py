"""Real, if empty-at-first, corpus collection for docs/CAPABILITY_MATRIX.md's
"Genre-aware calibration" deferred gap.

That gap isn't missing engineering — it's missing DATA. `verify.py`
already computes `rhyme_density` (per section) and
`phoneme_repetition_similarity` (per song), and deliberately never turns
either into a pass/fail signal, because what counts as "enough" rhyme
genuinely varies by genre (a Hindi film couplet and a plain-spoken
English indie lyric have opposite defaults) and no real corpus exists to
learn those per-genre norms from. Inventing threshold numbers without one
would just be an elaborate way of shipping made-up numbers — exactly the
fabricated-confidence failure this codebase's own no-fabrication
discipline exists to rule out elsewhere.

This module does NOT calibrate anything. It only starts accumulating the
corpus that calibration would eventually need: one row per real song
adaptation (server/db_models.py::GenreCalibrationSample), written
best-effort right after verify.py runs. Once enough real rows exist,
`summarize_corpus` gives a human descriptive statistics to eyeball — real
calibration, if it ever happens, is a deliberate, separate decision made
by looking at that data, not something this module decides on its own.
"""
from __future__ import annotations

import logging
import os
import statistics

from engine.verify import VerificationReport

logger = logging.getLogger(__name__)

# Deliberately coarse and keyword-based, not an LLM call: this only needs
# to be good enough to GROUP real songs for later human inspection, not
# accurate enough to describe any single song well (that job already
# belongs to Song DNA's free-text genre_feel, which this never replaces
# or feeds back into). A genuinely ambiguous or novel genre_feel string
# landing in "other" is the correct, honest outcome, not a bug to chase -
# the alternative (forcing a wrong specific bucket) is worse for a corpus
# whose whole purpose is describing real per-genre norms accurately.
# Checked in order — first match wins — so more specific genres (e.g.
# "hip_hop_rap") are checked before generic ones ("pop") that might
# share a substring in a real Song DNA description.
_GENRE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("hip_hop_rap", ("hip hop", "hip-hop", "rap", "trap")),
    ("devotional_spiritual", ("devotional", "sacred", "spiritual", "bhajan", "qawwali", "hymn", "religious")),
    ("electronic_dance", ("electronic", "edm", "synth", "dance", "house", "techno")),
    ("rnb_soul", ("r&b", "rnb", "soul")),
    ("folk_traditional", ("folk", "traditional", "trot")),
    ("rock", ("rock", "punk", "metal")),
    ("ballad", ("ballad",)),
    ("pop", ("pop",)),
]


def classify_genre_bucket(genre_feel: str) -> str:
    """Maps Song DNA's free-text `genre_feel` (e.g. "melancholic pop
    ballad") to one of a small, fixed set of coarse buckets, or "other"
    when nothing matches. See this module's docstring for why a fixed
    vocabulary is the right tradeoff HERE even though it's deliberately
    NOT used for genre_feel itself at the engine layer.
    """
    lowered = genre_feel.lower()
    for bucket, keywords in _GENRE_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return bucket
    return "other"


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def record_calibration_sample(
    result_id: str,
    genre_feel: str,
    source_language: str,
    target_language: str,
    report: VerificationReport,
) -> None:
    """Best-effort, same discipline server/main.py's `_record_history`
    already holds itself to: a failure here is logged and swallowed,
    never allowed to fail the real adaptation request it's piggybacking
    on. No-ops entirely when no database is configured (local dev
    without DATABASE_URL) - there's nowhere to accumulate a corpus in
    that case, and that's fine; this was never meant to run in every
    environment, only real deployments.
    """
    if not _use_db():
        return
    try:
        from . import db
        from .db_models import GenreCalibrationSample

        verifiable = [s for s in report.sections if s.rhyme_density is not None]
        mean_rhyme_density = (
            sum(s.rhyme_density for s in verifiable) / len(verifiable) if verifiable else None
        )
        with db.session_scope() as session:
            session.add(
                GenreCalibrationSample(
                    result_id=result_id,
                    genre_feel=genre_feel,
                    genre_bucket=classify_genre_bucket(genre_feel),
                    source_language=source_language,
                    target_language=target_language,
                    mean_rhyme_density=mean_rhyme_density,
                    rhyme_density_section_count=len(verifiable),
                    phoneme_repetition_similarity=report.phoneme_repetition_similarity,
                )
            )
            session.commit()
    except Exception:
        logger.exception("failed to record genre calibration sample result_id=%s", result_id)


def summarize_corpus() -> list[dict]:
    """Descriptive statistics per genre_bucket over every sample
    accumulated so far — count, and mean rhyme_density/
    phoneme_repetition_similarity where computable. NEVER a pass/fail
    threshold and never will be from inside this function: turning this
    into real calibration is a deliberate future decision made by a
    human looking at real accumulated data, not something to automate
    here. Returns [] when no database is configured or no samples exist
    yet — an honest, empty corpus, not an error.
    """
    if not _use_db():
        return []

    from . import db
    from .db_models import GenreCalibrationSample

    with db.session_scope() as session:
        rows = session.query(GenreCalibrationSample).all()
        # Extract plain values while the session is still open, rather
        # than handing back ORM objects tied to a session about to close.
        samples = [
            (row.genre_bucket, row.mean_rhyme_density, row.phoneme_repetition_similarity)
            for row in rows
        ]

    by_bucket: dict[str, list[tuple[float | None, float | None]]] = {}
    for bucket, rhyme, pho in samples:
        by_bucket.setdefault(bucket, []).append((rhyme, pho))

    summary = []
    for bucket, values in sorted(by_bucket.items()):
        # rhyme_values/pho_values, and their counts below, are per-SONG
        # (one mean_rhyme_density per sample row, already averaged across
        # that song's own sections at write time) - not a count of
        # underlying sections. A row's own rhyme_density_section_count
        # column has the per-song section count for anyone drilling in.
        rhyme_values = [r for r, _ in values if r is not None]
        pho_values = [p for _, p in values if p is not None]
        summary.append(
            {
                "genre_bucket": bucket,
                "sample_count": len(values),
                "mean_rhyme_density": statistics.mean(rhyme_values) if rhyme_values else None,
                "rhyme_density_sample_count": len(rhyme_values),
                "mean_phoneme_repetition_similarity": (
                    statistics.mean(pho_values) if pho_values else None
                ),
                "phoneme_repetition_sample_count": len(pho_values),
            }
        )
    return summary
