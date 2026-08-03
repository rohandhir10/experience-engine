"""Tests for engine/youtube_ingest.py that never touch the network - they
exercise URL parsing and the section-grouping heuristic against synthetic
TranscriptSegment data, and check build_song_draft's shape against a
monkeypatched fetch_transcript.
"""
from __future__ import annotations

import pytest

from engine import youtube_ingest as yi
from engine.youtube_ingest import IngestError, TranscriptSegment, extract_video_id, group_into_sections


def test_extract_video_id_from_watch_url():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_from_watch_url_with_extra_params():
    assert (
        extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL123")
        == "dQw4w9WgXcQ"
    )


def test_extract_video_id_from_short_url():
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_from_shorts_url():
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_from_bare_id():
    assert extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_raises_on_garbage():
    with pytest.raises(IngestError):
        extract_video_id("not a youtube link at all")


def test_group_into_sections_splits_on_large_gaps():
    segments = [
        TranscriptSegment(text="line one", start=0.0, duration=2.0),
        TranscriptSegment(text="line two", start=2.5, duration=2.0),
        # 5-second gap here (prev ends at 4.5, this starts at 9.5)
        TranscriptSegment(text="line three", start=9.5, duration=2.0),
        TranscriptSegment(text="line four", start=12.0, duration=2.0),
    ]
    sections = group_into_sections(segments, gap_threshold_seconds=3.0)
    assert sections == ["line one\nline two", "line three\nline four"]


def test_group_into_sections_keeps_everything_together_with_no_gaps():
    segments = [
        TranscriptSegment(text="a", start=0.0, duration=1.0),
        TranscriptSegment(text="b", start=1.0, duration=1.0),
        TranscriptSegment(text="c", start=2.0, duration=1.0),
    ]
    sections = group_into_sections(segments, gap_threshold_seconds=3.0)
    assert sections == ["a\nb\nc"]


def test_group_into_sections_empty_input():
    assert group_into_sections([]) == []


class _FakeListRaises:
    """Stands in for YouTubeTranscriptApi when api.list() itself fails
    (network/proxy error, rate limit, whatever) - the case that used to
    dump a raw exception string straight into the user-facing message."""

    def __init__(self, exc: Exception):
        self._exc = exc

    def list(self, video_id):
        raise self._exc


class _FakeTranscript:
    def __init__(self, fetch_exc: Exception | None = None):
        self._fetch_exc = fetch_exc
        self.language_code = "en"
        self.is_generated = False

    def fetch(self):
        if self._fetch_exc:
            raise self._fetch_exc
        return [TranscriptSegment(text="a line", start=0.0, duration=1.0)]


class _FakeListFetchRaises:
    """Stands in for YouTubeTranscriptApi when listing succeeds but the
    actual transcript.fetch() call fails - previously uncaught entirely,
    so it would have crashed as a raw 500 instead of a clean IngestError."""

    def __init__(self, fetch_exc: Exception):
        self._fetch_exc = fetch_exc

    def list(self, video_id):
        return self

    def find_manually_created_transcript(self, languages):
        raise yi.NoTranscriptFound(video_id="x", requested_language_codes=languages, transcript_data=[])

    def find_generated_transcript(self, languages):
        return _FakeTranscript(fetch_exc=self._fetch_exc)

    def __iter__(self):
        return iter([_FakeTranscript(fetch_exc=self._fetch_exc)])


def test_fetch_transcript_hides_raw_exception_text_when_listing_fails(monkeypatch):
    """A ProxyError/ConnectionError's raw str() is exactly the kind of
    library-internal text a listener/reader should never see - the
    message must stay clean and generic, with the real detail only
    logged, not shown."""
    raw = Exception(
        "HTTPSConnectionPool(host='www.youtube.com', port=443): Max retries "
        "exceeded (Caused by ProxyError('Tunnel connection failed: 403'))"
    )
    monkeypatch.setattr(yi, "YouTubeTranscriptApi", lambda: _FakeListRaises(raw))

    with pytest.raises(IngestError) as exc_info:
        yi.fetch_transcript("dQw4w9WgXcQ")

    message = str(exc_info.value)
    assert "ProxyError" not in message
    assert "HTTPSConnectionPool" not in message
    assert "try again" in message


def test_fetch_transcript_hides_raw_exception_text_when_fetch_fails(monkeypatch):
    """transcript.fetch() (downloading the actual captions, a separate
    network call from listing what's available) previously had no
    try/except at all - an exception here used to propagate unhandled
    instead of becoming a clean IngestError."""
    raw = ConnectionResetError("connection reset by peer")
    monkeypatch.setattr(yi, "YouTubeTranscriptApi", lambda: _FakeListFetchRaises(raw))

    with pytest.raises(IngestError) as exc_info:
        yi.fetch_transcript("dQw4w9WgXcQ", preferred_languages=["en"])

    message = str(exc_info.value)
    assert "connection reset" not in message.lower()
    assert "try again" in message


def test_build_song_draft_shape_and_warning(monkeypatch):
    def fake_fetch_transcript(video_id, preferred_languages=None):
        return (
            [
                TranscriptSegment(text="pehli panktee", start=0.0, duration=2.0),
                TranscriptSegment(text="dusri panktee", start=2.0, duration=2.0),
            ],
            "hi",
            False,
        )

    monkeypatch.setattr(yi, "fetch_transcript", fake_fetch_transcript)

    draft = yi.build_song_draft("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert draft["source_language"] == "Hindi"
    assert draft["title"] is None
    assert "DRAFT" in draft["context_note"]
    assert "manually created" in draft["context_note"]
    assert "speech-to-text" not in draft["context_note"]
    assert draft["sections"] == [
        {"name": "section_1", "source_text": "pehli panktee\ndusri panktee"}
    ]


def test_build_song_draft_warns_when_auto_generated(monkeypatch):
    def fake_fetch_transcript(video_id, preferred_languages=None):
        return (
            [TranscriptSegment(text="garbled asr text", start=0.0, duration=2.0)],
            "hi",
            True,
        )

    monkeypatch.setattr(yi, "fetch_transcript", fake_fetch_transcript)

    draft = yi.build_song_draft("dQw4w9WgXcQ")
    assert "auto-generated" in draft["context_note"]
    assert "speech-to-text" in draft["context_note"]


def test_group_into_sections_with_timing_keeps_start_and_end_per_block():
    segments = [
        TranscriptSegment(text="line one", start=0.0, duration=2.0),
        TranscriptSegment(text="line two", start=2.5, duration=2.0),
        # 5-second gap here (prev ends at 4.5, this starts at 9.5)
        TranscriptSegment(text="line three", start=9.5, duration=2.0),
        TranscriptSegment(text="line four", start=12.0, duration=2.0),
    ]
    blocks = yi.group_into_sections_with_timing(segments, gap_threshold_seconds=3.0)

    assert [b.text for b in blocks] == ["line one\nline two", "line three\nline four"]
    assert blocks[0].start == 0.0
    assert blocks[0].end == 4.5  # last segment in block: start 2.5 + duration 2.0
    assert blocks[1].start == 9.5
    assert blocks[1].end == 14.0


def test_build_web_draft_shape(monkeypatch):
    def fake_fetch_transcript(video_id, preferred_languages=None):
        return (
            [
                TranscriptSegment(text="pehli panktee", start=0.0, duration=2.0),
                TranscriptSegment(text="dusri panktee", start=10.0, duration=2.0),
            ],
            "hi",
            False,
        )

    monkeypatch.setattr(yi, "fetch_transcript", fake_fetch_transcript)

    draft = yi.build_web_draft("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert draft["video_id"] == "dQw4w9WgXcQ"
    assert draft["source_language"] == "Hindi"
    assert "DRAFT" in draft["warning"]
    # Two separate blocks (10s gap > default 3s threshold) joined by a
    # blank line - text_ingest.py's split_into_sections must recover the
    # same two blocks from this exact string.
    assert draft["draft_text"] == "pehli panktee\n\ndusri panktee"
    assert draft["sections"] == [
        {"start": 0.0, "end": 2.0},
        {"start": 10.0, "end": 12.0},
    ]


def test_build_web_draft_text_round_trips_through_split_into_sections(monkeypatch):
    """The whole design depends on this: a web-ingested draft, dropped
    into the same textarea a manual paste would use, must split back into
    the same number of sections the timing list has entries for."""
    from engine.text_ingest import split_into_sections

    def fake_fetch_transcript(video_id, preferred_languages=None):
        return (
            [
                TranscriptSegment(text="verse line", start=0.0, duration=2.0),
                TranscriptSegment(text="chorus line", start=10.0, duration=2.0),
            ],
            "en",
            False,
        )

    monkeypatch.setattr(yi, "fetch_transcript", fake_fetch_transcript)
    draft = yi.build_web_draft("dQw4w9WgXcQ")

    sections = split_into_sections(draft["draft_text"])
    assert len(sections) == len(draft["sections"])
