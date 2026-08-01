"""Benchmark CLI — three stages, resumable, each writing plain files:

    # 1. Run every system over the corpus (needs OPENAI_API_KEY; Anthropic
    #    optional; manual reference files optional):
    python -m benchmark.cli run --corpus examples --run-id pilot_1

    # 2. Build blinded reviewer packets (after step 1):
    python -m benchmark.cli blind --run-id pilot_1 --corpus examples \\
        --reviewers priya rohan amit

    # 3. Drop returned ratings_*.json files into
    #    benchmark/runs/pilot_1/ratings/, then:
    python -m benchmark.cli report --run-id pilot_1
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .analyze import analyze
from .blind import make_blind_packets
from .runner import RUNS_DIR, load_corpus, run_benchmark
from .schema import SystemOutput
from .systems import default_systems


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="AURA blind benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run all systems over the corpus")
    p_run.add_argument("--corpus", type=Path, required=True)
    p_run.add_argument("--run-id", required=True)

    p_blind = sub.add_parser("blind", help="Build blinded reviewer packets")
    p_blind.add_argument("--run-id", required=True)
    p_blind.add_argument("--corpus", type=Path, required=True)
    p_blind.add_argument("--reviewers", nargs="+", required=True)
    p_blind.add_argument("--seed", type=int, default=7)

    p_report = sub.add_parser("report", help="De-blind ratings and write report.md")
    p_report.add_argument("--run-id", required=True)

    args = parser.parse_args(argv)
    run_dir = RUNS_DIR / args.run_id

    if args.command == "run":
        songs = load_corpus(args.corpus)
        outputs = run_benchmark(songs, default_systems(), args.run_id)
        total = sum(len(v) for v in outputs.values())
        print(f"Stored {total} outputs across {len(outputs)} song(s) in {run_dir}/outputs")
        return 0

    if args.command == "blind":
        songs = load_corpus(args.corpus)
        outputs_dir = run_dir / "outputs"
        if not outputs_dir.exists():
            print(f"No outputs at {outputs_dir} — run the 'run' stage first.", file=sys.stderr)
            return 1
        outputs_by_song = {}
        for song_dir in sorted(outputs_dir.iterdir()):
            if song_dir.is_dir():
                outputs_by_song[song_dir.name] = [
                    SystemOutput.model_validate_json(p.read_text())
                    for p in sorted(song_dir.glob("*.json"))
                ]
        blind_dir = make_blind_packets(
            outputs_by_song, songs, args.reviewers, run_dir, seed=args.seed
        )
        print(f"Packets + key written to {blind_dir}")
        print("Send each packet_<reviewer>.html to its reviewer. NEVER send key.json.")
        (run_dir / "ratings").mkdir(exist_ok=True)
        return 0

    if args.command == "report":
        report = analyze(run_dir)
        print(report)
        print(f"(also written to {run_dir}/report.md)")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
