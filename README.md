# experience-engine

## AURA

AURA (Adaptive Understanding & Re-expression Architecture) is a research-grade
system design for preserving emotional impact, poetic meaning, cultural
context, and narrative intent across languages — deliberately not a
translation engine. See the full technical design document:

[`docs/AURA_ARCHITECTURE.md`](docs/AURA_ARCHITECTURE.md)

The **Experience Graph** is AURA's canonical central representation — a
language-independent graph every lyric, dialogue line, or poem is compiled
into before any re-expression occurs. See:

[`docs/EXPERIENCE_GRAPH.md`](docs/EXPERIENCE_GRAPH.md)

Before investing in that architecture, the core hypothesis — that AI can
generate lyric re-expressions bilingual speakers judge as more emotionally
faithful than conventional translation — needs to be tested with the
smallest possible experiment. See:

[`docs/FEASIBILITY_EXPERIMENT.md`](docs/FEASIBILITY_EXPERIMENT.md)

The internal production engine that turns this into daily output — an
editorial workflow from song selection to a finished lyric video, for
Hindi, Japanese, Korean, Arabic, Russian, and Spanish → English — is
specified in:

[`docs/PRODUCTION_WORKFLOW.md`](docs/PRODUCTION_WORKFLOW.md)

For the highest-stakes lines in a song, drafting is done by a multi-agent
creative room — specialist critique modeled on Pixar's Braintrust, not a
translation committee — instead of a single generate-and-edit pass:

[`docs/WRITERS_ROOM.md`](docs/WRITERS_ROOM.md)

**Version 1 default:** to prove the core hypothesis quickly rather than
maximize sophistication, the engine defaults to a minimal-agent room —
Translator + Creative Adapter (Poet/Songwriter merged) generate, and the
Judge invokes Cultural Historian / Native Speaker / Psychologist only when
it decides they're needed, based on routing signals from Song DNA and the
candidates' own reported confidence. The full seven-agent room above
remains available as an opt-in mode. See:

[`docs/WRITERS_ROOM_V1.md`](docs/WRITERS_ROOM_V1.md)

Before any re-expression begins, every song is analyzed into its **Song
DNA** — an artistic profile (emotional arc, imagery, motif, ambiguity,
symbolism, vulnerability, rhythm, repetition, narrative function, density,
style, songwriter intention) built around what the song is meant to make
someone feel, not what its words say. This is the representation every
Writers' Room agent works from:

[`docs/SONG_DNA.md`](docs/SONG_DNA.md)

## Running the engine

The `engine/` package is a working implementation of Song DNA analysis
followed by the Writers' Room pipeline — V1 minimal room by default, or
the full seven-agent room via `--room full` — callable via
`python -m engine.cli examples/sample_song.json`. It calls OpenAI by
default (`OPENAI_API_KEY`); Anthropic is kept in the codebase as an
inactive alternate provider (`AURA_PROVIDER=anthropic`). See:

[`docs/ENGINE.md`](docs/ENGINE.md)

## Product 1: the web frontend

A production-quality frontend (Next.js + Tailwind) now runs against the
real engine end to end, through a local FastAPI service (`server/`) —
paste a song, get a shareable result page, with same-song requests served
from a cache instead of re-running the engine. See:

[`web/README.md`](web/README.md)