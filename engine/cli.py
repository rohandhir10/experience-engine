"""Command-line entry point.

Usage:
    python -m engine.cli examples/sample_song.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import SongInput
from .pipeline import run_engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the AURA engine on one song.")
    parser.add_argument(
        "song_file",
        type=Path,
        help="Path to a song JSON file (see examples/sample_song.json for the shape).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Where to write the full JSON transcript. Defaults to <song_file>.result.json",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "After the run, check the result against the Burden of Change "
            "constitution deterministically (engine/verify.py) and print the "
            "audit. No extra LLM calls."
        ),
    )
    parser.add_argument(
        "--room",
        choices=["v1", "full"],
        default="v1",
        help=(
            "Which Writers' Room to run: 'v1' (default) is the minimal "
            "3-agent room from docs/WRITERS_ROOM_V1.md; 'full' is the "
            "original 7-agent room from docs/WRITERS_ROOM.md."
        ),
    )
    args = parser.parse_args(argv)

    song_data = json.loads(args.song_file.read_text())
    song = SongInput.model_validate(song_data)

    result = run_engine(song, room_version=args.room)

    output_path = args.output or args.song_file.with_suffix(".result.json")
    output_path.write_text(json.dumps(result.to_dict(), indent=2))

    print(f"Wrote full transcript to {output_path}")
    print("\nFinal lyrics:\n")
    print(result.final_lyrics())

    if args.verify:
        from .verify import verify_result

        report = verify_result(result.to_dict())
        print("\n" + report.summary())

    return 0


if __name__ == "__main__":
    sys.exit(main())
