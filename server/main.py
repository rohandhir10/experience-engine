"""Local-only HTTP API wrapping the Python engine, for the Next.js frontend
(web/app/api/adapt/route.ts) to call. Run with:

    uvicorn server.main:app --reload --port 8000

from the repo root, with OPENAI_API_KEY already exported.

Two endpoints:
  POST /api/adapt      body: {"text": "..."} -> a full ExperienceResult
  GET  /api/adapt/{id} -> a previously computed ExperienceResult, for the
                          frontend's shareable /s/[id] page.

Same-text submissions are served from server/.cache without re-running
the engine (server/cache.py) - the id returned is also the frontend's
shareable URL slug.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.llm_client import LLMError, create_default_client
from engine.models import SongInput
from engine.pipeline import run_engine
from engine.text_ingest import split_into_sections

from . import cache
from .mapping import to_experience_result

app = FastAPI(title="AURA engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AdaptRequest(BaseModel):
    text: str


@app.post("/api/adapt")
def adapt(request: AdaptRequest) -> dict:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Paste a song first.")

    result_id = cache.content_id(text)
    cached = cache.get(result_id)
    if cached is not None:
        return cached

    try:
        sections = split_into_sections(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    song = SongInput(source_language="unspecified", sections=sections)

    try:
        client = create_default_client()
        engine_result = run_engine(song, client=client, room_version="v1")
        experience_result = to_experience_result(client, engine_result, result_id)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=f"The engine failed: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    cache.set(result_id, experience_result)
    return experience_result


@app.get("/api/adapt/{result_id}")
def get_adapt(result_id: str) -> dict:
    cached = cache.get(result_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No result found for this link.")
    return cached
