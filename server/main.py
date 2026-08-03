"""HTTP API wrapping the Python engine, for the Next.js frontend
(web/app/api/adapt/route.ts) to call. Run locally with:

    uvicorn server.main:app --reload --port 8000

or in production via the Dockerfile at the repo root. OPENAI_API_KEY must
be set in the environment either way.

Endpoints:
  GET  /health         -> liveness probe for hosting platforms
  POST /api/adapt      body: {"text": "..."} -> a full ExperienceResult
  GET  /api/adapt/{id} -> a previously computed ExperienceResult, for the
                          frontend's shareable /s/[id] page.

Operational behavior:
  - Same-text submissions are served from server/.cache without re-running
    the engine (server/cache.py); the id doubles as the share-URL slug.
  - Input is length-capped (AURA_MAX_INPUT_CHARS) so one paste can't run
    an unbounded number of engine sections.
  - A simple per-IP daily quota (AURA_DAILY_LIMIT, in-memory, resets on
    restart) caps LLM spend from any single client. Cache hits don't
    count against it. Set to 0 to disable.
  - Endpoints are plain `def`, so FastAPI runs them in its threadpool —
    the engine is synchronous and a full song takes tens of seconds; this
    keeps the event loop free without touching the engine.
  - Structured request logging: one line per request with duration and
    cache hit/miss, so cost and latency are visible from stdout.
  - Every run is verified (engine/verify.py) against the Burden of Change
    constitution and, if that finds an error-severity issue, corrected
    once (engine/pipeline.py's bounded corrective pass) before shipping.
    Verification runs a second time after that pass purely for logging —
    it does not loop or retry again — so anything still wrong stays
    visible in production logs instead of only being checkable by hand
    via the CLI's --verify flag.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine import config
from engine.llm_client import LLMError, create_default_client
from engine.models import SUPPORTED_TARGET_LANGUAGES, SongInput
from engine.pipeline import run_engine
from engine.rhythm import is_latin_script
from engine.text_ingest import split_into_sections
from engine.verify import verify_result

from . import cache, db
from .mapping import to_experience_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("aura.server")

MAX_INPUT_CHARS = int(os.environ.get("AURA_MAX_INPUT_CHARS", "8000"))
DAILY_LIMIT = int(os.environ.get("AURA_DAILY_LIMIT", "10"))
ALLOWED_ORIGINS = os.environ.get(
    "AURA_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")

@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Best-effort: DATABASE_URL isn't set in local/test environments that
    # never touch Postgres, and nothing on the /api/adapt path depends on
    # it yet, so a missing or unreachable database logs a warning here
    # rather than crashing the whole API.
    if not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL not set - skipping database init")
    else:
        try:
            db.create_all()
            logger.info("database tables ready")
        except Exception:
            logger.exception("database init failed")
    yield


app = FastAPI(title="AURA engine API", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# {(day, ip): engine runs today}. In-memory on purpose: this is a
# single-instance cost guard, not billing infrastructure. Restarting the
# process resets it, which is acceptable at this stage.
_daily_runs: dict[tuple[str, str], int] = defaultdict(int)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_quota(ip: str) -> None:
    if DAILY_LIMIT <= 0:
        return
    key = (date.today().isoformat(), ip)
    if _daily_runs[key] >= DAILY_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=(
                "You've reached today's limit for new songs. Already-"
                "processed songs are still free to view and share."
            ),
        )
    _daily_runs[key] += 1


class AdaptRequest(BaseModel):
    text: str
    # "English" (the original, only-ever-supported direction) unless the
    # caller asks for one of the reverse pairings — see
    # engine/models.py::SUPPORTED_TARGET_LANGUAGES for exactly which
    # directions actually exist.
    target_language: str = "English"


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> dict:
    from sqlalchemy import text

    try:
        with db.get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unreachable: {exc}") from exc


@app.post("/api/adapt")
def adapt(request: AdaptRequest, http_request: Request) -> dict:
    started = time.monotonic()
    ip = _client_ip(http_request)

    text = request.text.strip()
    target_language = request.target_language.strip() or "English"
    if not text:
        raise HTTPException(status_code=400, detail="Paste a song first.")
    if len(text) > MAX_INPUT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"That's over the {MAX_INPUT_CHARS:,}-character limit for one "
                "song. Try a single song rather than a whole album."
            ),
        )
    if target_language not in SUPPORTED_TARGET_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{target_language!r} isn't a supported target language. "
                f"AURA currently supports: {', '.join(sorted(SUPPORTED_TARGET_LANGUAGES))}."
            ),
        )
    if target_language != "English" and not is_latin_script(text):
        # A real (if imperfect) guard, not full language detection: every
        # non-English target direction expects an English source, and a
        # majority-non-Latin-script paste is a strong signal this is one
        # of the *other* directions (Hindi/Korean/Japanese/Spanish source)
        # that this target language was never built or verified for.
        raise HTTPException(
            status_code=400,
            detail=(
                f"Adapting into {target_language} expects English lyrics as "
                "the source. This text doesn't look like English."
            ),
        )

    result_id = cache.content_id(text, target_language=target_language)
    cached = cache.get(result_id)
    if cached is not None:
        logger.info(
            "adapt id=%s ip=%s target=%s cache=hit duration=%.2fs",
            result_id, ip, target_language, time.monotonic() - started,
        )
        return cached

    # A near-identical paste of a song already in the database (a typo, a
    # reflowed line break, stray punctuation) won't match the exact hash
    # above but is, for all practical purposes, a repeat - cache.find_similar
    # only reports a match above a conservative similarity threshold, since
    # a wrong match here would silently serve one song's adaptation for a
    # different one. Also stored under this exact text's own id, so the
    # next byte-identical repeat of *this* paste is a fast exact hit too.
    similar = cache.find_similar(text, target_language=target_language)
    if similar is not None:
        matched_id, matched_result, similarity = similar
        cache.set(result_id, matched_result, source_text=text, target_language=target_language)
        logger.info(
            "adapt id=%s ip=%s target=%s cache=fuzzy_hit matched=%s similarity=%.3f duration=%.2fs",
            result_id, ip, target_language, matched_id, similarity, time.monotonic() - started,
        )
        return matched_result

    _check_quota(ip)

    try:
        sections = split_into_sections(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        song = SongInput(
            source_language="unspecified",
            target_language=target_language,
            sections=sections,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "adapt id=%s ip=%s target=%s cache=miss sections=%d chars=%d starting engine run",
        result_id, ip, target_language, len(sections), len(text),
    )

    try:
        client = create_default_client()
        # apply_corrective_pass: verify.py runs once against the raw
        # output, and any error-severity finding gets one bounded re-judge
        # (engine/pipeline.py's Phase 2 corrective pass) before this ships
        # to a real user — not just logged after the fact.
        engine_result = run_engine(
            song, client=client, room_version="v1", apply_corrective_pass=True
        )
        # explain_why is presentation text, not adaptation reasoning — the
        # one call in this request that's a legitimate candidate for a
        # cheaper model (engine/config.py's EXPLAIN_WHY_MODEL). A separate
        # client so its calls are still fully measured (merged into the
        # cost log below), just not on the same model as the rest.
        explain_why_client = create_default_client(model=config.EXPLAIN_WHY_MODEL)
        experience_result = to_experience_result(
            client, engine_result, result_id, explain_why_client=explain_why_client
        )
    except LLMError as exc:
        logger.error("adapt id=%s engine failure: %s", result_id, exc)
        raise HTTPException(
            status_code=502,
            detail="The engine hit a problem processing this song. Try again in a moment.",
        ) from exc
    except RuntimeError as exc:
        logger.error("adapt id=%s configuration failure: %s", result_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Verified a second time here, after the corrective pass already ran
    # inside run_engine — this call never triggers another correction, it
    # only makes what's still true (if anything) visible in production
    # logs, since nothing was checking this in the deployed web app until
    # now.
    report = verify_result(engine_result.to_dict())
    errors = [f for f in report.all_findings if f.severity == "error"]
    warnings = [f for f in report.all_findings if f.severity == "warning"]
    if errors:
        logger.warning(
            "adapt id=%s shipped with %d unresolved verify.py error(s) after "
            "the corrective pass: %s",
            result_id,
            len(errors),
            "; ".join(f"{f.law} ({f.section})" for f in errors),
        )
    logger.info(
        "adapt id=%s verify errors=%d warnings=%d laws=[%s]",
        result_id,
        len(errors),
        len(warnings),
        ", ".join(sorted({f.law for f in errors + warnings})),
    )

    cache.set(result_id, experience_result, source_text=text, target_language=target_language)
    # Measured, not estimated (engine/models.py::LLMCallRecord) — every
    # real API call this request made, so cost/latency stays visible in
    # production logs instead of only being knowable after building a
    # separate benchmark. Aggregated per stage since a section-by-section
    # breakdown is more log lines than one request needs by default.
    # Includes explain_why_client's calls too — a different model, but
    # still real cost from this request, and it would otherwise vanish
    # from this total silently.
    calls = client.call_log + explain_why_client.call_log
    tokens_by_stage: dict[tuple[str, str], list[int]] = {}
    for record in calls:
        counts = tokens_by_stage.setdefault((record.stage, record.model), [0, 0])
        counts[0] += record.prompt_tokens
        counts[1] += record.completion_tokens
    stage_summary = ", ".join(
        f"{stage}[{model}]={prompt}p/{completion}c"
        for (stage, model), (prompt, completion) in sorted(tokens_by_stage.items())
    )
    total_prompt = sum(r.prompt_tokens for r in calls)
    total_completion = sum(r.completion_tokens for r in calls)
    llm_latency = sum(r.latency_seconds for r in calls)
    logger.info(
        "adapt id=%s ip=%s cache=stored sections=%d duration=%.2fs "
        "llm_calls=%d llm_latency=%.2fs prompt_tokens=%d completion_tokens=%d "
        "by_stage=[%s]",
        result_id, ip, len(sections), time.monotonic() - started,
        len(calls), llm_latency, total_prompt, total_completion, stage_summary,
    )
    return experience_result


@app.get("/api/adapt/{result_id}")
def get_adapt(result_id: str) -> dict:
    cached = cache.get(result_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No result found for this link.")
    return cached
