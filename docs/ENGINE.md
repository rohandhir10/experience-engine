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

## Ingesting from a YouTube URL

The engine itself is still text-in, text-out — nothing below touches
`engine/pipeline.py`. `engine/youtube_ingest.py` is a separate preprocessing
step: it pulls a video's own subtitles/captions and writes a **draft**
`SongInput` JSON in the same shape as `examples/*.json`, for a human to
review and correct before it's ever run through the engine.

```bash
python -m engine.youtube_ingest "https://www.youtube.com/watch?v=VIDEO_ID"
# writes VIDEO_ID.draft.json

# then, after you've reviewed/edited it:
python -m engine.cli VIDEO_ID.draft.json
```

Options: `-o/--output` to name the file, `--languages` to prefer specific
transcript language codes (e.g. `--languages hi en`), `--gap-threshold` to
tune the silence-length (seconds) treated as a section break (default 3.0).

**What this can't fix, and doesn't pretend to:**

- **Section boundaries are a guess.** They're inferred from pauses between
  captions, not real verse/chorus structure — every draft's sections are
  named `section_1`, `section_2`, ... and its `context_note` says so
  explicitly. Rename and re-split them by hand before running the engine;
  do not treat the draft as ready to use.
- **Auto-generated captions are unreliable for singing.** YouTube's
  auto-generated ("ASR") captions are speech-to-text, and singing isn't
  speech — for non-English music in particular, they're often badly
  garbled. This module always prefers a manually-created transcript when
  one exists, and its `context_note` warning says clearly when what it
  found was auto-generated instead, so you know to check the text against
  the actual audio.
- **No transcript at all is a hard failure, not a fallback.** Many music
  videos have captions disabled or none uploaded. `youtube_ingest` reports
  this plainly (`Could not ingest this video: ...`) rather than silently
  producing something worse.

This is why the product should never advertise "paste a YouTube URL" as a
one-step feature — it's two steps, the second of which is a human review
the engine has no way to skip.

## Input format

```json
{
  "title": "optional",
  "source_language": "Korean",
  "context_note": "optional narrative context (EXPERIENCE_GRAPH.md §3.3)",
  "sections": [
    {"name": "verse_1", "source_text": "line one\nline two", "voice": "optional singer/speaker name"},
    {"name": "chorus", "source_text": "..."}
  ]
}
```

Section names must be unique, and a `repeats` reference must point at an
earlier section — both are validated at input time rather than failing
deep in the pipeline. `voice` attributes a section to a named
singer/speaker for multi-voice works (duets); voice consistency is then
judged within each voice rather than across the whole song, and room
memory labels prior rulings per voice. Omit it for single-voice works —
prompts are unchanged when it's absent. (V1 room only; the full room
accepts but ignores it, with a logged warning.)

`target_language` is also a field on the input (defaults to `"English"`),
threaded through every prompt in `engine/prompts.py` rather than
hardcoded — but **English is the only supported output today**; this
exists purely so a future target language never requires another prompt
redesign, not because anything else is actually supported yet. Don't set
it to anything else expecting it to work.

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
`philosophy` field, self-reported `confidence`/`uncertainty_type`, and a
`syllable_count` computed deterministically in code (`engine/rhythm.py`,
CMU Pronouncing Dictionary via `pronouncing`, English output only — `None`
otherwise) rather than by the model — `WRITERS_ROOM_V1.md` §9.3, §9.6),
`routing_signals` (what fired and why — cultural density, ambiguity,
guarded vulnerability, low confidence, and the specialists those signals
suggested), `specialists_invoked` (which the Judge actually called, 0-3),
`specialist_critiques` (their critiques, if any were called), and `ruling`
— the Judge's `final_line` plus its full rationale, now including
`deviations` (the Burden-of-Change ledger: every fragment that differs
from the Translator's literal anchor, with a justification tied to one of
the five scored dimensions — empty is the healthy default),
`dimension_scores` (Artistic Fidelity, Genre Authenticity, Natural
English, Voice Consistency, Singability & Rhythm — grounded for the last
of these by each candidate's computed `syllable_count` and, when the
source is Latin-script, a rough `source_syllable_estimate` — `WRITERS_ROOM_V1.md`
§9.1-9.2, §9.6), and `invention_penalty` (an aggregate 0-1 score across all
candidates reviewed for how much of the deviation ledger leaned on weak
"sounds better" justifications rather than specific reasons —
`WRITERS_ROOM_V1.md` §9.6).

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
