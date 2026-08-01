"""De-blinds returned ratings, computes per-system statistics, and writes
a markdown report with real significance tests.

Statistics, chosen to be defensible without heavy dependencies:

- Per dimension, per system: mean rating and n.
- AURA vs. each baseline: paired differences on matched (reviewer, song)
  pairs, tested with a two-sided paired sign-flip permutation test —
  exact in spirit, assumption-light (no normality claim), and honest at
  the small sample sizes this benchmark will start with.
- Best-overall: how often each system's output was picked as the best
  version of a song.

The report states its own limitations (n, reviewers, corpus size)
instead of overclaiming — evidence nobody can pick apart beats a big
number someone can.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .schema import DIMENSIONS, BlindKeyEntry, Rating, ReviewerSubmission

PERMUTATION_ITERATIONS = 20_000


def load_key(run_dir: Path) -> dict[tuple[str, str, str], str]:
    entries = [
        BlindKeyEntry.model_validate(e)
        for e in json.loads((run_dir / "blind" / "key.json").read_text())
    ]
    return {(e.reviewer, e.song_id, e.letter): e.system for e in entries}


def load_ratings(run_dir: Path) -> list[Rating]:
    ratings: list[Rating] = []
    ratings_dir = run_dir / "ratings"
    for path in sorted(ratings_dir.glob("*.json")):
        submission = ReviewerSubmission.model_validate(json.loads(path.read_text()))
        ratings.extend(submission.ratings)
    if not ratings:
        raise ValueError(f"No rating files found in {ratings_dir}")
    return ratings


def deblind(
    ratings: list[Rating], key: dict[tuple[str, str, str], str]
) -> list[tuple[str, Rating]]:
    """Returns [(system, rating), ...]; unknown letters are an error —
    a rating that can't be attributed means the key and packets diverged.
    """
    out = []
    for rating in ratings:
        lookup = (rating.reviewer, rating.song_id, rating.letter)
        if lookup not in key:
            raise KeyError(f"Rating has no key entry: {lookup}")
        out.append((key[lookup], rating))
    return out


def paired_permutation_test(
    diffs: list[float], iterations: int = PERMUTATION_ITERATIONS, seed: int = 11
) -> float:
    """Two-sided p-value for mean(diffs) != 0 via sign-flip permutation."""
    if not diffs or all(d == 0 for d in diffs):
        return 1.0
    rng = random.Random(seed)
    observed = abs(mean(diffs))
    hits = 0
    for _ in range(iterations):
        flipped = [d if rng.random() < 0.5 else -d for d in diffs]
        if abs(mean(flipped)) >= observed - 1e-12:
            hits += 1
    return hits / iterations


def analyze(run_dir: Path, primary: str = "aura") -> str:
    key = load_key(run_dir)
    labeled = deblind(load_ratings(run_dir), key)

    # (system, dimension) -> list of scores; (reviewer, song, system, dim) -> score
    scores: dict[tuple[str, str], list[int]] = defaultdict(list)
    paired: dict[tuple[str, str, str], dict[str, int]] = defaultdict(dict)
    best_counts: dict[str, int] = defaultdict(int)
    best_total = 0
    reviewers, songs = set(), set()

    for system, rating in labeled:
        reviewers.add(rating.reviewer)
        songs.add(rating.song_id)
        for dim, score in rating.scores.items():
            scores[(system, dim)].append(score)
            paired[(rating.reviewer, rating.song_id, dim)][system] = score
        if rating.best_overall:
            best_counts[system] += 1
            best_total += 1

    systems = sorted({system for system, _ in scores})

    lines = [
        "# AURA blind benchmark report",
        "",
        f"- Reviewers: {len(reviewers)}",
        f"- Songs: {len(songs)}",
        f"- Systems compared: {', '.join(systems)}",
        "",
        "## Mean ratings (1-5)",
        "",
        "| System | " + " | ".join(DIMENSIONS) + " | Overall |",
        "|---|" + "---|" * (len(DIMENSIONS) + 1),
    ]
    for system in systems:
        row = [system]
        all_scores: list[int] = []
        for dim in DIMENSIONS:
            values = scores.get((system, dim), [])
            all_scores.extend(values)
            row.append(f"{mean(values):.2f}" if values else "—")
        row.append(f"{mean(all_scores):.2f}" if all_scores else "—")
        lines.append("| " + " | ".join(row) + " |")

    lines += [
        "",
        "## Best-overall picks",
        "",
        "| System | Times picked best | Share |",
        "|---|---|---|",
    ]
    for system in sorted(best_counts, key=best_counts.get, reverse=True):
        share = best_counts[system] / best_total if best_total else 0
        lines.append(f"| {system} | {best_counts[system]} | {share:.0%} |")

    lines += [
        "",
        f"## {primary} vs. each baseline (paired, per reviewer x song)",
        "",
        "Two-sided sign-flip permutation test on matched pairs. p < 0.05 "
        "conventionally 'significant' — but read n first: with few "
        "reviewer x song pairs, a non-significant result means 'not enough "
        "data', not 'no difference'.",
        "",
        "| Baseline | Dimension | n pairs | Mean diff | p |",
        "|---|---|---|---|---|",
    ]
    for baseline in systems:
        if baseline == primary:
            continue
        for dim in DIMENSIONS:
            diffs = [
                by_system[primary] - by_system[baseline]
                for (_, _, d), by_system in paired.items()
                if d == dim and primary in by_system and baseline in by_system
            ]
            if not diffs:
                continue
            p = paired_permutation_test(diffs)
            marker = " *" if p < 0.05 else ""
            lines.append(
                f"| {baseline} | {dim} | {len(diffs)} | "
                f"{mean(diffs):+.2f} | {p:.4f}{marker} |"
            )

    lines += [
        "",
        "## Honest limitations",
        "",
        f"- {len(reviewers)} reviewer(s) and {len(songs)} song(s) is "
        "preliminary evidence, not proof. The pre-registered bar "
        "(docs/WRITERS_ROOM_V1.md §9.5) is 10-15 songs across emotional "
        "registers, replicated on held-out songs never used to tune a prompt.",
        "- Reviewers were recruited by the project; independent replication "
        "would strengthen any claim.",
        "- Systems missing for some songs (no manual reference available) "
        "reduce paired-n against those baselines specifically.",
    ]

    report = "\n".join(lines) + "\n"
    (run_dir / "report.md").write_text(report)
    return report
