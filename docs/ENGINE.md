# Running the Engine

Implements `docs/SONG_DNA.md` and `docs/WRITERS_ROOM.md` as a working
pipeline: one Song DNA analysis call, then the full five-round Writers'
Room (generate → diagnose → cross-critique → recombine → judge) run
section by section, with room memory carried forward between sections.

This is the code artifact for the design in those two documents — read
them first if you haven't; this doc only covers running it.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

Optional environment overrides (see `engine/config.py`):

- `AURA_MODEL` — defaults to `claude-sonnet-5`.
- `AURA_MAX_TOKENS` — defaults to `4096` per call (Song DNA and Judge calls
  request more headroom internally).

## Run it on a song

```bash
python -m engine.cli examples/sample_song.json
```

This writes `examples/sample_song.result.json` (the full transcript: Song
DNA, every round's candidates, every critique and rebuttal, and each
section's Judge ruling) and prints the final assembled lyrics to stdout.

`examples/sample_song.json` is a synthetic English-language fixture (the
"locked drawer" song used as the worked example in `SONG_DNA.md` §14) —
it exists to exercise the pipeline's mechanics without needing rights-
cleared foreign-language lyrics. A real production run supplies actual
Hindi/Japanese/Korean/Arabic/Russian/Spanish source lyrics per
`PRODUCTION_WORKFLOW.md`, with `source_language` set accordingly.

## Input format

```json
{
  "title": "optional",
  "source_language": "Korean",
  "context_note": "optional narrative context (EXPERIENCE_GRAPH.md §3.3)",
  "sections": [
    {"name": "verse_1", "source_text": "line one\nline two"},
    {"name": "chorus", "source_text": "..."}
  ]
}
```

Sections are processed in the order given, and each section's Judge ruling
is added to room memory before the next section runs — this is what lets
later sections stay consistent with earlier ones (`WRITERS_ROOM.md` §8).

## Output format

The written `.result.json` contains, per section: `candidates_round1` (one
each from Translator/Poet/Songwriter), `critiques` (from all four
diagnostic agents, against every Round 1 candidate), `rebuttals` (the
one-pass cross-critique), `candidates_round4` (the recombination pass),
and `ruling` (the Judge's `final_line` plus its full rationale —
`sources_used`, `vetoes_applied`, `priority_tradeoffs_made`,
`disagreements_overruled`). Nothing is collapsed away: the transcript is
meant to be auditable end to end, the same way `WRITERS_ROOM.md` §7.3
specifies.

## Testing without an API key

```bash
python -m pytest tests/
```

`tests/test_pipeline_mock.py` runs the full pipeline against a fake LLM
client that returns canned, schema-valid responses — it verifies the round
structure, section-to-section room memory handoff, and data parsing all
work correctly without any network access or API key. It does not verify
prompt *quality* — only that the engine's control flow and schemas are
correct.

## What this does not do yet

This runs the "full room" process from `WRITERS_ROOM.md` on every section
of every song. `PRODUCTION_WORKFLOW.md` §9 and `WRITERS_ROOM.md` §9 both
note that the full room is meant for a song's highest-stakes lines, not
run uniformly at production scale — a lighter mode (skip diagnosis/cross-
critique for low-stakes sections) is a natural next addition, not yet
implemented here. There is also no video assembly, timing/sync, or visual
pipeline in this codebase — this engine produces the English lyric script
only, which is the input to `PRODUCTION_WORKFLOW.md` Stage 6 onward.
