"""Tests for engine/pipeline.py::run_engine's on_stage/on_section_done
progress callbacks and `deadline` safety ceiling - the song-side mirror
of tests/test_comics_adapt.py's equivalent coverage, added once the same
"looks completely frozen" bug (no progress reporting at all, no timeout
ceiling) was found to affect songs too, not just comics chapters.
"""
from __future__ import annotations

import time

import pytest

from engine.models import SectionInput, SongInput
from engine.pipeline import EngineTimeoutError, run_engine

from .test_section_repeats import FakeClientForRepeats


def _song(sections: list[SectionInput]) -> SongInput:
    return SongInput(source_language="English (test)", sections=sections)


def test_run_engine_reports_on_stage_for_each_section_in_order():
    song = _song(
        [
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="chorus", source_text="line two"),
        ]
    )
    client = FakeClientForRepeats()
    events: list[tuple[str, int, int]] = []

    run_engine(song, client=client, room_version="v1", on_stage=lambda *args: events.append(args))

    assert events == [("verse_1", 1, 2), ("chorus", 2, 2)]


def test_run_engine_reports_on_section_done_once_per_section_with_the_real_result():
    song = _song(
        [
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="chorus", source_text="line two"),
        ]
    )
    client = FakeClientForRepeats()
    completed: list[tuple[str, int, int]] = []

    def on_section_done(section_name, result, index, total):
        assert result.ruling.final_line == "I keep the drawer locked."
        completed.append((section_name, index, total))

    result = run_engine(song, client=client, room_version="v1", on_section_done=on_section_done)

    assert completed == [("verse_1", 1, 2), ("chorus", 2, 2)]
    # The callback must not change what the function actually returns.
    assert [r.section for r in result.section_results] == ["verse_1", "chorus"]


def test_run_engine_reports_both_callbacks_for_a_repeated_section_too():
    """A repeated section makes no LLM call at all, but it's still real,
    instant progress - a poller shouldn't see the section count stall
    just because this one was free."""
    song = _song(
        [
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="chorus", source_text="line two"),
            SectionInput(name="chorus_2", source_text="line two", repeats="chorus"),
        ]
    )
    client = FakeClientForRepeats()
    stage_events: list[str] = []
    done_events: list[str] = []

    run_engine(
        song,
        client=client,
        room_version="v1",
        on_stage=lambda name, index, total: stage_events.append(name),
        on_section_done=lambda name, result, index, total: done_events.append(name),
    )

    assert stage_events == ["verse_1", "chorus", "chorus_2"]
    assert done_events == ["verse_1", "chorus", "chorus_2"]


def test_run_engine_works_unchanged_with_no_callbacks_given():
    song = _song([SectionInput(name="verse_1", source_text="line one")])
    client = FakeClientForRepeats()
    result = run_engine(song, client=client, room_version="v1")
    assert [r.section for r in result.section_results] == ["verse_1"]


def test_run_engine_completes_normally_with_a_deadline_far_in_the_future():
    song = _song(
        [
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="chorus", source_text="line two"),
        ]
    )
    client = FakeClientForRepeats()

    result = run_engine(
        song, client=client, room_version="v1", deadline=time.monotonic() + 3600
    )

    assert [r.section for r in result.section_results] == ["verse_1", "chorus"]


def test_run_engine_raises_before_any_section_starts_if_the_deadline_has_already_passed():
    """The deadline is only checked in the section loop, not before Song
    DNA generation (which run_engine does first, unconditionally, same
    as engine/comics_adapt.py's ChapterTimeoutError not covering Chapter
    DNA generation either - see run_engine's docstring) - so one call for
    DNA happens even when the deadline is already gone, and zero section
    calls happen after that."""
    song = _song([SectionInput(name="verse_1", source_text="line one")])
    client = FakeClientForRepeats()

    with pytest.raises(EngineTimeoutError) as exc_info:
        run_engine(song, client=client, room_version="v1", deadline=time.monotonic() - 1)

    assert "0/1" in str(exc_info.value)
    assert len(client.calls) == 1  # only Song DNA generation, no section work


def test_run_engine_deadline_check_runs_between_sections_not_mid_flight():
    """A deadline that passes DURING verse_1's own processing must not
    cut verse_1 short, and must let it finish for real before stopping
    the song - the check only runs between sections (see run_engine's
    docstring on why: engine/llm_client.py's own per-call timeout is
    what bounds a single stuck request; this deadline is a coarser,
    song-wide ceiling on top of that, not a replacement for it)."""

    class SlowFakeClient(FakeClientForRepeats):
        def complete_json(self, system, user, max_tokens=None, stage="unknown") -> dict:
            time.sleep(0.05)
            return super().complete_json(system, user, max_tokens, stage)

    song = _song(
        [
            SectionInput(name="verse_1", source_text="line one"),
            SectionInput(name="chorus", source_text="line two"),
        ]
    )
    client = SlowFakeClient()

    # verse_1 alone takes >0.1s (song-dna + 3 section calls, each 0.05s);
    # this deadline is already gone by the time verse_1 finishes, but
    # still in the future when run_engine starts - so verse_1 must
    # complete intact and chorus must never start.
    deadline = time.monotonic() + 0.1

    with pytest.raises(EngineTimeoutError) as exc_info:
        run_engine(song, client=client, room_version="v1", deadline=deadline)

    assert "1/2" in str(exc_info.value)


def test_run_engine_never_enables_emphasis_markup_for_a_song():
    """run_engine has no emphasis_markup argument at all - comics-only
    typographic markup (engine/comics_adapt.py passes it to
    writers_room_v1.run_section directly) must never reach a song's
    Judge prompt. Captures the real system text (unlike
    FakeClientForRepeats.calls, which only keeps a 60-char prefix)."""

    class SystemCapturingClient(FakeClientForRepeats):
        def __init__(self):
            super().__init__()
            self.systems: list[str] = []

        def complete_json(self, system, user, max_tokens=None, stage="unknown"):
            self.systems.append(system)
            return super().complete_json(system, user, max_tokens, stage)

    song = _song([SectionInput(name="verse_1", source_text="line one")])
    client = SystemCapturingClient()

    run_engine(song, client=client, room_version="v1")

    assert not any("lettered into a comic speech bubble" in s for s in client.systems)
