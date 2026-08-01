# AURA — web frontend

A Next.js (App Router) + Tailwind frontend for Product 1. Local-only for
now — no deployment, no auth, no backend wiring yet.

## Run it

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000. Paste anything into the box and submit — the
API route (`app/api/adapt/route.ts`) always returns a fixed sample result
right now (the Agar Tum Saath Ho comparison from `lib/sample-data.ts`),
regardless of what you paste. That route is the integration seam: swap its
body for a real call to the Python engine (e.g. a small FastAPI service
wrapping `engine/pipeline.py`) when that's ready, and nothing else in the
frontend needs to change — `ExperienceResult` in `lib/types.ts` is the
contract both sides agree on.

## What's intentionally not here

- No YouTube URL input on the homepage. The engine's YouTube ingestion
  (`engine/youtube_ingest.py`) always needs a human review/edit step before
  its output is trustworthy (see `docs/ENGINE.md`) — that doesn't fit
  "one input, one button, nothing else," so it isn't exposed as a
  consumer-facing feature yet.
- No internal terminology anywhere in the UI (Song DNA, Writers' Room,
  Burden of Change, dimension scores, invention penalty, etc.) — those are
  implementation details, not something a listener needs to know exists.
- No fabricated metrics (percentage match scores, fidelity scores) — if a
  number isn't actually computed, it isn't shown.
