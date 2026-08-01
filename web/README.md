# AURA — web frontend

A Next.js (App Router) + Tailwind frontend for Product 1, now wired to the
real Python engine end to end. Still local-only — no deployment, no auth.

## Run the full stack

Two processes, both from the repo root, in separate terminals:

```bash
# 1. The engine's HTTP API
export OPENAI_API_KEY=sk-...
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8000

# 2. The frontend
cd web
npm install
npm run dev
```

Open http://localhost:3000, paste a song, submit. What actually happens:

```
Paste lyrics → engine/text_ingest.py splits into sections → engine/pipeline.py
runs the real Writers' Room → server/mapping.py turns the ruling into plain
English → cached by content hash (server/cache.py) → frontend redirects to
/s/[id], a real, reloadable, shareable URL.
```

Submitting the exact same text again (any user, any session) skips the
engine entirely and serves the cached result instantly — see
`server/cache.py`.

## Architecture

- `app/api/adapt/route.ts` — thin proxy from the frontend to
  `server/main.py`. Components only ever call `fetch("/api/adapt")`; this
  is the one file that knows a Python service exists at all.
- `server/main.py` — FastAPI app. `POST /api/adapt` runs the engine (or
  serves the cache); `GET /api/adapt/{id}` backs the shareable page.
- `server/mapping.py` — translates `engine.pipeline.EngineResult` (Song
  DNA, deviations, dimension scores, all the internal machinery) into the
  frontend's plain `ExperienceResult` contract (`lib/types.ts`). This is
  the one place internal reasoning gets turned into a plain-English "why"
  sentence — the engine's own prompts are untouched.
- `app/s/[id]/page.tsx` — the actual shareable result page, server-rendered
  by fetching from the engine API directly.
- `app/page.tsx` — just the input screen and the loading sequence; on
  success it redirects to `/s/[id]`, it doesn't hold result state itself.

## What's intentionally not here

- No YouTube URL input on the homepage. The engine's YouTube ingestion
  (`engine/youtube_ingest.py`) always needs a human review/edit step before
  its output is trustworthy (see `docs/ENGINE.md`) — that doesn't fit
  "one input, one button, nothing else," so it isn't exposed as a
  consumer-facing feature.
- No internal terminology anywhere in the UI (Song DNA, Writers' Room,
  Burden of Change, dimension scores, invention penalty, etc.) — those are
  implementation details, not something a listener needs to know exists.
- No fabricated metrics (percentage match scores, fidelity scores) — if a
  number isn't actually computed, it isn't shown.
- No deployment. This is the "make the local flow work end to end first"
  stage on purpose — see the plan in this file's git history for why.
