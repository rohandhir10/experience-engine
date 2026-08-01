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
