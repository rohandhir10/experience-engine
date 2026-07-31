# Running the Engine

Two room implementations are available, both sharing the same Song DNA
analysis step:

- **`v1` (default)** — the minimal room from `docs/WRITERS_ROOM_V1.md`:
  Translator + Creative Adapter generate, the Judge triages using free
  routing signals and either rules immediately or names specific
  specialists (Cultural Historian / Native Speaker / Psychologist) to
  consult before ruling. 3 calls typical, ~6-7 worst case, per section.
- **`full`** — the original seven-agent room from `docs/WRITERS_ROOM.md`:
  all seven agents run on every section, five rounds, ~16 calls per
  section. Opt in for songs where that blanket coverage is worth the cost.

This is the code artifact for the design in those documents — read them
first if you haven't; this doc only covers running it.

## Setup

The engine also supports two model providers, behind the same
`client.complete_json(...)` interface everywhere else in the codebase —
swapping providers never touches Song DNA generation, the Writers' Room,
or the routing logic.

- **OpenAI (active default):**
  ```bash
  pip install -r requirements.txt
  export OPENAI_API_KEY=sk-...
  ```
- **Anthropic (kept in the codebase, inactive by default):**
  ```bash
  pip install -r requirements.txt
  export ANTHROPIC_API_KEY=sk-ant-...
  export AURA_PROVIDER=anthropic
  ```

Optional environment overrides (see `engine/config.py`):

- `AURA_PROVIDER` — `openai` (default) or `anthropic`.
- `AURA_OPENAI_MODEL` — defaults to `gpt-4o`.
- `AURA_ANTHROPIC_MODEL` — defaults to `claude-sonnet-5` (only relevant
  when `AURA_PROVIDER=anthropic`).
- `AURA_MAX_TOKENS` — defaults to `4096` per call (Song DNA and Judge calls
  request more headroom internally).

Never put an API key directly in a chat message, a committed file, or a
command someone else can see — export it as an environment variable in
whatever shell/session actually runs the engine. If a key is ever pasted
somewhere it shouldn't be, treat it as compromised and rotate it
immediately at the provider's dashboard, regardless of whether it was
actually used.

## Run it on a song

```bash
python -m engine.cli examples/sample_song.json          # V1, the default
python -m engine.cli examples/sample_song.json --room full   # original room
```

This writes `examples/sample_song.result.json` (the full transcript) and
prints the final assembled lyrics to stdout.

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
later sections stay consistent with earlier ones (`WRITERS_ROOM.md` §8,
`WRITERS_ROOM_V1.md` §7).

## Output format

`room_version` in the written `.result.json` records which room produced
the transcript.

**V1 (`room_version: "v1"`)**, per section: `candidates` (1 Translator
literal anchor + 5 Creative Adapter candidates, one per adaptation
philosophy — `maximum_fidelity`, `native_english_lyricist`,
`performance_first`, `emotion_first`, `genre_first` — each with a
`philosophy` field and self-reported `confidence`/`uncertainty_type` —
`WRITERS_ROOM_V1.md` §9.3), `routing_signals` (what fired and why —
cultural density, ambiguity, guarded vulnerability, low confidence, and
the specialists those signals suggested), `specialists_invoked` (which the
Judge actually called, 0-3), `specialist_critiques` (their critiques, if
any were called), and `ruling` — the Judge's `final_line` plus its full
rationale, now including `deviations` (the Burden-of-Change ledger: every
fragment that differs from the Translator's literal anchor, with a
justification tied to one of the five scored dimensions — empty is the
healthy default) and `dimension_scores` (Artistic Fidelity, Genre
Authenticity, Natural English, Voice Consistency, Singability & Rhythm —
`WRITERS_ROOM_V1.md` §9.1-9.2).

A `SectionInput` may also set `repeats` to an earlier section's name (a
chorus recurring verbatim later in the song) — that section's ruling and
Song DNA profile are reused directly at zero extra LLM cost instead of
re-running the room on identical text (see `examples/sadda_haq.json` for a
full song reconstructed this way).

**Full (`room_version: "full"`)**, per section: `candidates_round1` (one
each from Translator/Poet/Songwriter), `critiques` (all four diagnostic
agents against every Round 1 candidate), `rebuttals` (the cross-critique
pass), `candidates_round4` (the recombination pass), and `ruling`.

In both modes, `ruling` always carries the full auditable rationale —
`sources_used`, `vetoes_applied`, `priority_tradeoffs_made`,
`disagreements_overruled` — so a human reviewer can audit and override it
(`PRODUCTION_WORKFLOW.md` Stage 5) without re-deriving the tradeoff from
scratch.

## Testing without an API key

```bash
python -m pytest tests/
```

- `tests/test_writers_room_v1.py` — pure unit tests of the routing
  signals (`engine/routing.py`, zero LLM calls) plus fake-client tests of
  both V1 paths: the Judge ruling immediately (3 generative/triage calls)
  and the Judge requesting a specialist before ruling.
- `tests/test_pipeline_mock.py` — the full seven-agent room's control
  flow (all five rounds, room-memory handoff), pinned to
  `room_version="full"` since `v1` is now the default.

None of these verify prompt *quality* — only that each pipeline's control
flow, routing logic, and schemas are correct.

## What this does not do yet

Neither room mode has a video assembly, timing/sync, or visual pipeline —
this engine produces the English lyric script only, which is the input to
`PRODUCTION_WORKFLOW.md` Stage 6 onward. V1's routing is also not yet
tunable per production run (thresholds like the 0.7 confidence cutoff in
`engine/routing.py` are fixed, not configurable) — see
`WRITERS_ROOM_V1.md` §6 for the specific quality trade-offs that were
accepted to get the lower cost/latency, and what to check first if V1's
output quality regresses relative to `full`.
