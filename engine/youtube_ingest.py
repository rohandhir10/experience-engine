"""YouTube ingestion: pulls a video's own subtitles/captions and turns them
into a *draft* SongInput JSON a human reviews and edits before it's ever
handed to the engine.

This is deliberately a separate, disconnected step — the engine itself
stays text-in, text-out (docs/ENGINE.md). Nothing here calls an LLM or
touches engine/pipeline.py; it only produces a file in the same shape as
examples/*.json, with a big warning baked into context_note that section
names/boundaries are a timing-gap guess, not real verse/chorus structure,
and must be checked by a human first.

Two things this can't fix, and shouldn't pretend to:
  - Auto-generated ("ASR") captions are speech-to-text run on singing, not
    speech - for most music videos in non-English languages they're poor
    to unusable. This module always prefers a manually-created transcript
    over an auto-generated one, and labels which kind it found.
  - Many official music videos have no transcript at all (captions
    disabled, or none uploaded). That's a hard failure, reported clearly,
    not a fallback to a worse-quality source.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)

# Timing gap (seconds) between one caption ending and the next starting that
# we treat as a likely section boundary (end of verse/chorus, instrumental
# break). This is a heuristic, not a real structural analysis - it will
# sometimes be wrong, which is exactly why the output is a draft.
DEFAULT_GAP_THRESHOLD_SECONDS = 3.0

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

# Common ISO 639-1 codes for languages this project has actually tested
# against - not exhaustive. Anything unmapped is passed through as-is so a
# human filling in the draft can correct it themselves.
_LANGUAGE_NAMES = {
    "hi": "Hindi",
    "pa": "Punjabi",
    "ur": "Urdu",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "ru": "Russian",
    "es": "Spanish",
    "en": "English",
}


class IngestError(Exception):
    """Raised for any failure a human needs to see plainly, not as a stack trace."""


@dataclass
class TranscriptSegment:
    text: str
    start: float
    duration: float


def extract_video_id(url_or_id: str) -> str:
    """Accepts a full YouTube URL (watch/shortened/embed/shorts) or a bare
    11-character video ID, and returns the video ID.
    """
    candidate = url_or_id.strip()
    if _VIDEO_ID_RE.match(candidate):
        return candidate

    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, candidate)
        if match:
            return match.group(1)

    raise IngestError(
        f"Could not extract a video ID from {url_or_id!r}. Expected a full "
        "YouTube URL or an 11-character video ID."
    )


def fetch_transcript(
    video_id: str, preferred_languages: list[str] | None = None
) -> tuple[list[TranscriptSegment], str, bool]:
    """Fetches the best available transcript for a video.

    Prefers a manually-created transcript over an auto-generated one, and
    prefers preferred_languages (if given) over whatever else is available.
    Returns (segments, language_code, is_generated) so the caller can warn
    the human when the only transcript available is auto-generated.

    Raises IngestError with a plain-language reason on any failure - no
    transcript available, transcripts disabled, video unavailable, etc.
    """
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
    except TranscriptsDisabled as exc:
        raise IngestError(
            f"Captions are disabled for video {video_id!r}. This pipeline "
            "can only work from a transcript the video actually has."
        ) from exc
    except VideoUnavailable as exc:
        raise IngestError(f"Video {video_id!r} is unavailable.") from exc
    except Exception as exc:  # noqa: BLE001 - surfaced as IngestError either way
        # The raw exception (connection pool internals, proxy errors,
        # whatever requests/urllib3 happened to say) is logged for
        # whoever's debugging this, but never shown to the person who
        # pasted a link - a library stack-trace-shaped string is exactly
        # the "cold technical log leaking to a consumer" failure this
        # project treats as a real bug everywhere else it's shown up.
        logger.warning("YouTube transcript list fetch failed for %r: %s", video_id, exc)
        raise IngestError(
            f"Could not reach YouTube for video {video_id!r} right now. "
            "This is usually temporary - try again in a moment."
        ) from exc

    languages = list(preferred_languages) if preferred_languages else None

    transcript = None
    is_generated = True
    try:
        if languages:
            transcript = transcript_list.find_manually_created_transcript(languages)
            is_generated = False
    except NoTranscriptFound:
        pass

    if transcript is None:
        try:
            transcript = transcript_list.find_manually_created_transcript(
                [t.language_code for t in transcript_list]
            )
            is_generated = False
        except NoTranscriptFound:
            pass

    if transcript is None:
        try:
            transcript = (
                transcript_list.find_generated_transcript(languages)
                if languages
                else next(iter(transcript_list))
            )
            is_generated = transcript.is_generated
        except (NoTranscriptFound, StopIteration) as exc:
            raise IngestError(
                f"No transcript at all is available for video {video_id!r}."
            ) from exc

    try:
        fetched = transcript.fetch()
    except Exception as exc:  # noqa: BLE001 - same reasoning as api.list()'s catch above
        logger.warning("YouTube transcript fetch failed for %r: %s", video_id, exc)
        raise IngestError(
            f"Could not download the transcript for video {video_id!r} right "
            "now. This is usually temporary - try again in a moment."
        ) from exc

    segments = [
        TranscriptSegment(text=s.text.strip(), start=s.start, duration=s.duration)
        for s in fetched
        if s.text.strip()
    ]
    if not segments:
        raise IngestError(f"Transcript for video {video_id!r} came back empty.")

    return segments, transcript.language_code, is_generated


@dataclass
class TimedBlock:
    text: str
    start: float
    end: float


def group_into_sections_with_timing(
    segments: list[TranscriptSegment],
    gap_threshold_seconds: float = DEFAULT_GAP_THRESHOLD_SECONDS,
) -> list[TimedBlock]:
    """Same grouping heuristic as group_into_sections, but keeps each
    block's start (its first caption's start time) and end (its last
    caption's start + duration) - needed to sync playback to the
    eventually-adapted lyrics (server/main.py's /api/youtube-draft), not
    needed by the CLI draft, which only ever wrote text to a JSON file.
    """
    if not segments:
        return []

    blocks: list[list[TranscriptSegment]] = [[segments[0]]]
    prev_end = segments[0].start + segments[0].duration

    for segment in segments[1:]:
        gap = segment.start - prev_end
        if gap >= gap_threshold_seconds:
            blocks.append([])
        blocks[-1].append(segment)
        prev_end = segment.start + segment.duration

    return [
        TimedBlock(
            text="\n".join(s.text for s in block),
            start=block[0].start,
            end=block[-1].start + block[-1].duration,
        )
        for block in blocks
    ]


def group_into_sections(
    segments: list[TranscriptSegment],
    gap_threshold_seconds: float = DEFAULT_GAP_THRESHOLD_SECONDS,
) -> list[str]:
    """Groups caption lines into blocks separated by a timing gap, as a rough
    stand-in for verse/chorus boundaries. This is a guess, not a structural
    analysis - the resulting section count and boundaries are exactly what
    the human is expected to correct before running the engine.
    """
    return [b.text for b in group_into_sections_with_timing(segments, gap_threshold_seconds)]


def _draft_warning(
    language_code: str, is_generated: bool, gap_threshold_seconds: float
) -> str:
    caption_kind = "auto-generated (speech-to-text)" if is_generated else "manually created"
    return (
        f"DRAFT - NOT REVIEWED. Captions were {caption_kind} ({language_code}). "
        + (
            "Auto-generated captions are speech-to-text run on singing, not "
            "speech, and are frequently wrong or garbled for sung lyrics - "
            "check every line against the actual audio before trusting this "
            "text. "
            if is_generated
            else ""
        )
        + f"Section boundaries below were guessed from a >= "
        f"{gap_threshold_seconds:.1f}s pause between captions, not real "
        "verse/chorus structure - rename sections and fix boundaries by hand "
        "before running this through the engine."
    )


def build_song_draft(
    url_or_id: str,
    preferred_languages: list[str] | None = None,
    gap_threshold_seconds: float = DEFAULT_GAP_THRESHOLD_SECONDS,
) -> dict:
    """Produces a dict in the same shape as examples/*.json - NOT validated
    or run through the engine here. The caller writes it to a file for a
    human to review and correct before ever pointing engine/cli.py at it.
    """
    video_id = extract_video_id(url_or_id)
    segments, language_code, is_generated = fetch_transcript(video_id, preferred_languages)
    section_texts = group_into_sections(segments, gap_threshold_seconds)
    language_name = _LANGUAGE_NAMES.get(language_code, language_code)

    return {
        "title": None,
        "source_language": language_name,
        "context_note": _draft_warning(language_code, is_generated, gap_threshold_seconds),
        "sections": [
            {"name": f"section_{i + 1}", "source_text": text}
            for i, text in enumerate(section_texts)
        ],
    }


# Matches the blank-line-separated-blocks convention engine/text_ingest.py's
# split_into_sections expects from the homepage's single textarea - so a
# web-ingested draft can be edited in exactly the same box, by the exact
# same rule, as a manually pasted song.
_SECTION_JOIN = "\n\n"


def build_web_draft(
    url_or_id: str,
    preferred_languages: list[str] | None = None,
    gap_threshold_seconds: float = DEFAULT_GAP_THRESHOLD_SECONDS,
) -> dict:
    """Like build_song_draft, but shaped for server/main.py's
    /api/youtube-draft endpoint rather than a CLI-written JSON file:
    one editable blob of text (same review step the CLI's "must be
    checked by a human first" warning asks for, just done in the
    browser's textarea instead of a text editor) plus the per-section
    timing needed to sync playback afterward.

    Still never touches engine/pipeline.py - this is ingestion, not
    adaptation. If the section count that comes back from splitting the
    (possibly hand-edited) draft text later doesn't match len(sections)
    here, the caller must not attempt to line up timings by position
    anymore - see server/main.py's adapt().
    """
    video_id = extract_video_id(url_or_id)
    segments, language_code, is_generated = fetch_transcript(video_id, preferred_languages)
    blocks = group_into_sections_with_timing(segments, gap_threshold_seconds)
    language_name = _LANGUAGE_NAMES.get(language_code, language_code)

    return {
        "video_id": video_id,
        "source_language": language_name,
        "warning": _draft_warning(language_code, is_generated, gap_threshold_seconds),
        "draft_text": _SECTION_JOIN.join(b.text for b in blocks),
        "sections": [{"start": b.start, "end": b.end} for b in blocks],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract a YouTube video's own subtitles into a draft SongInput "
            "JSON. Produces a DRAFT for human review - never runs the engine "
            "itself."
        )
    )
    parser.add_argument("url", help="YouTube URL or bare video ID.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Where to write the draft JSON. Defaults to <video_id>.draft.json",
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        default=None,
        help="Preferred transcript language codes, e.g. --languages hi en",
    )
    parser.add_argument(
        "--gap-threshold",
        type=float,
        default=DEFAULT_GAP_THRESHOLD_SECONDS,
        help="Seconds of silence between captions treated as a section break.",
    )
    args = parser.parse_args(argv)

    try:
        draft = build_song_draft(args.url, args.languages, args.gap_threshold)
    except IngestError as exc:
        print(f"Could not ingest this video: {exc}", file=sys.stderr)
        return 1

    video_id = extract_video_id(args.url)
    output_path = args.output or Path(f"{video_id}.draft.json")
    output_path.write_text(json.dumps(draft, indent=2, ensure_ascii=False))

    print(f"Wrote draft to {output_path}")
    print(
        "\nThis is a DRAFT. Open it, fix the section names/boundaries, set "
        "source_language and title, and re-check the text against the "
        "audio before running:\n"
        f"  python3 -m engine.cli {output_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
