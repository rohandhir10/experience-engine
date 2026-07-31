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

Before any re-expression begins, every song is analyzed into its **Song
DNA** — an artistic profile (emotional arc, imagery, motif, ambiguity,
symbolism, vulnerability, rhythm, repetition, narrative function, density,
style, songwriter intention) built around what the song is meant to make
someone feel, not what its words say. This is the representation every
Writers' Room agent works from:

[`docs/SONG_DNA.md`](docs/SONG_DNA.md)

## Running the engine

The `engine/` package is a working implementation of Song DNA analysis
followed by the full Writers' Room pipeline, callable via
`python -m engine.cli examples/sample_song.json`. See:

[`docs/ENGINE.md`](docs/ENGINE.md)