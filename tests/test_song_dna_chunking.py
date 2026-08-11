"""Tests for the chunked long-song Song DNA path (engine/song_dna.py's
_generate_chunked_song_dna) - the fix for the "long-form input needs
chunked analysis (not yet implemented)" gap. A song with more than
SECTION_COUNT_SOFT_LIMIT distinct sections used to silently truncate in
one call; it now gets a real whole-work call plus per-section analysis in
SECTION_CHUNK_SIZE-sized batches instead.
"""
from __future__ import annotations

from engine.models import SectionInput, SongInput
from engine.song_dna import (
    SECTION_CHUNK_SIZE,
    SECTION_COUNT_SOFT_LIMIT,
    generate_song_dna,
)

_OVERVIEW = {
    "artistic_thesis": "test thesis",
    "genre_feel": "test genre",
    "poetic_register": "test register",
    "arc_shape": "test arc",
    "songwriter_intention": "test intention",
    "turn_points": [],
    "motifs": [],
    "ambiguities": [],
    "symbols": [],
    "repetition_patterns": [],
    "style": {
        "diction_register": "test",
        "rhyme_type": "test",
        "syntax_tendency": "test",
        "signature_devices": [],
    },
}


def _section_profile(name: str) -> dict:
    return {
        "name": name,
        "narrative_function": {"section": name, "function": "setup", "relation_to_adjacent": "n/a"},
        "density": {"section": name, "density": "sparse", "note": "test"},
        "emotional_arc_point": {
            "section": name,
            "valence": 0.0,
            "intensity": 0.0,
            "dominant_feeling": "test",
        },
        "imagery": [],
        "vulnerability": [],
        "rhythm": [],
    }


class _RecordingClient:
    """Fakes both the overview and per-batch section calls, and records
    every call's stage + the section names each batch was actually asked
    about - real assertions about chunk boundaries, not just "it ran"."""

    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []  # (stage, system, user)

    def complete_json(self, system: str, user: str, max_tokens=None, stage: str = "unknown") -> dict:
        self.calls.append((stage, system, user))
        if stage == "song_dna":
            # The single-call path - only reached for a song at/under
            # SECTION_COUNT_SOFT_LIMIT, so a small canned reply covering
            # every section given is enough.
            names = [line[1:-1] for line in user.splitlines() if line.startswith("[") and line.endswith("]")]
            return {**_OVERVIEW, "sections": [_section_profile(n) for n in names]}
        if stage == "song_dna_overview":
            return _OVERVIEW
        if stage == "song_dna_sections":
            names = [line[1:-1] for line in user.splitlines() if line.startswith("[") and line.endswith("]")]
            return {"sections": [_section_profile(n) for n in names]}
        raise AssertionError(f"Unexpected stage in the chunked path: {stage!r}")


def _long_song(section_count: int) -> SongInput:
    return SongInput(
        source_language="English (test)",
        sections=[
            SectionInput(name=f"section_{i}", source_text=f"line {i}") for i in range(section_count)
        ],
    )


def test_a_song_within_the_soft_limit_still_uses_the_single_call_path():
    """No behavior change for the common case - this is the same
    assertion the pre-existing golden-prompt/missing-section tests make,
    restated here to pin the boundary itself."""
    client = _RecordingClient()
    song = _long_song(SECTION_COUNT_SOFT_LIMIT)  # exactly at the limit, not over it

    generate_song_dna(song, client)

    stages = [c[0] for c in client.calls]
    assert stages == ["song_dna"]


def test_a_song_over_the_soft_limit_uses_the_chunked_path():
    client = _RecordingClient()
    song = _long_song(SECTION_COUNT_SOFT_LIMIT + 1)

    dna = generate_song_dna(song, client)

    stages = [c[0] for c in client.calls]
    assert stages[0] == "song_dna_overview"
    assert all(s == "song_dna_sections" for s in stages[1:])
    assert dna.artistic_thesis == "test thesis"
    assert {s.name for s in dna.sections} == {f"section_{i}" for i in range(SECTION_COUNT_SOFT_LIMIT + 1)}


def test_chunked_path_batches_at_the_configured_chunk_size():
    section_count = SECTION_CHUNK_SIZE * 2 + 3  # two full batches + a partial one
    client = _RecordingClient()
    song = _long_song(section_count)

    generate_song_dna(song, client)

    batch_calls = [c for c in client.calls if c[0] == "song_dna_sections"]
    assert len(batch_calls) == 3  # ceil(section_count / SECTION_CHUNK_SIZE)
    batch_sizes = [user.count("\n\n[") for _stage, _system, user in batch_calls]
    # First two batches full-sized, the last one holds the remainder - real
    # chunk boundaries, not just "some number of calls happened".
    assert batch_sizes == [SECTION_CHUNK_SIZE, SECTION_CHUNK_SIZE, 3]


def test_chunked_path_covers_every_section_exactly_once():
    section_count = SECTION_CHUNK_SIZE * 3 + 1
    client = _RecordingClient()
    song = _long_song(section_count)

    dna = generate_song_dna(song, client)

    names = [s.name for s in dna.sections]
    assert len(names) == section_count
    assert len(set(names)) == section_count  # no section analyzed twice


def test_chunked_path_grounds_every_batch_in_the_same_overview():
    """Each batch's prompt carries the SAME whole-work read from the
    overview call, not a per-batch guess - the whole reason for the two-
    call split instead of just splitting sections blind."""
    client = _RecordingClient()
    song = _long_song(SECTION_CHUNK_SIZE * 2 + 1)

    generate_song_dna(song, client)

    batch_users = [user for stage, _system, user in client.calls if stage == "song_dna_sections"]
    assert len(batch_users) == 3
    for user in batch_users:
        assert "test thesis" in user
        assert "test arc" in user


def test_chunked_path_still_patches_a_section_a_batch_omitted():
    """_fill_missing_sections must still run on the merged result - a
    model dropping a section inside one batch is exactly as recoverable
    as it was in the single-call path, not a new crash surface."""

    class _DropsOneSection(_RecordingClient):
        def complete_json(self, system, user, max_tokens=None, stage="unknown"):
            if stage != "song_dna_sections":
                return super().complete_json(system, user, max_tokens, stage)
            names = [line[1:-1] for line in user.splitlines() if line.startswith("[") and line.endswith("]")]
            names = names[1:]  # drop the first section of every batch
            self.calls.append((stage, system, user))
            return {"sections": [_section_profile(n) for n in names]}

    client = _DropsOneSection()
    song = _long_song(SECTION_COUNT_SOFT_LIMIT + 1)

    dna = generate_song_dna(song, client)

    assert {s.name for s in dna.sections} == {f"section_{i}" for i in range(SECTION_COUNT_SOFT_LIMIT + 1)}
    dropped = dna.section("section_0")
    assert dropped.narrative_function.function == "unspecified"
