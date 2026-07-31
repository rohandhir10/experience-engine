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