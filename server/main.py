"""HTTP API wrapping the Python engine, for the Next.js frontend
(web/app/api/adapt/route.ts) to call. Run locally with:

    uvicorn server.main:app --reload --port 8000

or in production via the Dockerfile at the repo root. OPENAI_API_KEY must
be set in the environment either way.

Endpoints:
  GET  /health              -> liveness probe for hosting platforms
  POST /api/adapt           body: {"text": "..."} -> a full ExperienceResult
                            (blocking - see the job endpoints below for
                            anything that might run past a serverless
                            function's timeout).
  GET  /api/adapt/{id}      -> a previously computed ExperienceResult, for
                               the frontend's shareable /s/[id] page.
  POST /api/adapt/start     body: same as /api/adapt -> {"status": "done",
                            "result": ...} on a cache hit, or
                            {"status": "pending", "job_id": ...} otherwise
                            - the engine run continues in a background
                            thread past this request's return.
  GET  /api/adapt/jobs/{id} -> {"status": "pending"|"running"|"done"|
                            "error", "result": ..., "error": ...} - poll
                            until status is "done" or "error".

Why /api/adapt/start exists: a real multi-section song run is several
sections deep, each running 3-7 sequential LLM calls of its own (Song DNA
once, then per section: Translator, Creative Adapter, Judge triage, up to
3 specialists, Judge final) — a full song routinely takes minutes, well
past Vercel's 60s Hobby-plan function ceiling (web/app/api/adapt/
route.ts's maxDuration comment). /api/adapt itself is unchanged and still
useful for short songs/local dev/anything not bound by a serverless
timeout; /api/adapt/start moves the actual engine run into a background
thread that outlives the HTTP request that started it (this process is a
long-lived Railway container, not a serverless function, so nothing here
needs an external job queue at today's scale), and the caller polls
/api/adapt/jobs/{id} — itself a fast dict lookup — until it's done.

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
import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine import config
from engine import youtube_ingest
from engine.llm_client import LLMError, create_default_client
from engine.models import SUPPORTED_LANGUAGES, SectionInput, SongInput
from engine.pipeline import run_engine
from engine.text_ingest import split_into_sections
from engine.verify import verify_result
from engine.youtube_ingest import IngestError

from . import accounts, cache, db, jobs, quota
from .mapping import to_experience_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("aura.server")

MAX_INPUT_CHARS = int(os.environ.get("AURA_MAX_INPUT_CHARS", "8000"))
DAILY_LIMIT = int(os.environ.get("AURA_DAILY_LIMIT", "10"))
# Shared secret between the Next.js server and this API, for the
# account endpoints (/api/users/sync, /api/me/*) and for trusting a
# user id forwarded on adapt requests. The Next.js side is the party
# that actually verified the Google sign-in (Auth.js); this secret is
# how it proves a request came from it and not from a browser talking
# to this API directly. Unset -> account endpoints answer 503 and
# forwarded user ids are ignored (accounts off, everything else works).
INTERNAL_API_SECRET = os.environ.get("AURA_INTERNAL_API_SECRET", "")
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
            # Alembic (server/migrations), not bare create_all - the
            # baseline revision is checkfirst so this is safe on both a
            # fresh database and the already-deployed one. See
            # server/db.py::migrate_to_head.
            db.migrate_to_head()
            logger.info("database schema at migration head")
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

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _require_internal_secret(request: Request) -> None:
    if not INTERNAL_API_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Accounts are not configured on this deployment (AURA_INTERNAL_API_SECRET unset).",
        )
    if request.headers.get("x-aura-internal-secret") != INTERNAL_API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid internal secret.")


def _required_user_id(request: Request) -> str:
    """For the /api/me/* endpoints, which are meaningless without a user.
    The internal secret is checked separately by _require_internal_secret
    — this only pulls the id out."""
    user_id = request.headers.get("x-aura-user-id")
    if not user_id:
        raise HTTPException(status_code=400, detail="X-Aura-User-Id header is required.")
    return user_id


def _authed_user_id(request: Request) -> str | None:
    """The signed-in user's id, forwarded by the Next.js server on adapt
    requests — honored ONLY alongside the internal secret, since anyone
    can put a header on a request but only the Next.js server (which
    verified the Google sign-in) knows the secret. Returns None rather
    than raising: a missing/bad pairing means the request proceeds as
    anonymous, exactly like before accounts existed — history is an
    enhancement to an adapt request, never a gate on it."""
    user_id = request.headers.get("x-aura-user-id")
    if not user_id:
        return None
    if not INTERNAL_API_SECRET:
        return None
    if request.headers.get("x-aura-internal-secret") != INTERNAL_API_SECRET:
        return None
    return user_id


def _check_quota(ip: str) -> None:
    # server/quota.py: Postgres-backed (atomic, safe across more than one
    # process/instance) when DATABASE_URL is set, an in-memory dict
    # otherwise - see that module's docstring.
    if not quota.check_and_increment(ip, DAILY_LIMIT):
        raise HTTPException(
            status_code=429,
            detail=(
                "You've reached today's limit for new songs. Already-"
                "processed songs are still free to view and share."
            ),
        )


class YoutubeSectionTiming(BaseModel):
    start: float
    end: float


class AdaptRequest(BaseModel):
    text: str
    # "English" (the original, only-ever-supported direction) unless the
    # caller asks for one of the other pairings — see
    # engine/models.py::SUPPORTED_LANGUAGES for the full roster. Any two
    # distinct languages from it are a supported direction.
    target_language: str = "English"
    # "unspecified" lets the engine auto-detect, same as always - only
    # actually safe when target_language == "English" (every source
    # language this product has ever tested funnels into English, so
    # auto-detect there is well-trodden). Every other direction requires
    # this to be set explicitly and to differ from target_language - see
    # adapt()'s validation below for why "unspecified" isn't trusted
    # there anymore (it used to be, guarded by a Latin-script heuristic;
    # that heuristic assumed a non-English target always meant an English
    # source, which stopped being true the moment direct pairs like
    # Hindi -> Korean were allowed).
    source_language: str = "unspecified"
    # Both set together, only when this text came from /api/youtube-draft
    # and the user didn't restructure the section breaks while reviewing
    # it (see adapt()'s length check below) — lets the result page sync
    # playback to a real video instead of just embedding it decoratively.
    # The engine itself never sees these; timing is server/frontend-only
    # bookkeeping, matched to sections purely by position.
    youtube_video_id: str | None = None
    youtube_section_timings: list[YoutubeSectionTiming] | None = None


class YoutubeDraftRequest(BaseModel):
    url: str
    preferred_languages: list[str] | None = None


class UserSyncRequest(BaseModel):
    google_sub: str
    email: str | None = None
    display_name: str | None = None


class FavoriteRequest(BaseModel):
    is_favorite: bool


class CollectionRequest(BaseModel):
    name: str


class MembershipRequest(BaseModel):
    member: bool


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/youtube-draft")
def youtube_draft(request: YoutubeDraftRequest) -> dict:
    """Fetches a video's own captions and groups them into a draft the
    frontend drops into the same textarea a manual paste would use — see
    engine/youtube_ingest.py::build_web_draft's docstring for why this
    is still a review step, not a direct pipe into the engine.
    """
    try:
        return youtube_ingest.build_web_draft(request.url, request.preferred_languages)
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/users/sync")
def users_sync(request: UserSyncRequest, http_request: Request) -> dict:
    """Called by the Next.js server from Auth.js's jwt callback on
    sign-in — upserts the user and returns {id, plan} for the session
    token. See server/accounts.py for the identity split."""
    _require_internal_secret(http_request)
    if not request.google_sub.strip():
        raise HTTPException(status_code=400, detail="google_sub is required.")
    result = accounts.sync_user(
        request.google_sub.strip(), request.email, request.display_name
    )
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Accounts need a database (DATABASE_URL is unset on this deployment).",
        )
    return result


@app.get("/api/me/adaptations")
def me_adaptations(
    http_request: Request,
    favorites_only: bool = False,
    collection_id: str | None = None,
) -> dict:
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    try:
        adaptations = accounts.list_adaptations(
            user_id, favorites_only=favorites_only, collection_id=collection_id
        )
    except ValueError as exc:  # malformed collection_id UUID
        raise HTTPException(status_code=400, detail="Invalid collection id.") from exc
    return {"adaptations": adaptations}


# --- Collections -----------------------------------------------------------
# Every handler here delegates its authorization to accounts.py, whose
# queries are scoped by user_id; a False return is always rendered as 404
# so "not yours" and "doesn't exist" stay indistinguishable to a caller.


def _collection_name(raw: str) -> str:
    name = raw.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Give the collection a name.")
    if len(name) > 100:
        raise HTTPException(
            status_code=400, detail="Collection names are limited to 100 characters."
        )
    return name


@app.get("/api/me/collections")
def me_collections(http_request: Request) -> dict:
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    return {"collections": accounts.list_collections(user_id)}


@app.post("/api/me/collections")
def me_create_collection(request: CollectionRequest, http_request: Request) -> dict:
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    created = accounts.create_collection(user_id, _collection_name(request.name))
    if created is None:
        raise HTTPException(
            status_code=503,
            detail="Collections need a database (DATABASE_URL is unset on this deployment).",
        )
    return created


@app.patch("/api/me/collections/{collection_id}")
def me_rename_collection(
    collection_id: str, request: CollectionRequest, http_request: Request
) -> dict:
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    name = _collection_name(request.name)
    if not _collection_write(accounts.rename_collection, user_id, collection_id, name):
        raise HTTPException(status_code=404, detail="No such collection.")
    return {"id": collection_id, "name": name}


@app.delete("/api/me/collections/{collection_id}")
def me_delete_collection(collection_id: str, http_request: Request) -> dict:
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    if not _collection_write(accounts.delete_collection, user_id, collection_id):
        raise HTTPException(status_code=404, detail="No such collection.")
    return {"id": collection_id, "deleted": True}


@app.post("/api/me/collections/{collection_id}/adaptations/{result_id}")
def me_set_collection_membership(
    collection_id: str,
    result_id: str,
    request: MembershipRequest,
    http_request: Request,
) -> dict:
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    if not _collection_write(
        accounts.set_collection_membership,
        user_id,
        collection_id,
        result_id,
        request.member,
    ):
        raise HTTPException(
            status_code=404, detail="No such collection or adaptation in your account."
        )
    return {"collectionId": collection_id, "resultId": result_id, "member": request.member}


def _collection_write(fn, user_id: str, collection_id: str, *args) -> bool:
    """Runs one accounts.py collection write, turning a malformed
    collection id into the same 404 a nonexistent one gets — a caller
    probing with garbage learns nothing a caller probing with a
    well-formed guess wouldn't."""
    try:
        return fn(user_id, collection_id, *args)
    except ValueError:
        return False


@app.get("/api/me/adaptations/{result_id}")
def me_adaptation(result_id: str, http_request: Request) -> dict:
    """One history entry, for the result page's save controls. `saved`
    false means this user has no history row for it — they're looking at
    someone else's shared link, or their own from before accounts."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    entry = accounts.get_adaptation(user_id, result_id)
    return {"saved": entry is not None, "adaptation": entry}


@app.post("/api/me/adaptations/{result_id}/save")
def me_save_adaptation(result_id: str, http_request: Request) -> dict:
    """Adds a result to the caller's history so it can be favorited or
    filed. Idempotent; 404s for a result that was never computed."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    if not accounts.save_adaptation(user_id, result_id):
        raise HTTPException(status_code=404, detail="No such adaptation.")
    return {"resultId": result_id, "saved": True}


@app.post("/api/me/adaptations/{result_id}/favorite")
def me_set_favorite(
    result_id: str, request: FavoriteRequest, http_request: Request
) -> dict:
    """Toggles the favorite flag on one of the caller's own history rows.
    A result the user has never adapted 404s — accounts.set_favorite
    scopes the lookup by user_id, so this can't be used to probe or flip
    another user's history."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    if not accounts.set_favorite(user_id, result_id, request.is_favorite):
        raise HTTPException(
            status_code=404, detail="No adaptation found in your history for this song."
        )
    return {"resultId": result_id, "isFavorite": request.is_favorite}


@app.get("/health/db")
def health_db() -> dict:
    from sqlalchemy import text

    try:
        with db.get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unreachable: {exc}") from exc


def _validate_adapt_request(request: AdaptRequest) -> tuple[str, str, str]:
    """Every check /api/adapt used to do inline, shared with /api/adapt/
    start so the two endpoints can't drift on what counts as a valid
    request. Raises HTTPException; returns (text, target_language,
    source_language), each already stripped/defaulted."""
    text = request.text.strip()
    target_language = request.target_language.strip() or "English"
    source_language = request.source_language.strip() or "unspecified"
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
    if target_language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{target_language!r} isn't a supported target language. "
                f"AURA currently supports: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
            ),
        )
    if source_language != "unspecified":
        if source_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{source_language!r} isn't a supported source language. "
                    f"AURA currently supports: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
                ),
            )
        if source_language == target_language:
            raise HTTPException(
                status_code=400,
                detail="Source and target language can't be the same.",
            )
    elif target_language != "English":
        # "unspecified" source used to be trusted here too, guarded by a
        # Latin-script heuristic that assumed a non-English target always
        # meant an English source. That assumption broke the moment direct
        # pairs (Hindi -> Korean, say) became possible - a Devanagari
        # paste bound for Korean is no longer obviously a mistake, so
        # guessing is no longer safe. Ask instead of guessing.
        raise HTTPException(
            status_code=400,
            detail=(
                f"Adapting into {target_language} needs a source language "
                "specified - pick which language the pasted lyrics are in."
            ),
        )
    return text, target_language, source_language


def _build_song(
    text: str, target_language: str, source_language: str
) -> tuple[list[SectionInput], SongInput]:
    try:
        sections = split_into_sections(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        song = SongInput(
            source_language=source_language,
            target_language=target_language,
            sections=sections,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return sections, song


def _record_history(user_id: str | None, result_id: str, source_language: str) -> None:
    """History is an enhancement to an adapt request, never a gate on it —
    a failure here is logged and swallowed so the user still gets their
    result."""
    if not user_id:
        return
    try:
        accounts.record_adaptation(user_id, result_id, source_language)
    except Exception:
        logger.exception("failed to record history user=%s result=%s", user_id, result_id)


def _run_adaptation(
    request: AdaptRequest,
    result_id: str,
    text: str,
    target_language: str,
    source_language: str,
    sections: list[SectionInput],
    song: SongInput,
    ip: str,
    started: float,
    log_prefix: str = "adapt",
    user_id: str | None = None,
) -> dict:
    """The actual engine run: Song DNA -> Writers' Room -> Judge, then
    verification and cache write. Shared by the blocking /api/adapt
    endpoint and the background job /api/adapt/start kicks off - callers
    differ only in how they turn an LLMError/RuntimeError into a response
    (an HTTPException here, a job's stored `error` string there), so
    those propagate uncaught rather than being translated in here.
    """
    logger.info(
        "%s id=%s ip=%s source=%s target=%s cache=miss sections=%d chars=%d starting engine run",
        log_prefix, result_id, ip, source_language, target_language, len(sections), len(text),
    )

    client = create_default_client()
    # apply_corrective_pass: verify.py runs once against the raw output,
    # and any error-severity finding gets one bounded re-judge
    # (engine/pipeline.py's Phase 2 corrective pass) before this ships to
    # a real user — not just logged after the fact.
    engine_result = run_engine(
        song, client=client, room_version="v1", apply_corrective_pass=True
    )
    # explain_why is presentation text, not adaptation reasoning — the one
    # call in this request that's a legitimate candidate for a cheaper
    # model (engine/config.py's EXPLAIN_WHY_MODEL). A separate client so
    # its calls are still fully measured (merged into the cost log
    # below), just not on the same model as the rest.
    explain_why_client = create_default_client(model=config.EXPLAIN_WHY_MODEL)
    experience_result = to_experience_result(
        client, engine_result, result_id, explain_why_client=explain_why_client
    )

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
            "%s id=%s shipped with %d unresolved verify.py error(s) after "
            "the corrective pass: %s",
            log_prefix,
            result_id,
            len(errors),
            "; ".join(f"{f.law} ({f.section})" for f in errors),
        )
    logger.info(
        "%s id=%s verify errors=%d warnings=%d laws=[%s]",
        log_prefix,
        result_id,
        len(errors),
        len(warnings),
        ", ".join(sorted({f.law for f in errors + warnings})),
    )

    # Song-level (a correlation needs the whole song's sections, not one),
    # so it doesn't fit the per-section shape mapping.py already builds -
    # attached here instead. None for non-English targets or songs with
    # too few CMU-resolvable sections; the frontend must treat null as
    # "not computed," never as a zero score.
    experience_result["phonemeRepetitionSimilarity"] = report.phoneme_repetition_similarity

    if request.youtube_video_id and request.youtube_section_timings:
        timings = request.youtube_section_timings
        result_sections = experience_result["sections"]
        if len(timings) == len(result_sections):
            experience_result["videoId"] = request.youtube_video_id
            for section, timing in zip(result_sections, timings):
                section["startSeconds"] = timing.start
                section["endSeconds"] = timing.end
        else:
            # The user added/removed a section break while reviewing the
            # draft — positional timing no longer lines up with anything
            # real, so this drops it rather than guess at a new mapping.
            logger.info(
                "%s id=%s youtube timing discarded: %d timings vs %d sections",
                log_prefix, result_id, len(timings), len(result_sections),
            )

    cache.set(
        result_id,
        experience_result,
        source_text=text,
        target_language=target_language,
        source_language=source_language,
    )
    _record_history(user_id, result_id, source_language)
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
        "%s id=%s ip=%s cache=stored sections=%d duration=%.2fs "
        "llm_calls=%d llm_latency=%.2fs prompt_tokens=%d completion_tokens=%d "
        "by_stage=[%s]",
        log_prefix, result_id, ip, len(sections), time.monotonic() - started,
        len(calls), llm_latency, total_prompt, total_completion, stage_summary,
    )
    return experience_result


@app.post("/api/adapt")
def adapt(request: AdaptRequest, http_request: Request) -> dict:
    started = time.monotonic()
    ip = _client_ip(http_request)
    user_id = _authed_user_id(http_request)
    text, target_language, source_language = _validate_adapt_request(request)

    result_id = cache.content_id(text, target_language=target_language, source_language=source_language)
    cached = cache.get(result_id)
    if cached is not None:
        # A cache hit is still this user asking for this song — history
        # records the relationship, not the compute.
        _record_history(user_id, result_id, source_language)
        logger.info(
            "adapt id=%s ip=%s source=%s target=%s cache=hit duration=%.2fs",
            result_id, ip, source_language, target_language, time.monotonic() - started,
        )
        return cached

    # A near-identical paste of a song already in the database (a typo, a
    # reflowed line break, stray punctuation) won't match the exact hash
    # above but is, for all practical purposes, a repeat - cache.find_similar
    # only reports a match above a conservative similarity threshold, since
    # a wrong match here would silently serve one song's adaptation for a
    # different one. Also stored under this exact text's own id, so the
    # next byte-identical repeat of *this* paste is a fast exact hit too.
    similar = cache.find_similar(text, target_language=target_language, source_language=source_language)
    if similar is not None:
        matched_id, matched_result, similarity = similar
        cache.set(
            result_id,
            matched_result,
            source_text=text,
            target_language=target_language,
            source_language=source_language,
        )
        _record_history(user_id, result_id, source_language)
        logger.info(
            "adapt id=%s ip=%s source=%s target=%s cache=fuzzy_hit matched=%s similarity=%.3f duration=%.2fs",
            result_id, ip, source_language, target_language, matched_id, similarity,
            time.monotonic() - started,
        )
        return matched_result

    _check_quota(ip)
    sections, song = _build_song(text, target_language, source_language)

    try:
        return _run_adaptation(
            request, result_id, text, target_language, source_language, sections, song, ip, started,
            user_id=user_id,
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


@app.get("/api/adapt/{result_id}")
def get_adapt(result_id: str) -> dict:
    cached = cache.get(result_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No result found for this link.")
    return cached


# Bounds how many engine runs can be mid-flight at once, regardless of
# how many /api/adapt/start requests land at the same time. Each run is
# several dozen sequential LLM calls at its peak (a full multi-section
# song) - with no cap, a burst of concurrent submissions would all hit
# the LLM provider simultaneously and risk provider-side rate-limit
# failures across every concurrent job, not just the newest one. The
# number itself is a starting guess, not a measured ceiling - tune via
# AURA_MAX_CONCURRENT_RUNS once real concurrent traffic exists to learn
# from.
MAX_CONCURRENT_RUNS = int(os.environ.get("AURA_MAX_CONCURRENT_RUNS", "4"))
_run_slots = threading.Semaphore(MAX_CONCURRENT_RUNS)


def _run_job(
    job_id: str,
    request: AdaptRequest,
    result_id: str,
    text: str,
    target_language: str,
    source_language: str,
    sections: list[SectionInput],
    song: SongInput,
    ip: str,
    started: float,
    user_id: str | None = None,
) -> None:
    with _run_slots:
        jobs.set_running(job_id)
        try:
            experience_result = _run_adaptation(
                request, result_id, text, target_language, source_language, sections, song, ip, started,
                log_prefix="job", user_id=user_id,
            )
            jobs.set_done(job_id, experience_result)
        except LLMError as exc:
            logger.error("job id=%s engine failure: %s", job_id, exc)
            jobs.set_error(
                job_id, "The engine hit a problem processing this song. Try again in a moment."
            )
        except RuntimeError as exc:
            logger.error("job id=%s configuration failure: %s", job_id, exc)
            jobs.set_error(job_id, str(exc))
        except Exception:
            # A background thread's uncaught exception is otherwise silent -
            # nothing re-raises it anywhere the poller would see. Whoever's
            # polling deserves an "error" status, not an indefinite "pending".
            logger.exception("job id=%s unexpected failure", job_id)
            jobs.set_error(job_id, "Something went wrong processing this song. Try again.")


@app.post("/api/adapt/start")
def adapt_start(request: AdaptRequest, http_request: Request) -> dict:
    """Same validation, cache, and quota behavior as /api/adapt, but the
    actual engine run happens in a background thread that outlives this
    request - see this module's docstring for why. Returns immediately
    either with a cached/fuzzy-matched result (status="done") or a job_id
    to poll (status="pending")."""
    started = time.monotonic()
    ip = _client_ip(http_request)
    user_id = _authed_user_id(http_request)
    text, target_language, source_language = _validate_adapt_request(request)

    result_id = cache.content_id(text, target_language=target_language, source_language=source_language)
    cached = cache.get(result_id)
    if cached is not None:
        _record_history(user_id, result_id, source_language)
        logger.info(
            "adapt/start id=%s ip=%s source=%s target=%s cache=hit duration=%.2fs",
            result_id, ip, source_language, target_language, time.monotonic() - started,
        )
        return {"status": "done", "job_id": None, "result": cached}

    similar = cache.find_similar(text, target_language=target_language, source_language=source_language)
    if similar is not None:
        matched_id, matched_result, similarity = similar
        cache.set(
            result_id,
            matched_result,
            source_text=text,
            target_language=target_language,
            source_language=source_language,
        )
        _record_history(user_id, result_id, source_language)
        logger.info(
            "adapt/start id=%s ip=%s source=%s target=%s cache=fuzzy_hit matched=%s similarity=%.3f duration=%.2fs",
            result_id, ip, source_language, target_language, matched_id, similarity,
            time.monotonic() - started,
        )
        return {"status": "done", "job_id": None, "result": matched_result}

    _check_quota(ip)
    sections, song = _build_song(text, target_language, source_language)

    job_id = uuid.uuid4().hex
    jobs.create(job_id)

    thread = threading.Thread(
        target=_run_job,
        args=(job_id, request, result_id, text, target_language, source_language, sections, song, ip, started, user_id),
        daemon=True,
    )
    thread.start()
    return {"status": "pending", "job_id": job_id, "result": None}


@app.get("/api/adapt/jobs/{job_id}")
def adapt_job_status(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404, detail="No job found for this id. It may have expired."
        )
    return job
