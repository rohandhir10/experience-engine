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
  POST /api/comics/ocr     multipart: image file + language -> detected
                            text regions with bounding boxes (engine/
                            comics_ocr.py) for /comics's panel review
                            workspace. Never adapts anything itself.
  POST /api/comics/adapt   body: {"source_language", "target_language",
                            "panels": [{"id", "text"}]} -> {"chapter_dna",
                            "panels": [{"id", "literal", "adapted_text",
                            "why"}]}. Runs Chapter DNA + the Writers'
                            Room per panel (engine/chapter_dna.py,
                            engine/comics_adapt.py) - blocking, no job
                            endpoint yet (see that function's docstring).

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
  - Input is length-capped (CASTIA_MAX_INPUT_CHARS for songs,
    CASTIA_MAX_COMICS_PANELS for a chapter's panel count) so one
    submission can't run an unbounded number of engine sections.
  - A per-IP daily quota (CASTIA_DAILY_LIMIT, Postgres-backed when
    DATABASE_URL is set - server/quota.py) is an anti-burst limit only,
    not a cost ceiling by itself - it resets every day, forever. A
    separate per-IP monthly quota (CASTIA_MONTHLY_LIMIT) is the real
    ceiling on cumulative free-tier spend, shared across music and
    comics for the same IP. Both cover the browser-facing endpoints
    (/api/adapt, /api/comics/adapt); the public API (/v1/*) uses its own
    per-API-key limit (CASTIA_API_DAILY_LIMIT) instead. Cache hits don't
    count against either. Set a limit to 0 to disable it.
    The two per-panel comics endpoints (/api/comics/ocr,
    /api/comics/redraw) have their own much larger ceilings
    (CASTIA_PANEL_DAILY_LIMIT/CASTIA_PANEL_MONTHLY_LIMIT) in a separate
    quota scope, since one legitimate chapter fires one call per panel -
    see PANEL_DAILY_LIMIT. Note that whose quota a request counts against
    depends on the Next.js proxy forwarding the real visitor's address
    (X-Castia-Client-IP, see _client_ip) - without that every visitor
    shares one bucket.
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

import base64
import json
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import anyio
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from engine import comics_align, comics_ocr, comics_read, comics_vision, config
from engine import youtube_ingest
from engine.chapter_dna import generate_chapter_dna
from engine.comics_adapt import adapt_chapter, character_bible_updates, merge_character_bible
from engine.comics_ocr import OcrError
from engine import comics_redraw
from engine.comics_redraw import RedrawError, redraw_panel_detailed
from engine.llm_client import LLMError, create_default_client, create_vision_client
from engine.models import SUPPORTED_LANGUAGES, BubbleInput, ChapterInput, SectionInput, SongInput
from engine.pipeline import run_engine
from engine.text_ingest import split_into_sections
from engine.verify import verify_result
from engine.youtube_ingest import IngestError

from . import accounts, api_keys, cache, character_bibles, credits, db, emailing, genre_corpus, jobs, monitoring, paddle, password_auth, quota, task_queue
from .mapping import _explain_why, _translator_text, to_experience_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("castia.server")

# Every plain `def` endpoint in this file runs in Starlette's threadpool
# (see this module's docstring above), which is capped by AnyIO's
# default CapacityLimiter at 40 concurrent threads PER PROCESS - not
# configured anywhere in this repo before now, just inherited silently.
# Most of these requests are I/O-bound (a DB round-trip, an LLM/Vision
# call) rather than CPU-bound, so the real ceiling on how many can be
# usefully in flight at once is much higher than 40 - 40 just means the
# 41st concurrent request queues behind the others even though the
# process has plenty of spare capacity to actually serve it. Raised well
# past what one process's CPU could ever put to work simultaneously,
# since the cost of an idle thread waiting on I/O is small; genuinely
# CPU-bound work (engine runs) is already separately bounded by
# MAX_CONCURRENT_RUNS/the Redis queue, not by this. Set once at startup
# in _lifespan (has to run inside the event loop - see anyio's
# current_default_thread_limiter docs). Starting guess, not a measured
# ceiling - tune via CASTIA_THREADPOOL_SIZE.
THREADPOOL_SIZE = int(os.environ.get("CASTIA_THREADPOOL_SIZE", "200"))

MAX_INPUT_CHARS = int(os.environ.get("CASTIA_MAX_INPUT_CHARS", "8000"))
# Anti-burst only, not a real cost ceiling on its own (see MONTHLY_LIMIT
# below) - lowered from 10 once the real per-request cost was worked out
# (docs/CAPABILITY_MATRIX.md): 10/day with no monthly cap left a
# persistent free IP's cumulative spend completely unbounded.
DAILY_LIMIT = int(os.environ.get("CASTIA_DAILY_LIMIT", "3"))
# The actual free-tier cost ceiling per IP, checked alongside DAILY_LIMIT
# in _check_quota (server/quota.py::check_and_increment_monthly). Shares
# one counter across both music and comics for the same IP (deliberately
# not tracked per-medium) - it's a total spend ceiling, not a per-feature
# allowance.
MONTHLY_LIMIT = int(os.environ.get("CASTIA_MONTHLY_LIMIT", "6"))
# Per-IP ceilings for the two per-panel comics endpoints (/api/comics/ocr,
# /api/comics/redraw), counted in their own quota scope
# (server/quota.py::_bucket_key) so they never consume the adaptation
# allowance above and vice versa.
#
# These endpoints had NO ceiling of any kind before this: each OCR call is
# a real, metered Google Cloud Vision request and each redraw is real
# inpainting work, both billed to this project per call, and a plain loop
# against either could run up an unbounded bill. They also can't reuse
# DAILY_LIMIT's numbers - that cap is 3, while ONE legitimate chapter
# fires one call per panel (up to MAX_COMICS_PANELS, and a whole-chapter
# strip auto-sliced by web/lib/chapterSlice.ts routinely lands in the
# dozens), so sharing that bucket would break normal use immediately.
#
# Sized against real use rather than guessed: a 100-panel chapter (the
# MAX_COMICS_PANELS ceiling) costs at most 100 OCR + 100 redraw calls, so
# 400/day comfortably covers a couple of the largest chapters this product
# accepts, or many ordinary ones, while still stopping a runaway loop
# within a few hundred calls instead of never.
PANEL_DAILY_LIMIT = int(os.environ.get("CASTIA_PANEL_DAILY_LIMIT", "400"))
PANEL_MONTHLY_LIMIT = int(os.environ.get("CASTIA_PANEL_MONTHLY_LIMIT", "2000"))
# The quota scope name for the two limits above - see quota._bucket_key.
PANEL_QUOTA_SCOPE = "panel"
# Per-IP daily ceiling on /api/auth/forgot-password. That endpoint's
# response can never reveal whether an email exists (password_auth.py's
# no-enumeration rule), which also means it can never rate-limit per
# account - the only lever left to stop it being used to spam a victim's
# inbox with reset links is capping how many requests one IP can fire in
# a day. Its own scope (not DAILY_LIMIT's) since this has nothing to do
# with adaptation cost.
PASSWORD_RESET_DAILY_LIMIT = int(os.environ.get("CASTIA_PASSWORD_RESET_DAILY_LIMIT", "5"))
PASSWORD_RESET_QUOTA_SCOPE = "password-reset"
# Per-IP daily ceilings on /api/auth/register and /api/auth/login.
#
# Every call to either endpoint runs a PBKDF2-HMAC-SHA256 hash at
# password_auth._PBKDF2_ITERATIONS (260,000) - register() hashes the new
# password, and authenticate() hashes something even for an email that
# doesn't exist (password_auth._DUMMY_HASH, so a nonexistent-account
# attempt takes the same time as a real one - see that module's
# docstring). That's deliberate, real CPU cost per request, and neither
# endpoint had any cap on how many times a single caller could trigger
# it - confirmed empirically to matter: a local load test at ~60-100
# concurrent requests (a single unauthenticated machine, no botnet)
# pushed p50 latency on both endpoints from a few hundred ms to 5-12
# seconds, and measurably bled into other traffic on the same process
# (a bystander /health check spiked to 6.5s mid-flood) - a real,
# cheap, single-machine DoS against sign-up/sign-in specifically.
#
# Same fix shape as PASSWORD_RESET_DAILY_LIMIT above: a per-IP daily cap
# via quota.check_and_increment, checked before the expensive hash runs
# so a caller who's already hit the limit is rejected by one cheap
# atomic UPSERT instead of paying for another 260,000-iteration hash.
# This bounds total daily damage/cost per IP; it does not by itself cap
# how much a single quick burst up to that ceiling can degrade latency
# in the moment - there's no sub-day granularity in quota.py to do
# that, matching PASSWORD_RESET_DAILY_LIMIT's own single-daily-cap
# shape. Register's default is lower than login's: real signups from
# one IP are rare even behind shared/NAT'd connections, while login is
# used every session and needs more headroom for e.g. an office or
# campus network's shared address. Both are starting guesses, not
# measured ceilings - tune via the env vars below.
AUTH_REGISTER_DAILY_LIMIT = int(os.environ.get("CASTIA_AUTH_REGISTER_DAILY_LIMIT", "20"))
AUTH_LOGIN_DAILY_LIMIT = int(os.environ.get("CASTIA_AUTH_LOGIN_DAILY_LIMIT", "50"))
AUTH_REGISTER_QUOTA_SCOPE = "auth-register"
AUTH_LOGIN_QUOTA_SCOPE = "auth-login"
# A full-resolution chapter-slice PNG can be several megabytes; this caps
# a single panel upload well above any normal slice, not just above a
# typical one, so this only ever rejects something clearly wrong (a
# non-panel file, a batch accidentally concatenated) rather than a real
# comic page.
MAX_IMAGE_BYTES = int(os.environ.get("CASTIA_MAX_IMAGE_BYTES", str(15 * 1024 * 1024)))
# Comics has no per-request cost ceiling at all otherwise: unlike songs
# (MAX_INPUT_CHARS bounds one submission's size), a chapter's cost scales
# directly with panel count and nothing capped it - a 100-panel chapter
# and a 3-panel one both cost "1" against DAILY_LIMIT/MONTHLY_LIMIT
# despite wildly different real spend, for an anonymous request; a
# signed-in one is charged CREDITS_PER_PANEL regardless, which already
# prices a large chapter correctly. 12 used to be low specifically to
# dodge a synchronous request's timeout (see comics_adapt_endpoint's old
# docstring) - now that /api/comics/adapt/start moves the actual engine
# run into a background job the same way /api/adapt/start already does
# for songs, that reason is gone. 100 is a real ceiling against a
# genuinely abusive single request (a script submitting a whole bound
# volume as one "chapter"), not a stand-in for a timeout workaround.
MAX_COMICS_PANELS = int(os.environ.get("CASTIA_MAX_COMICS_PANELS", "100"))
# Overall safety ceiling for one chapter's adapt_chapter run (engine/
# comics_adapt.py's `deadline` param) - not a normal-case limit (a
# reasonably sized chapter finishes in a fraction of this even under
# real rate-limiting), a backstop against a chapter that keeps eating
# 429 retries bubble after bubble until the total run time becomes
# unreasonable to keep a user waiting on, or to keep occupying a
# _run_slots concurrency slot other users' jobs are waiting on.
# Deliberately shorter than the frontend's own 15-minute poll ceiling
# (web/lib/comicsAdapt.ts's MAX_POLL_MS), not longer - the backend must
# give up and report a clean "error" status before the frontend's own
# deadline passes, or the frontend times out first with a generic
# message while this job is technically still going to fail moments
# later anyway.
JOB_TIMEOUT_SECONDS = int(os.environ.get("CASTIA_JOB_TIMEOUT_SECONDS", str(12 * 60)))
# Same idea as JOB_TIMEOUT_SECONDS above, for run_engine's `deadline`
# param (engine/pipeline.py's EngineTimeoutError) - a separate constant,
# not a shared one, because it has to stay under a different frontend
# ceiling: web/lib/useAdaptSubmit.ts's own MAX_POLL_MS for songs.
# Raised from 8 to 15 minutes (matching comics' JOB_TIMEOUT_SECONDS) -
# real full multi-section songs (several sections, each 3-7 sequential
# LLM calls) were routinely hitting the old 8-minute ceiling and erroring
# out with "N/M sections finished" partway through, not a rare edge case.
SONG_JOB_TIMEOUT_SECONDS = int(os.environ.get("CASTIA_SONG_JOB_TIMEOUT_SECONDS", str(15 * 60)))
# Per-unit credit prices, matching web/app/pricing/page.tsx's advertised
# averages exactly (SONG_CREDITS=30 for "~6 sections" => 5/section;
# PAGE_CREDITS=50 for "~5 panels" => 10/panel) - charged per actual
# section/panel count here rather than a flat per-submission price, so a
# 40-section song or a 40-panel chapter costs proportionally more than a
# 3-section song or 3-panel chapter, not the same flat price for wildly
# different real compute.
CREDITS_PER_SECTION = int(os.environ.get("CASTIA_CREDITS_PER_SECTION", "5"))
CREDITS_PER_PANEL = int(os.environ.get("CASTIA_CREDITS_PER_PANEL", "10"))
# Per-API-key daily cap for the public /v1/* endpoints (server/api_keys.py) -
# a separate dimension from CASTIA_DAILY_LIMIT above, which is per-IP and
# only ever gates the anonymous browser flow. A real API caller is
# identified by its key, not by IP (many legitimate calls can share one
# IP - a studio's own server, a shared office network), so it needs its
# own limit, not the browser one repurposed.
API_DAILY_LIMIT = int(os.environ.get("CASTIA_API_DAILY_LIMIT", "1000"))
# Shared secret between the Next.js server and this API, for the
# account endpoints (/api/users/sync, /api/me/*) and for trusting a
# user id forwarded on adapt requests. The Next.js side is the party
# that actually verified the Google sign-in (Auth.js); this secret is
# how it proves a request came from it and not from a browser talking
# to this API directly. Unset -> account endpoints answer 503 and
# forwarded user ids are ignored (accounts off, everything else works).
INTERNAL_API_SECRET = os.environ.get("CASTIA_INTERNAL_API_SECRET", "")
# Paddle's own notification/webhook secret (set per-webhook-destination
# in Paddle's dashboard, not the same as a Paddle API key) - verifies a
# /webhooks/paddle POST actually came from Paddle (server/paddle.py).
# Unset -> the webhook route rejects every request with a 503, same
# "off, not silently insecure" convention as INTERNAL_API_SECRET above.
PADDLE_WEBHOOK_SECRET = os.environ.get("CASTIA_PADDLE_WEBHOOK_SECRET", "")
ALLOWED_ORIGINS = os.environ.get(
    "CASTIA_ALLOWED_ORIGINS", "http://localhost:3000"
).split(",")

def production_config_problems() -> list[str]:
    """Settings that are fine (or deliberate) in local dev but are real
    problems in production, checked once at startup and logged.

    Every item here is a failure that is otherwise SILENT: nothing throws,
    the service comes up healthy, and the damage only shows up later as
    lost work, mis-metered quota, or a purchase that never granted
    credits. A startup line is the cheapest place to catch a deploy that
    is missing an environment variable.

    Returns strings rather than logging directly so this is testable
    without capturing log output, and so a future readiness endpoint could
    surface the same list. Deliberately never raises - a warning must not
    be able to take down a deployment that is otherwise serving fine.
    """
    problems: list[str] = []

    if not os.environ.get("DATABASE_URL"):
        problems.append(
            "DATABASE_URL is not set. Accounts, credits, adaptation history and the "
            "Paddle idempotency guard are all unavailable, and quota/jobs/cache fall "
            "back to per-process memory and local disk - which on an ephemeral or "
            "multi-instance host means counters reset on every deploy and are not "
            "shared between instances (server/quota.py, server/jobs.py, server/cache.py)."
        )

    if not INTERNAL_API_SECRET:
        problems.append(
            "CASTIA_INTERNAL_API_SECRET is not set. The /api/me/* account endpoints "
            "return 503, signed-in identity is never trusted, and per-IP quota cannot "
            "tell visitors apart - every request buckets under the proxy's own address "
            "(see _client_ip)."
        )

    if not os.environ.get("RESEND_API_KEY"):
        problems.append(
            "RESEND_API_KEY is not set. Email verification links are only written to "
            "the log, never delivered, so nobody can complete a password signup "
            "(server/emailing.py)."
        )
    elif "resend.dev" in emailing.EMAIL_FROM:
        problems.append(
            f"CASTIA_EMAIL_FROM is still Resend's sandbox sender ({emailing.EMAIL_FROM}). "
            "Set it to an address on a domain verified in Resend, or verification mail "
            "will look untrustworthy and is likely to be filtered as spam."
        )

    if not os.environ.get("CASTIA_SENTRY_DSN"):
        problems.append(
            "CASTIA_SENTRY_DSN is not set. Errors are still written to the log, but "
            "nothing aggregates or alerts on them - a failure affecting many users "
            "looks exactly like one that happened once (server/monitoring.py)."
        )

    if not os.environ.get("CASTIA_PADDLE_WEBHOOK_SECRET"):
        problems.append(
            "CASTIA_PADDLE_WEBHOOK_SECRET is not set. The Paddle webhook returns 503, so "
            "completed purchases never grant credits (server/paddle.py)."
        )
    elif not os.environ.get("CASTIA_PADDLE_PRICE_CREDITS"):
        problems.append(
            "CASTIA_PADDLE_PRICE_CREDITS is not set. Paddle webhooks are accepted and "
            "verified but map no price id to a credit amount, so a real payment grants "
            "nothing (server/paddle.py)."
        )

    return problems


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # First, so anything that fails during the rest of startup (the
    # database init below) is itself reported rather than only logged.
    monitoring.init_error_monitoring()
    # Must run inside a running event loop - current_default_thread_limiter()
    # is contextvar-scoped per loop, so this can't be set at import time.
    # See THREADPOOL_SIZE's comment above for why 40 (AnyIO's default) is
    # too low for this app's mostly-I/O-bound endpoints.
    anyio.to_thread.current_default_thread_limiter().total_tokens = THREADPOOL_SIZE
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
    for problem in production_config_problems():
        logger.warning("PRODUCTION CONFIG: %s", problem)
    yield


app = FastAPI(title="CASTIA engine API", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# How many reverse-proxy hops sit between the internet and this service
# for a DIRECT (non-proxied) caller - see _client_ip's x-forwarded-for
# fallback below. Every hop that legitimately forwards a request
# *appends* its own observed peer address to the end of the header
# (standard `proxy_add_x_forwarded_for`-style behavior, e.g. nginx/most
# platform edges including Railway's), so the entries a client can
# freely fabricate are the ones on the LEFT, not the right - only the
# rightmost TRUSTED_PROXY_HOPS entries were actually appended by proxies
# this deployment trusts.
#
# Default 1: Railway's own edge is the only reverse proxy this
# deployment sits behind for direct traffic (browser-facing requests
# through the Next.js proxy never reach this fallback at all - see
# X-Castia-Client-IP below). Trusting index 0 instead (this function's
# previous behavior) let anyone hitting this service's public URL
# directly fabricate an X-Forwarded-For header and rotate the claimed
# address per request to bypass every IP-based quota check in this
# file for free - found during a security audit, not from an incident.
# Tune via CASTIA_TRUSTED_PROXY_HOPS if that chain ever grows another
# hop (e.g. an additional load balancer in front of Railway's edge) -
# get this wrong in the other direction (too high) and it degrades back
# toward the same vulnerability, one hop at a time.
TRUSTED_PROXY_HOPS = int(os.environ.get("CASTIA_TRUSTED_PROXY_HOPS", "1"))


def _client_ip(request: Request) -> str:
    """The address a request's quota (server/quota.py) is bucketed under.

    Every browser-facing request arrives through the Next.js proxy
    (web/app/api/**/route.ts), which opens its own outbound fetch - so
    this process's peer address is the Next.js server for EVERY visitor,
    and x-forwarded-for on that hop describes the proxy's own connection,
    not the person using the site. Bucketing on either of those puts the
    entire site in ONE quota bucket: the first few visitors of the day
    exhaust it and everyone after them is refused. That is an
    availability bug, not a metering rounding error, which is why the
    proxy now forwards the real address explicitly.

    X-Castia-Client-IP is honored ONLY alongside a valid internal secret,
    the same reasoning _authed_user_id already applies to forwarded user
    identity: anyone can set a header, but only the Next.js server knows
    the secret, so an unauthenticated request claiming an address is not
    evidence of anything and must fall through to the peer address.
    Otherwise quota would be opt-out for anyone who reads this file.

    Direct callers (the public /v1 API, and anyone who calls the
    browser-facing endpoints straight against this service's own public
    URL instead of through the Next.js proxy) still reach here via the
    platform's own edge proxy and are read from x-forwarded-for - see
    TRUSTED_PROXY_HOPS above for why only its rightmost entries are ever
    trusted.
    """
    if INTERNAL_API_SECRET and request.headers.get("x-castia-internal-secret") == INTERNAL_API_SECRET:
        forwarded_client = (request.headers.get("x-castia-client-ip") or "").strip()
        if forwarded_client:
            return forwarded_client

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if hops:
            index = max(0, len(hops) - TRUSTED_PROXY_HOPS)
            return hops[index]
    return request.client.host if request.client else "unknown"


def _require_internal_secret(request: Request) -> None:
    if not INTERNAL_API_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Accounts are not configured on this deployment (CASTIA_INTERNAL_API_SECRET unset).",
        )
    if request.headers.get("x-castia-internal-secret") != INTERNAL_API_SECRET:
        raise HTTPException(status_code=401, detail="Invalid internal secret.")


def _required_user_id(request: Request) -> str:
    """For the /api/me/* endpoints, which are meaningless without a user.
    The internal secret is checked separately by _require_internal_secret
    — this only pulls the id out."""
    user_id = request.headers.get("x-castia-user-id")
    if not user_id:
        raise HTTPException(status_code=400, detail="X-Castia-User-Id header is required.")
    return user_id


def _authed_user_id(request: Request) -> str | None:
    """The signed-in user's id, forwarded by the Next.js server on adapt
    requests — honored ONLY alongside the internal secret, since anyone
    can put a header on a request but only the Next.js server (which
    verified the Google sign-in) knows the secret. Returns None rather
    than raising: a missing/bad pairing means the request proceeds as
    anonymous, exactly like before accounts existed — history is an
    enhancement to an adapt request, never a gate on it."""
    user_id = request.headers.get("x-castia-user-id")
    if not user_id:
        return None
    if not INTERNAL_API_SECRET:
        return None
    if request.headers.get("x-castia-internal-secret") != INTERNAL_API_SECRET:
        return None
    return user_id


def _require_api_key(request: Request) -> dict:
    """Gate for the public /v1/* endpoints - a real third-party caller,
    not the Next.js server (that's _authed_user_id's job, a different
    trust chain entirely). Reads `Authorization: Bearer <key>`, resolves
    it via server/api_keys.py, enforces the per-key daily limit, and
    records the key as used. Raises HTTPException; returns
    {"user_id", "key_id"} on success - the public API is unconditionally
    off (401 on every request) if DATABASE_URL isn't set, since a key
    can't be issued or checked without a database at all.
    """
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Pass it as 'Authorization: Bearer <key>'.",
        )
    raw_key = header[len("Bearer "):].strip()
    resolved = api_keys.resolve_key(raw_key)
    if resolved is None:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key.")
    if not api_keys.check_and_increment_usage(resolved["key_id"], API_DAILY_LIMIT):
        raise HTTPException(
            status_code=429,
            detail=f"Daily API request limit ({API_DAILY_LIMIT}) exceeded for this key.",
        )
    api_keys.touch_last_used(resolved["key_id"])
    return resolved


def _check_quota(ip: str, kind: str = "songs") -> None:
    # server/quota.py: Postgres-backed (atomic, safe across more than one
    # process/instance) when DATABASE_URL is set, an in-memory dict
    # otherwise - see that module's docstring. Daily is an anti-burst
    # limit only; monthly is the real cost ceiling - see MONTHLY_LIMIT's
    # comment above for why the daily-only check that used to be here
    # left cumulative spend completely unbounded.
    if not quota.check_and_increment(ip, DAILY_LIMIT):
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've reached today's limit for new {kind}. Already-"
                f"processed {kind} are still free to view and share."
            ),
        )
    if not quota.check_and_increment_monthly(ip, MONTHLY_LIMIT):
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've reached this month's free limit for new {kind}. "
                f"Already-processed {kind} are still free to view and share."
            ),
        )


def _check_panel_quota(ip: str, kind: str) -> None:
    """The per-IP ceiling for one per-panel comics call (OCR or redraw).

    Applied to every caller, signed in or not - deliberately unlike
    _check_quota above, which a signed-in user bypasses. That bypass is
    justified there because a signed-in adaptation is charged real
    credits (CREDITS_PER_SECTION/CREDITS_PER_PANEL), so the cost is
    already paid for by the person incurring it. Neither of these two
    endpoints charges credits today, so nobody has paid for this work and
    there is nothing for an account to bypass on the strength of. If they
    ever do start charging, this should grow the same
    credits-then-elif-quota shape the adapt endpoints use.

    See PANEL_DAILY_LIMIT for why these have their own scope and their
    own, much larger numbers than the adaptation caps.
    """
    if not quota.check_and_increment(ip, PANEL_DAILY_LIMIT, scope=PANEL_QUOTA_SCOPE):
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've reached today's limit for {kind}. "
                "Panels already processed are unaffected - try again tomorrow."
            ),
        )
    if not quota.check_and_increment_monthly(ip, PANEL_MONTHLY_LIMIT, scope=PANEL_QUOTA_SCOPE):
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've reached this month's limit for {kind}. "
                "Panels already processed are unaffected."
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
    # youtube_section_timings alone (no video_id) is set when this text
    # came from lib/lyricsImport.ts's .lrc/.srt import - real per-section
    # timing, no video to sync. Both set together when it came from
    # /api/youtube-draft instead, letting the result page embed a synced
    # player. Either way, only kept when the user didn't restructure the
    # section breaks while reviewing the draft (see adapt()'s length
    # check below) - the engine itself never sees this, it's server/
    # frontend-only bookkeeping, matched to sections purely by position.
    youtube_video_id: str | None = None
    youtube_section_timings: list[YoutubeSectionTiming] | None = None


class YoutubeDraftRequest(BaseModel):
    url: str
    preferred_languages: list[str] | None = None


class UserSyncRequest(BaseModel):
    google_sub: str
    email: str | None = None
    display_name: str | None = None


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class FavoriteRequest(BaseModel):
    is_favorite: bool


class CollectionRequest(BaseModel):
    name: str


class MembershipRequest(BaseModel):
    member: bool


class ApiKeyRequest(BaseModel):
    name: str


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


@app.post("/api/comics/ocr")
def comics_ocr_endpoint(
    http_request: Request,
    image: UploadFile = File(...),
    language: str | None = Form(None),
) -> dict:
    """Extracts text regions from one uploaded comic panel image via
    Google Cloud Vision (engine/comics_ocr.py) — see that module's
    docstring for what this can and can't do (no stylized-lettering
    guarantees; requires GOOGLE_CLOUD_VISION_CREDENTIALS_JSON, a
    base64-encoded service-account key, to be set). Called from
    web/app/comics's panel workspace to pre-fill a panel's "Extracted
    text" field instead of a fully manual paste; the result is always a
    draft the human reviews, never handed straight to the adaptation
    engine.

    `language` is optional and used only as a hint — Cloud Vision
    auto-detects script/language per block on its own, unlike the
    Tesseract-based version this replaced.

    Plain `def`, not `async def` — reads the upload via the underlying
    SpooledTemporaryFile (`image.file.read()`) rather than UploadFile's
    async `.read()`, so this runs in FastAPI's threadpool like every
    other endpoint here instead of needing pytest-asyncio just to test.
    """
    image_bytes = image.file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image is larger than the {MAX_IMAGE_BYTES // (1024 * 1024)}MB limit.",
        )

    # After the size check (a rejected upload never reaches Vision, so it
    # shouldn't spend anyone's allowance) and before any billable call.
    _check_panel_quota(_client_ip(http_request), "reading panels")

    # Built once, up front, so real usage (its call_log) can be logged no
    # matter which path below actually uses it - previously this cost was
    # entirely invisible: comics_vision.read_panel built and discarded its
    # own client internally, so nothing survived for the caller to
    # inspect. None when reading is disabled (config.VISION_READING_ENABLED)
    # or the client can't be built - both paths below already degrade to
    # OCR-only on None/failure, same as before this change.
    vision_client = None
    if config.VISION_READING_ENABLED:
        try:
            vision_client = create_vision_client()
        except Exception as exc:  # noqa: BLE001 - reading is opt-in enrichment, not the request
            logger.warning("Vision reading unavailable, falling back to OCR only: %s", exc)

    # Preferred path when a detector is configured: detect the boxes
    # first, then read them twice concurrently (engine/comics_read.py).
    # Keying both readers to the detector's node_ids makes the merge
    # exact instead of a text-similarity guess. Returns {} if detection
    # finds nothing or fails, which falls through to the single-step
    # path below rather than failing the request.
    if config.TEXT_DETECTOR_URL:
        two_step = comics_read.read_panel_two_step(
            image_bytes,
            mime_type=image.content_type or "image/jpeg",
            language=language,
            vision_client=vision_client,
        )
        if two_step:
            _log_vision_reading_cost(vision_client, getattr(image, "filename", None), read_path="two_step")
            return two_step
        # A configured detector that found nothing is otherwise silent -
        # worth a log line, since it means this request fell all the way
        # back to the naive single-step path below despite a detector
        # being configured, which is easy to mistake for "no detector
        # configured at all" from the outside.
        logger.info("comics_ocr read_path=two_step_fallback image=%s", getattr(image, "filename", None))

    # Both reads are fired at once rather than one after the other. The
    # vision model is not given Cloud Vision's boxes to correct, precisely
    # so it doesn't have to wait for them - total latency is the slower of
    # the two calls instead of their sum. The cost of not sharing a
    # coordinate frame is paid afterwards, by matching the model's text
    # back onto Vision's boxes (engine/comics_align.py).
    #
    # Disabled by default (config.VISION_READING_ENABLED); when off,
    # read_panel returns [] without making a call and this is exactly the
    # old OCR-only path.
    with ThreadPoolExecutor(max_workers=2) as pool:
        ocr_future = pool.submit(
            comics_ocr.extract_text_regions, image_bytes, language=language
        )
        vision_future = pool.submit(
            comics_vision.read_panel,
            image_bytes,
            image.content_type or "image/jpeg",
            None,
            vision_client,
        )
        try:
            result = ocr_future.result()
        except OcrError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        # read_panel never raises - it degrades to [] - so a vision
        # failure can only ever cost the enrichment, never the OCR result
        # the user actually asked for.
        readings = vision_future.result()

    _log_vision_reading_cost(vision_client, getattr(image, "filename", None), read_path="single_step")
    return _merge_vision_readings(result, readings)


def _log_vision_reading_cost(vision_client, image_name: str | None, read_path: str) -> None:
    """Measured, not estimated (engine/models.py::LLMCallRecord) - real
    token usage from the vision-LLM reading pass, the same gap flagged
    for the comics adaptation path above: this cost previously never
    reached a log line at all.

    `read_path` ("two_step" or "single_step") makes which OCR path a
    real request actually took diagnosable from logs alone - previously
    both paths call Cloud Vision identically (a configured detector
    falls back to CloudVisionDetector's own DOCUMENT_TEXT_DETECTION when
    no dedicated detector service is set), so nothing in a log line told
    you whether CASTIA_TEXT_DETECTOR_URL was actually taking effect.

    Still logs even with zero vision-LLM calls (CASTIA_VISION_READING
    off) so read_path is visible on every request, not only when reading
    is enabled - cost fields are simply zero in that case, never
    estimated.
    """
    calls = getattr(vision_client, "call_log", [])
    total_prompt = sum(r.prompt_tokens for r in calls)
    total_completion = sum(r.completion_tokens for r in calls)
    llm_latency = sum(r.latency_seconds for r in calls)
    logger.info(
        "comics_ocr_vision read_path=%s image=%s llm_calls=%d llm_latency=%.2fs "
        "prompt_tokens=%d completion_tokens=%d",
        read_path, image_name, len(calls), llm_latency, total_prompt, total_completion,
    )


def _merge_vision_readings(ocr_result: dict, readings: list) -> dict:
    """Folds a vision-LLM reading of the panel into the Cloud Vision
    result, region by region. Returns ocr_result unchanged when there are
    no readings, so the OCR-only path is untouched.

    Every region keeps its Cloud Vision bounding box no matter what -
    only the TEXT can come from the model, and only where the match was
    confident. `text_source` is reported per region so the frontend can
    show which readings were corrected rather than implying the whole
    panel was.
    """
    if not readings:
        return ocr_result

    regions = ocr_result.get("regions", [])
    aligned = comics_align.align_readings([r["text"] for r in regions], readings)

    for region, match in zip(regions, aligned.regions):
        region["text"] = match.text
        region["text_source"] = match.source
        region["kind"] = match.kind
        region["speaker"] = match.speaker

    ocr_result["full_text"] = "\n\n".join(r["text"] for r in regions)
    ocr_result["vision_corrected_count"] = aligned.corrected_count
    # Text the model read that no OCR box matched - almost always a bubble
    # Cloud Vision missed entirely. Surfaced rather than dropped, but kept
    # out of regions/full_text since there's no box to place or redraw it.
    ocr_result["unplaced_readings"] = [
        {"text": r.text, "kind": r.kind, "speaker": r.speaker} for r in aligned.unplaced
    ]
    return ocr_result


class RedrawBbox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class RedrawRegion(BaseModel):
    bbox: RedrawBbox
    adapted_text: str
    # A key into engine/comics_redraw.py's FONTS, or None to fall back to
    # `default_font` below (and from there to comics_redraw.DEFAULT_FONT)
    # - lets one panel mix fonts (a softer default, a bolder override on
    # one shout) without every region having to name one.
    font: str | None = None
    # Optional - the same "dialogue" | "sfx" | "narration" | "background"
    # | "unknown" classification /api/comics/ocr's vision-LLM read pass
    # can already produce per region (BubbleInput.kind), when the caller
    # has it. Not required: the base OCR-only path doesn't classify at
    # all, and a manually-typed region never has one either - both stay
    # trusted exactly as before this field existed. When present,
    # engine/comics_redraw.py rejects "sfx"/"background" outright rather
    # than attempting an inpaint known to produce a broken result.
    kind: str | None = None


@app.post("/api/comics/redraw")
def comics_redraw_endpoint(
    http_request: Request,
    image: UploadFile = File(...),
    regions: str = Form(...),
    default_font: str | None = Form(None),
) -> dict:
    """Erases the original text out of each given bubble region and
    draws the adapted line back in its place (engine/comics_redraw.py) -
    see that module's docstring for the honest, disclosed scope: speech
    bubbles only (not SFX), a small curated set of bundled OFL comic
    fonts rather than a match for the original lettering, and a
    heuristic text-color guess.

    `regions` is a JSON-encoded string (multipart can't carry nested
    JSON directly) - `[{"bbox": {"x","y","width","height"}, "adapted_text", "font"}, ...]`,
    the same bbox shape /api/comics/ocr already returns per detected
    region, paired with whatever adapted text the caller wants drawn
    there. `font` (per region) and `default_font` (this request's
    fallback for any region that omits one) must each be a key in
    engine/comics_redraw.py's FONTS or omitted entirely - an unrecognized
    name is rejected with a 400 rather than silently drawing in the
    wrong font, even though comics_redraw.py's own resolution would
    quietly fall back to the default for the same input; the API
    boundary is where a caller's typo should be surfaced, not swallowed.
    Returns the composited PNG as base64, plus `id` - a real,
    content-addressed id (server/cache.py::comics_redraw_content_id),
    the same idea as /api/adapt's result_id. An identical (image, regions,
    fonts) request is served straight from cache.get() rather than
    re-running the inpainting pipeline (OpenCV or LaMa, whichever this
    image needed - both are pure functions of their input, so a cache
    hit is exactly the same output as a recompute) - this is what keeps
    a page reload, a retried request, or several browser tabs on the
    same panel from each paying for their own redraw. Fetch a past
    result later via GET /api/comics/redraw/{id}.
    """
    image_bytes = image.file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image is larger than the {MAX_IMAGE_BYTES // (1024 * 1024)}MB limit.",
        )
    try:
        parsed = json.loads(regions)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"'regions' must be valid JSON: {exc}") from exc
    try:
        validated = [RedrawRegion(**r) for r in parsed]
    except (TypeError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not validated:
        raise HTTPException(status_code=400, detail="At least one region is required.")

    unknown_fonts = sorted(
        {f for f in [default_font, *(r.font for r in validated)] if f and f not in comics_redraw.FONTS}
    )
    if unknown_fonts:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown font(s) {unknown_fonts} - must be one of "
                f"{sorted(comics_redraw.FONTS)}."
            ),
        )

    # Same reasoning as the unknown-font check above: reject before
    # spending any per-IP panel quota on a request already guaranteed to
    # fail (engine/comics_redraw.py::_validate_redrawable would raise
    # RedrawError for the same regions anyway, but only after the quota
    # check below).
    unsafe_kinds = sorted(
        {(i, r.kind) for i, r in enumerate(validated) if r.kind in comics_redraw.UNSAFE_REDRAW_KINDS}
    )
    if unsafe_kinds:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Region(s) {[i for i, _ in unsafe_kinds]} are classified as "
                f"{sorted({k for _, k in unsafe_kinds})} - SFX and background "
                "regions are not safe to redraw as speech bubbles. Only "
                "dialogue/narration/unclassified regions can be redrawn."
            ),
        )

    region_dicts = [
        {"bbox": r.bbox.model_dump(), "adapted_text": r.adapted_text, "font": r.font, "kind": r.kind}
        for r in validated
    ]

    result_id = cache.comics_redraw_content_id(image_bytes, region_dicts, default_font)
    cached = cache.get(result_id)
    if cached is not None:
        return {**cached, "id": result_id}

    # Deliberately after the cache lookup: a cache hit runs no inpainting
    # and costs nothing, and this module's stated convention (see the
    # quota bullet in the docstring at the top of this file) is that cache
    # hits don't count against any quota. Reloading a page or opening the
    # same panel in a second tab must not spend the allowance.
    _check_panel_quota(_client_ip(http_request), "redrawing panels")

    try:
        result_bytes, inpaint_method = redraw_panel_detailed(
            image_bytes, region_dicts, default_font
        )
    except RedrawError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Reported so a fallback isn't invisible. A LaMa reconstruction and an
    # OpenCV smear look very different on drawn artwork, and a UI that
    # showed both without distinction would be implying a quality this
    # panel may not actually have.
    result = {
        "image_base64": base64.b64encode(result_bytes).decode("ascii"),
        "inpaint_method": inpaint_method,
    }
    cache.set(result_id, result)
    return {**result, "id": result_id}


@app.get("/api/comics/redraw/{result_id}")
def get_comics_redraw(result_id: str) -> dict:
    cached = cache.get(result_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No result found for this link.")
    return {**cached, "id": result_id}


class ComicsPanelText(BaseModel):
    id: str
    text: str
    # Free-text name of who's speaking, typed by the human reviewing the
    # panel (web/components/comics/PanelWorkspace.tsx) - threaded
    # straight through to BubbleInput.voice below. None/omitted means
    # unattributed, same as before this field existed.
    voice: str | None = None
    # "dialogue" | "sfx" | "narration" | "background" | "unknown" - the
    # optional vision-LLM OCR read pass's classification of this region
    # (web/lib/comics-types.ts's OcrRegion.kind), when it ran. Threaded
    # straight through to BubbleInput.kind, which engine/comics_adapt.py
    # uses to skip the Writers' Room entirely for "sfx"/"background"
    # regions. None/omitted (every request before this existed, and any
    # deployment without CASTIA_VISION_READING set) behaves exactly as
    # before - nothing is skipped without a real classification.
    kind: str | None = None


class ComicsAdaptRequest(BaseModel):
    source_language: str
    target_language: str = "English"
    context_note: str | None = None
    panels: list[ComicsPanelText]
    # Free-text series name (server/character_bibles.py) that ties this
    # chapter's characters to any previously-persisted voice/honorific
    # data for the SAME signed-in user's series of that name - see
    # engine/comics_adapt.py::merge_character_bible/character_bible_updates.
    # None/blank means no cross-chapter memory for this request, same as
    # every request behaved before this field existed. Anonymous requests
    # (user_id is None) never persist or read a bible even if this is
    # set - a bible needs a real owner.
    series_name: str | None = None


@app.post("/api/comics/adapt")
def comics_adapt_endpoint(request: ComicsAdaptRequest, http_request: Request) -> dict:
    """Runs a whole chapter's worth of panels through Chapter DNA
    (engine/chapter_dna.py) and the Writers' Room (engine/comics_adapt.py)
    — the first endpoint that actually adapts comic dialogue rather
    than just extracting or displaying it (see docs/CAPABILITY_MATRIX.md's
    chapter-level-context roadmap).

    Each entry in `request.panels` is one adaptation unit ("bubble" in
    engine terms) — this endpoint has no concept of a "panel" at all,
    only a flat list of {id, text, voice}. The frontend
    (lib/comics-types.ts::panelToChapterBubbles) sends one entry per
    detected OCR region when a panel has them, so a panel with several
    speech bubbles gets each adapted independently; a panel with no
    detected regions (hand-typed dialogue) sends one entry for its
    whole text instead, since there's no per-bubble structure to split
    against. `ComicsPanelText.voice`, when a speaker is named for a
    bubble (components/comics/PanelWorkspace.tsx), threads straight
    through to BubbleInput.voice — this is what actually drives
    per-character voice consistency and honorific-register tracking
    (engine/comics_adapt.py). A bubble left unattributed still adapts
    fine; it just doesn't get either benefit.

    Deliberately synchronous, same as /api/adapt still is — fine for a
    short chapter, but many sequential per-panel Writers' Room runs can
    exceed a request timeout well before MAX_COMICS_PANELS's real
    ceiling. A long chapter should use POST /api/comics/adapt/start
    instead (below) — the same background-job/poll pattern
    /api/adapt/start already established for songs.

    Now persisted: the result is stored under a real, content-addressed
    id (cache.comics_content_id — same get()/set() storage /api/adapt
    uses, so a repeat submission of the identical chapter is a cache hit,
    not a re-run) and, for a signed-in user, recorded in their history
    with medium="webtoons" (accounts.record_adaptation) — the first real
    persistence comics has had; see GET /api/comics/adapt/{result_id}
    below for the share-link read side this unlocks.
    """
    return _comics_adapt_or_serve_cached(
        request, http_request, _authed_user_id(http_request), enforce_ip_quota=True
    )


@app.post("/api/comics/adapt/start")
def comics_adapt_start(request: ComicsAdaptRequest, http_request: Request) -> dict:
    """Same validation, cache, and quota/credit behavior as
    /api/comics/adapt, but the actual engine run happens in a background
    thread that outlives this request — see /api/adapt/start's docstring
    for why, and _run_comics_adaptation's docstring for why panels run
    sequentially in that thread rather than batched/parallelized (voice/
    honorific continuity, not cost, is what that continuity buys).
    Returns immediately either with a cached result (status="done") or a
    job_id to poll via GET /api/comics/adapt/jobs/{job_id} (status="pending").
    """
    user_id = _authed_user_id(http_request)
    non_empty_panels = [p for p in request.panels if p.text.strip()]
    if not non_empty_panels:
        raise HTTPException(
            status_code=400, detail="At least one panel with extracted text is required."
        )
    if len(non_empty_panels) > MAX_COMICS_PANELS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"That's over the {MAX_COMICS_PANELS}-panel limit for one "
                "chapter. Try a shorter chapter or a single episode."
            ),
        )

    result_id = cache.comics_content_id(
        [p.text for p in non_empty_panels],
        target_language=request.target_language,
        source_language=request.source_language,
    )
    cached = cache.get(result_id)
    if cached is not None:
        _record_history(user_id, result_id, request.source_language, medium="webtoons")
        return {"status": "done", "job_id": None, "result": {"id": result_id, **cached}}

    debited = None
    if user_id is not None:
        debited = CREDITS_PER_PANEL * len(non_empty_panels)
        if not credits.deduct(user_id, debited, reason="adaptation", reference=result_id):
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Not enough credits for this chapter ({debited} needed). "
                    "Buy more credits on the pricing page."
                ),
            )
    else:
        _check_quota(_client_ip(http_request), kind="chapters")

    job_id = uuid.uuid4().hex
    jobs.create(job_id)

    if task_queue.use_queue():
        task_queue.get_queue().enqueue(
            _run_comics_job,
            job_id, request, result_id, non_empty_panels, user_id, debited,
            job_timeout=JOB_TIMEOUT_SECONDS + 120,
        )
    else:
        thread = threading.Thread(
            target=_run_comics_job,
            args=(job_id, request, result_id, non_empty_panels, user_id, debited),
            daemon=True,
        )
        thread.start()
    return {"status": "pending", "job_id": job_id, "result": None}


@app.get("/api/comics/adapt/jobs/{job_id}")
def comics_adapt_job_status(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404, detail="No job found for this id. It may have expired."
        )
    return job


def _run_comics_adaptation(
    request: ComicsAdaptRequest,
    result_id: str,
    non_empty_panels: list[ComicsPanelText],
    user_id: str | None,
    job_id: str | None = None,
) -> dict:
    """The actual engine run: Chapter DNA -> per-panel Writers' Room ->
    payload assembly, cache write, and history record. Shared by the
    synchronous /api/comics/adapt flow and the background job
    /api/comics/adapt/start kicks off — same split _run_adaptation has
    for songs. Raises ValidationError/LLMError/RuntimeError uncaught;
    callers differ only in how they turn that into a response (an
    HTTPException + refund here, a job's stored `error` string there),
    so those propagate uncaught rather than being translated in here.

    Deliberately NOT internally parallelized across panels: RoomMemory's
    honorific_state (engine/comics_adapt.py) threads sequentially from
    one panel to the next, which is what makes per-character voice/
    honorific-register consistency work across a chapter today. Running
    panels concurrently would break that continuity, so "handle a big
    chapter" is solved here by moving this same sequential run off the
    request thread (the job below), not by batching or parallelizing the
    panels themselves — the per-panel dollar cost is identical either
    way, this only removes the request-timeout ceiling on how many
    panels one chapter can have.

    `job_id`, when given (only the background job path passes one — the
    synchronous /api/comics/adapt endpoint has no job to report against
    and blocks until this returns anyway), turns on incremental progress
    reporting: adapt_chapter's on_stage/on_bubble_done hooks update
    jobs.set_progress after every real, already-happening step, so a
    poller sees each panel's actual finished text as soon as it's ready
    instead of only once the whole chapter completes - this is what lets
    the workspace unlock and render panels one by one rather than sit on
    a single spinner for however long a large chapter takes. The very
    first progress write happens below, before Chapter DNA generation
    even starts - without it, a poller sees nothing at all (not even a
    bubble count) until the first bubble begins, and Chapter DNA
    generation is itself a real LLM call that can be slow under the same
    rate-limiting a chapter's bubbles can hit, so that silent gap could
    otherwise be the single worst part of the wait to have zero
    feedback during.

    `deadline` bounds the whole run (engine/comics_adapt.py's
    ChapterTimeoutError, JOB_TIMEOUT_SECONDS below) - see that module's
    docstring for why this exists on top of every individual LLM call
    already having its own timeout.
    """
    chapter = ChapterInput(
        source_language=request.source_language,
        target_language=request.target_language,
        context_note=request.context_note,
        bubbles=[
            BubbleInput(id=p.id, source_text=p.text, voice=p.voice, kind=p.kind)
            for p in non_empty_panels
        ],
    )

    panels_out: list[dict] = []

    def _report_progress(completed: int, total: int, message: str) -> None:
        if job_id is None:
            return
        jobs.set_progress(
            job_id,
            {"completed": completed, "total": total, "message": message, "panels": list(panels_out)},
        )

    _report_progress(0, len(non_empty_panels), "Reading chapter…")

    client = create_default_client()
    dna = generate_chapter_dna(chapter, client)
    deadline = time.monotonic() + JOB_TIMEOUT_SECONDS

    # Persistent character bibles: a real owner (user_id) and a series
    # name are both required - a bible for an anonymous request or with
    # no series given would have nothing to key future lookups on, so
    # this is silently skipped rather than half-working. See
    # engine/comics_adapt.py::merge_character_bible's own docstring for
    # what "merge" actually does (override only a name this series has
    # seen before; leave every other character untouched).
    series_name = request.series_name
    bible_active = bool(user_id and series_name and series_name.strip())
    if bible_active:
        dna.characters = merge_character_bible(
            dna.characters, character_bibles.get_bible(user_id, series_name)
        )

    def on_stage(bubble_id: str, stage: str, index: int, total: int) -> None:
        verb = "adapting" if stage == "adapting" else "verifying"
        _report_progress(index - 1, total, f"Panel {index}/{total}: {verb}…")

    def on_bubble_done(bubble_id: str, result, index: int, total: int) -> None:
        literal = _translator_text(result)
        adapted = result.ruling.final_line
        # A skipped (SFX/background) bubble's "literal" and "adapted"
        # are both just the untranslated source text - there is no real
        # translation for _explain_why (another LLM call) to explain,
        # so use the skip reason directly rather than spending a call
        # asking a model to narrate a no-op.
        why = (
            result.ruling.priority_tradeoffs_made
            if getattr(result, "skipped", False)
            else _explain_why(
                client, dna.artistic_thesis, literal, adapted, result.ruling.priority_tradeoffs_made
            )
        )
        panels_out.append({"id": bubble_id, "literal": literal, "adapted_text": adapted, "why": why})
        _report_progress(index, total, f"Panel {index}/{total}: done")

    final_room_memory = None

    def on_room_memory_done(room_memory) -> None:
        nonlocal final_room_memory
        final_room_memory = room_memory

    adapt_chapter(
        chapter, dna, client, on_stage=on_stage, on_bubble_done=on_bubble_done,
        on_room_memory_done=on_room_memory_done, deadline=deadline,
    )

    # Written back only for characters dna.characters actually has after
    # merge_character_bible above - a character who didn't appear this
    # chapter keeps whatever the bible already had, untouched.
    if bible_active and final_room_memory is not None:
        character_bibles.save_bible(
            user_id, series_name, character_bible_updates(dna, final_room_memory)
        )

    payload = {"chapter_dna": dna.model_dump(), "panels": panels_out}
    cache.set(
        result_id,
        payload,
        target_language=request.target_language,
        source_language=request.source_language,
    )
    _record_history(user_id, result_id, request.source_language, medium="webtoons")
    # Measured, not estimated (engine/models.py::LLMCallRecord) - same
    # pattern _adapt_or_serve_cached already logs for songs
    # (server/main.py's tokens_by_stage block above). Comics has only one
    # client (Chapter DNA, every panel's Writers' Room, and _explain_why
    # all share `client`, unlike the song path's separate cheap-model
    # explain_why_client), so there's nothing else to sum in here.
    calls = getattr(client, "call_log", [])
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
        "comics_adapt id=%s panels=%d llm_calls=%d llm_latency=%.2fs "
        "prompt_tokens=%d completion_tokens=%d by_stage=[%s]",
        result_id, len(non_empty_panels), len(calls), llm_latency,
        total_prompt, total_completion, stage_summary,
    )
    return payload


def _comics_adapt_or_serve_cached(
    request: ComicsAdaptRequest,
    http_request: Request,
    user_id: str | None,
    enforce_ip_quota: bool,
) -> dict:
    """The actual cache-hit / run-engine flow for a comics chapter,
    shared by /api/comics/adapt (browser, per-IP quota, session-derived
    user_id) and /v1/comics/adapt (public API, per-API-key quota already
    enforced by the caller before this runs, user_id resolved from the
    key instead of a session) - same split, same reasoning, as
    _adapt_or_serve_cached does for songs: only the auth/quota gating
    differs between the two callers, not what actually happens once a
    user_id is known.
    """
    non_empty_panels = [p for p in request.panels if p.text.strip()]
    if not non_empty_panels:
        raise HTTPException(
            status_code=400, detail="At least one panel with extracted text is required."
        )
    if len(non_empty_panels) > MAX_COMICS_PANELS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"That's over the {MAX_COMICS_PANELS}-panel limit for one "
                "chapter. Try a shorter chapter or a single episode."
            ),
        )

    result_id = cache.comics_content_id(
        [p.text for p in non_empty_panels],
        target_language=request.target_language,
        source_language=request.source_language,
    )
    cached = cache.get(result_id)
    if cached is not None:
        # Moved ahead of the quota/credit check below (it used to run
        # first here, unlike _adapt_or_serve_cached's equivalent for
        # songs) - a cache hit costs nothing to serve, so it must not
        # consume either the anonymous quota or a signed-in account's
        # balance, matching what this module's own docstring already
        # claims ("cache hits don't count against either").
        _record_history(user_id, result_id, request.source_language, medium="webtoons")
        return {"id": result_id, **cached}

    # Same split as _adapt_or_serve_cached: a real account (browser
    # session or API key, either way a real user_id) pays in credits,
    # charged per panel actually adapted; no account at all falls back
    # to the anonymous per-IP quota.
    debited = None
    if user_id is not None:
        debited = CREDITS_PER_PANEL * len(non_empty_panels)
        if not credits.deduct(user_id, debited, reason="adaptation", reference=result_id):
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Not enough credits for this chapter ({debited} needed). "
                    "Buy more credits on the pricing page."
                ),
            )
    elif enforce_ip_quota:
        _check_quota(_client_ip(http_request), kind="chapters")

    try:
        payload = _run_comics_adaptation(request, result_id, non_empty_panels, user_id)
    except ValidationError as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        logger.error("comics adapt engine failure: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="The engine hit a problem processing this chapter. Try again in a moment.",
        ) from exc
    except RuntimeError as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        logger.error("comics adapt configuration failure: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"id": result_id, **payload}


def _run_comics_job(
    job_id: str,
    request: ComicsAdaptRequest,
    result_id: str,
    non_empty_panels: list[ComicsPanelText],
    user_id: str | None,
    debited: int | None,
) -> None:
    """Entry point for a comics adaptation job - either the RQ task body
    directly (server/task_queue.py's worker calls this exact function;
    RQ's own per-job timeout plus one-job-per-worker-process model
    already bounds concurrency, no additional slot logic needed) or,
    when REDIS_URL isn't configured, the background-thread target for
    /api/comics/adapt/start's in-process fallback, gated by the
    _run_slots semaphore below."""
    if task_queue.use_queue():
        _run_comics_job_body(job_id, request, result_id, non_empty_panels, user_id, debited)
        return

    if not _run_slots.acquire(timeout=SLOT_ACQUIRE_TIMEOUT_SECONDS):
        logger.error(
            "comics job id=%s timed out waiting %ds for a free run slot", job_id, SLOT_ACQUIRE_TIMEOUT_SECONDS
        )
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        jobs.set_error(job_id, "Castia is at capacity right now. Please try again in a few minutes.")
        return
    try:
        _run_comics_job_body(job_id, request, result_id, non_empty_panels, user_id, debited)
    finally:
        _run_slots.release()


def _run_comics_job_body(
    job_id: str,
    request: ComicsAdaptRequest,
    result_id: str,
    non_empty_panels: list[ComicsPanelText],
    user_id: str | None,
    debited: int | None,
) -> None:
    """The actual engine run + jobs.py status storage, shared by both
    dispatch paths above - a semaphore/RQ concern above this line, an
    error-handling/credit-refund concern below it, deliberately kept
    separate so neither has to know about the other."""
    jobs.set_running(job_id)
    try:
        payload = _run_comics_adaptation(
            request, result_id, non_empty_panels, user_id, job_id=job_id
        )
        jobs.set_done(job_id, {"id": result_id, **payload})
    except ValidationError as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        jobs.set_error(job_id, str(exc))
    except LLMError as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        logger.error("comics job id=%s engine failure: %s", job_id, exc)
        jobs.set_error(
            job_id, "The engine hit a problem processing this chapter. Try again in a moment."
        )
    except RuntimeError as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        logger.error("comics job id=%s configuration failure: %s", job_id, exc)
        jobs.set_error(job_id, str(exc))
    except Exception as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        logger.exception("comics job id=%s unexpected failure", job_id)
        # A background job's failure reaches no user and no HTTP status -
        # without this it exists only as one line in a log nobody is
        # watching. Identifiers only, never chapter content.
        monitoring.capture_exception(exc, job_id=job_id, kind="comics_adapt")
        jobs.set_error(job_id, "Something went wrong processing this chapter. Try again.")


@app.get("/api/comics/adapt/{result_id}")
def get_comics_adapt(result_id: str) -> dict:
    """Read side of the persistence above — mirrors GET /api/adapt/{id}
    for the future /comics/s/{id} share page."""
    cached = cache.get(result_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No result found for this link.")
    return {"id": result_id, **cached}


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


@app.post("/api/auth/register")
def auth_register(request: RegisterRequest, http_request: Request) -> dict:
    """Called by web/app/api/auth/register - the email/password
    counterpart to /api/users/sync above. Always {"status": "ok"} on a
    well-formed request (see server/password_auth.py's no-enumeration
    rule) - a 400 here means the input itself was invalid (bad email
    shape, too-short password), never "this email is taken"."""
    _require_internal_secret(http_request)
    # Before the expensive PBKDF2 hash inside register() - see
    # AUTH_REGISTER_DAILY_LIMIT's comment for why this exists.
    if not quota.check_and_increment(
        _client_ip(http_request), AUTH_REGISTER_DAILY_LIMIT, scope=AUTH_REGISTER_QUOTA_SCOPE
    ):
        raise HTTPException(status_code=429, detail="Too many signup attempts. Try again tomorrow.")
    try:
        result = password_auth.register(request.email, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Accounts need a database (DATABASE_URL is unset on this deployment).",
        )
    return result


@app.post("/api/auth/login")
def auth_login(request: LoginRequest, http_request: Request) -> dict:
    """Called from next-auth/providers/credentials's authorize()
    (web/auth.ts), never directly from a browser. Always 200 - the
    response's `status` field ("ok" | "unverified" | "invalid") is what
    the caller branches on, so a wrong password and an unreachable
    database don't have to be told apart by HTTP status alone."""
    _require_internal_secret(http_request)
    # Before the expensive PBKDF2 hash inside authenticate() - runs even
    # for a nonexistent email (password_auth._DUMMY_HASH) - see
    # AUTH_LOGIN_DAILY_LIMIT's comment for why this exists. A 429 here
    # breaks this endpoint's usual "always 200, branch on `status`"
    # contract, same as the other quota-gated endpoints in this file -
    # the credentials provider (web/auth.ts) surfaces a non-ok response
    # as a generic sign-in failure either way.
    if not quota.check_and_increment(
        _client_ip(http_request), AUTH_LOGIN_DAILY_LIMIT, scope=AUTH_LOGIN_QUOTA_SCOPE
    ):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again tomorrow.")
    return password_auth.authenticate(request.email, request.password)


@app.post("/api/auth/verify-email")
def auth_verify_email(request: VerifyEmailRequest, http_request: Request) -> dict:
    _require_internal_secret(http_request)
    ok = password_auth.verify_email_token(request.token)
    if not ok:
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired.")
    return {"status": "ok"}


@app.post("/api/auth/resend-verification")
def auth_resend_verification(request: ResendVerificationRequest, http_request: Request) -> dict:
    _require_internal_secret(http_request)
    return password_auth.resend_verification(request.email)


@app.post("/api/auth/forgot-password")
def auth_forgot_password(request: ForgotPasswordRequest, http_request: Request) -> dict:
    _require_internal_secret(http_request)
    # See PASSWORD_RESET_DAILY_LIMIT's comment: this is the only lever
    # available to stop the endpoint being used to spam a victim's inbox,
    # since the response itself can never reveal whether the email exists.
    if not quota.check_and_increment(
        _client_ip(http_request), PASSWORD_RESET_DAILY_LIMIT, scope=PASSWORD_RESET_QUOTA_SCOPE
    ):
        raise HTTPException(status_code=429, detail="Too many password reset requests. Try again tomorrow.")
    return password_auth.request_password_reset(request.email)


@app.post("/api/auth/reset-password")
def auth_reset_password(request: ResetPasswordRequest, http_request: Request) -> dict:
    _require_internal_secret(http_request)
    try:
        result = password_auth.reset_password(request.token, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result["status"] != "ok":
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    return result


@app.post("/webhooks/paddle")
async def paddle_webhook(request: Request) -> dict:
    """Paddle calls this on every transaction/subscription event -
    verifies the Paddle-Signature header against the raw body
    (server/paddle.py has the full format, sourced from Paddle's own
    docs) and, for transaction.completed, credits the account named in
    that checkout's custom_data.user_id (web/lib/paddle.ts sets this when
    opening checkout - there is no other reliable way to attach a Paddle
    transaction back to a Castia account).

    Reads the body as raw bytes BEFORE any JSON parsing - the signature
    is computed over the exact bytes Paddle sent, and Pydantic parsing
    a request body here (like every other POST endpoint in this file
    does) would only ever hand this the already-decoded object, too late
    to verify anything against.

    503s if CASTIA_PADDLE_WEBHOOK_SECRET isn't set (webhooks are simply
    off, not silently accepted unverified) - same "off, not insecure"
    convention as INTERNAL_API_SECRET.

    This is the one `async def` endpoint in this file - every other one
    is plain `def`, which FastAPI dispatches to Starlette's threadpool
    automatically (see this module's docstring), so a blocking call
    inside it never stalls the event loop. `await request.body()` needs
    an actual coroutine to run in, which is the only reason this
    function is declared `async def` at all - but `paddle.handle_webhook`
    itself is synchronous, blocking Postgres I/O (server/paddle.py,
    server/credits.py), and calling it directly here would run that
    inside THIS coroutine, on the event loop itself - blocking every
    other request this process is serving (including /health) for the
    duration of two DB round-trips, the one place in this file that
    actually broke its own async/sync discipline. Routed through
    run_in_threadpool for exactly the reason every plain `def` endpoint
    already gets this for free.
    """
    if not PADDLE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Paddle webhooks aren't configured on this deployment.",
        )

    raw_body = await request.body()
    try:
        await run_in_threadpool(
            paddle.handle_webhook, raw_body, request.headers.get("paddle-signature"), PADDLE_WEBHOOK_SECRET
        )
    except paddle.PaddleWebhookError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/api/me/adaptations")
def me_adaptations(
    http_request: Request,
    favorites_only: bool = False,
    collection_id: str | None = None,
    medium: str | None = None,
) -> dict:
    """medium ("music" | "webtoons") narrows the list the same way
    favorites_only/collection_id do; omitted, returns both mediums in one
    combined, newest-first timeline - see accounts.list_adaptations's
    docstring for why that's the default rather than music-only."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    try:
        adaptations = accounts.list_adaptations(
            user_id, favorites_only=favorites_only, collection_id=collection_id, medium=medium
        )
    except ValueError as exc:  # malformed collection_id UUID
        raise HTTPException(status_code=400, detail="Invalid collection id.") from exc
    return {"adaptations": adaptations}


@app.get("/api/me/credits")
def me_credits(http_request: Request) -> dict:
    """Backs the real Billing/Usage dashboard pages
    (web/app/dashboard/billing, /usage) - the actual balance and ledger
    history (server/credits.py), not the DashboardStub placeholder both
    used to be. `balance` is None only when there's no database at all
    (accounts don't exist, not "this account has 0 credits" - see
    credits.get_balance's own docstring for why those two states must
    never be confused)."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    return {
        "balance": credits.get_balance(user_id),
        "transactions": credits.list_transactions(user_id),
    }


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


@app.get("/api/me/api-keys")
def me_list_api_keys(http_request: Request) -> dict:
    """Never returns a raw key or hash - server/api_keys.py::list_keys
    only ever exposes each key's prefix, same one-time-reveal convention
    as GitHub/Stripe."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    return {"apiKeys": api_keys.list_keys(user_id)}


@app.post("/api/me/api-keys")
def me_create_api_key(request: ApiKeyRequest, http_request: Request) -> dict:
    """Returns the RAW key exactly once - the dashboard settings page
    must show it to the human immediately and never again."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    name = request.name.strip() or "Unnamed key"
    created = api_keys.generate_key(user_id, name)
    if created is None:
        raise HTTPException(
            status_code=503,
            detail="API keys need a database (DATABASE_URL is unset on this deployment).",
        )
    return created


@app.delete("/api/me/api-keys/{key_id}")
def me_revoke_api_key(key_id: str, http_request: Request) -> dict:
    """Scoped by user_id (server/api_keys.py::revoke_key) - a key
    belonging to someone else 404s, indistinguishable from one that
    doesn't exist."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    if not api_keys.revoke_key(user_id, key_id):
        raise HTTPException(status_code=404, detail="No such API key.")
    return {"id": key_id, "revoked": True}


@app.get("/api/me/export")
def me_export(http_request: Request) -> dict:
    """The "right of access" web/app/privacy states as real practice -
    everything this account owns, including the adapted results
    themselves rather than just ids pointing at them. Excludes credential
    material (password hash, API key hashes): those aren't the user's
    data to receive, they're the secrets protecting it, and putting them
    in a downloadable file would turn an export into a leak vector."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    data = accounts.export_account_data(user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="No such account.")
    return data


@app.delete("/api/me")
def me_delete(http_request: Request) -> dict:
    """The "right of erasure" half. Irreversible: removes the account and
    every row belonging to it, plus any cached result no remaining
    adaptation still references (see accounts.delete_account for why
    shared, content-addressed results are handled that carefully).

    Confirming intent is the caller's job - the Next.js side requires the
    user to type their email to enable the button. This endpoint does not
    second-guess a request that arrives with a valid internal secret."""
    _require_internal_secret(http_request)
    user_id = _required_user_id(http_request)
    if not accounts.delete_account(user_id):
        raise HTTPException(status_code=404, detail="No such account.")
    logger.info("account deleted user_id=%s", user_id)
    return {"deleted": True}


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
                f"CASTIA currently supports: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
            ),
        )
    if source_language != "unspecified":
        if source_language not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{source_language!r} isn't a supported source language. "
                    f"CASTIA currently supports: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
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


def _record_history(
    user_id: str | None, result_id: str, source_language: str, medium: str = "music"
) -> None:
    """History is an enhancement to an adapt request, never a gate on it —
    a failure here is logged and swallowed so the user still gets their
    result."""
    if not user_id:
        return
    try:
        accounts.record_adaptation(user_id, result_id, source_language, medium=medium)
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
    job_id: str | None = None,
) -> dict:
    """The actual engine run: Song DNA -> Writers' Room -> Judge, then
    verification and cache write. Shared by the blocking /api/adapt
    endpoint and the background job /api/adapt/start kicks off - callers
    differ only in how they turn an LLMError/RuntimeError into a response
    (an HTTPException here, a job's stored `error` string there), so
    those propagate uncaught rather than being translated in here.

    `job_id`, when given (only the background job path passes one - the
    synchronous /api/adapt endpoint has no job to report against and
    blocks until this returns anyway), turns on incremental progress
    reporting via jobs.set_progress - the song-side equivalent of
    server/main.py's _run_comics_adaptation. The very first write happens
    below, before run_engine (and the Song DNA generation inside it) even
    starts: without it, a poller sees nothing at all - not even a
    section count - until the first section begins, and Song DNA
    generation is itself a real LLM call that can be slow under the same
    rate-limiting a song's sections can hit.

    `deadline` bounds the whole run (engine/pipeline.py's
    EngineTimeoutError, SONG_JOB_TIMEOUT_SECONDS above) - see that
    module's docstring for why this exists on top of every individual
    LLM call already having its own timeout.
    """
    logger.info(
        "%s id=%s ip=%s source=%s target=%s cache=miss sections=%d chars=%d starting engine run",
        log_prefix, result_id, ip, source_language, target_language, len(sections), len(text),
    )

    def _report_progress(completed: int, total: int, message: str) -> None:
        if job_id is None:
            return
        jobs.set_progress(job_id, {"completed": completed, "total": total, "message": message})

    _report_progress(0, len(sections), "Reading song…")

    def on_stage(section_name: str, index: int, total: int) -> None:
        _report_progress(index - 1, total, f"Section {index}/{total}: adapting…")

    def on_section_done(section_name: str, result, index: int, total: int) -> None:
        _report_progress(index, total, f"Section {index}/{total}: done")

    client = create_default_client()
    deadline = time.monotonic() + SONG_JOB_TIMEOUT_SECONDS
    # apply_corrective_pass: verify.py runs once against the raw output,
    # and any error-severity finding gets one bounded re-judge
    # (engine/pipeline.py's Phase 2 corrective pass) before this ships to
    # a real user — not just logged after the fact.
    engine_result = run_engine(
        song,
        client=client,
        room_version="v1",
        apply_corrective_pass=True,
        on_stage=on_stage,
        on_section_done=on_section_done,
        deadline=deadline,
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
    # now. `client=client` additionally runs the cross-language emotional
    # fidelity check (engine/verify.py::check_cross_language_fidelity) —
    # one extra LLM call per section, reading the actual source text
    # directly rather than the Translator's own English anchor, which is
    # the one thing nothing else in this pipeline ever double-checks.
    # Warning-severity only (never triggers a retry) - a probabilistic
    # judgment about emotional tone, not a fact to auto-correct against.
    report = verify_result(engine_result.to_dict(), client=client)
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

    # Best-effort corpus collection for docs/CAPABILITY_MATRIX.md's
    # "Genre-aware calibration" deferred gap - see server/genre_corpus.py's
    # module docstring for why this only accumulates data and calibrates
    # nothing. Never allowed to affect the actual response either way.
    genre_corpus.record_calibration_sample(
        result_id, engine_result.dna.genre_feel, source_language, target_language, report
    )

    # Song-level (a correlation needs the whole song's sections, not one),
    # so it doesn't fit the per-section shape mapping.py already builds -
    # attached here instead. None for non-English targets or songs with
    # too few CMU-resolvable sections; the frontend must treat null as
    # "not computed," never as a zero score.
    experience_result["phonemeRepetitionSimilarity"] = report.phoneme_repetition_similarity

    if request.youtube_section_timings:
        # Not YouTube-specific despite the field name (kept as-is rather
        # than renamed - it's the same positional, engine-never-sees-it
        # timing either way): lib/lyricsImport.ts's .lrc/.srt import
        # produces this same shape with no video at all, so timing
        # attachment no longer requires youtube_video_id - only embedding
        # a sync player (ResultScreen.tsx) does, gated separately below.
        timings = request.youtube_section_timings
        result_sections = experience_result["sections"]
        if len(timings) == len(result_sections):
            if request.youtube_video_id:
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


def _adapt_or_serve_cached(
    request: AdaptRequest,
    http_request: Request,
    user_id: str | None,
    enforce_ip_quota: bool,
    log_prefix: str = "adapt",
) -> dict:
    """The actual cache-hit / fuzzy-hit / run-engine flow, shared by
    /api/adapt (browser, per-IP quota, session-derived user_id) and
    /v1/adapt (public API, per-API-key quota already enforced by the
    caller before this runs, user_id resolved from the key instead of a
    session). Only the auth/quota gating differs between the two
    callers - this is the part that must not drift between them.
    """
    started = time.monotonic()
    ip = _client_ip(http_request)
    text, target_language, source_language = _validate_adapt_request(request)

    result_id = cache.content_id(text, target_language=target_language, source_language=source_language)
    cached = cache.get(result_id)
    if cached is not None:
        # A cache hit is still this user asking for this song — history
        # records the relationship, not the compute.
        _record_history(user_id, result_id, source_language)
        logger.info(
            "%s id=%s ip=%s source=%s target=%s cache=hit duration=%.2fs",
            log_prefix, result_id, ip, source_language, target_language, time.monotonic() - started,
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
            "%s id=%s ip=%s source=%s target=%s cache=fuzzy_hit matched=%s similarity=%.3f duration=%.2fs",
            log_prefix, result_id, ip, source_language, target_language, matched_id, similarity,
            time.monotonic() - started,
        )
        return matched_result

    sections, song = _build_song(text, target_language, source_language)

    # Signed-in (either a browser session or an API key, both resolve a
    # real user_id) means a real account with a real balance - that's
    # what gates cost here, not the anonymous per-IP quota, which stays
    # reserved for requests with no account behind them at all. Charged
    # per section actually built, not a flat per-submission price
    # (CREDITS_PER_SECTION's comment), and debited BEFORE the engine
    # runs - see _run_adaptation's failure handling below for why a
    # failed run refunds rather than this waiting until success.
    debited = None
    if user_id is not None:
        debited = CREDITS_PER_SECTION * len(sections)
        if not credits.deduct(user_id, debited, reason="adaptation", reference=result_id):
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Not enough credits for this song ({debited} needed). "
                    "Buy more credits on the pricing page."
                ),
            )
    elif enforce_ip_quota:
        _check_quota(ip)

    try:
        return _run_adaptation(
            request, result_id, text, target_language, source_language, sections, song, ip, started,
            log_prefix=log_prefix,
            user_id=user_id,
        )
    except LLMError as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        logger.error("%s id=%s engine failure: %s", log_prefix, result_id, exc)
        raise HTTPException(
            status_code=502,
            detail="The engine hit a problem processing this song. Try again in a moment.",
        ) from exc
    except RuntimeError as exc:
        if debited is not None:
            credits.refund(user_id, debited, reference=result_id)
        logger.error("%s id=%s configuration failure: %s", log_prefix, result_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/adapt")
def adapt(request: AdaptRequest, http_request: Request) -> dict:
    user_id = _authed_user_id(http_request)
    return _adapt_or_serve_cached(request, http_request, user_id, enforce_ip_quota=True)


@app.get("/api/adapt/{result_id}")
def get_adapt(result_id: str) -> dict:
    cached = cache.get(result_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="No result found for this link.")
    return cached


# Everything below (_run_slots, SLOT_ACQUIRE_TIMEOUT_SECONDS) governs
# ONLY the in-process threading fallback used when REDIS_URL isn't set
# (local dev, the test suite, or a deployment that hasn't configured the
# queue yet) - see server/task_queue.py's module docstring. When
# REDIS_URL IS set, concurrency is governed by how many worker processes/
# replicas the separate worker Railway service runs instead, and none of
# this is consulted at all (_run_job/_run_comics_job's first check is
# task_queue.use_queue()).
#
# Bounds how many engine runs can be mid-flight at once in THIS process,
# regardless of how many /api/adapt/start requests land at the same
# time. Each run is several dozen sequential LLM calls at its peak (a
# full multi-section song) - with no cap, a burst of concurrent
# submissions would all hit the LLM provider simultaneously and risk
# provider-side rate-limit failures across every concurrent job, not
# just the newest one. The number itself is a starting guess, not a
# measured ceiling - tune via CASTIA_MAX_CONCURRENT_RUNS.
MAX_CONCURRENT_RUNS = int(os.environ.get("CASTIA_MAX_CONCURRENT_RUNS", "4"))
_run_slots = threading.Semaphore(MAX_CONCURRENT_RUNS)
# `with _run_slots:` blocks forever if a slot never comes free - fine
# when every job eventually finishes and releases its slot, not fine if
# one ever doesn't (an upstream call that hangs past its own timeout at
# the transport level, a bug in a retry path, anything that leaves a
# thread never reaching its `finally`). One such leaked slot is
# permanent for the life of the process - MAX_CONCURRENT_RUNS is small
# (4 by default), so it doesn't take many before every NEW job, however
# trivial, queues forever behind slots that are never coming back -
# indistinguishable from the engine itself hanging, from the poller's
# side. Bounding the wait turns that into a fast, clear "try again"
# instead of a silent, unbounded queue.
SLOT_ACQUIRE_TIMEOUT_SECONDS = int(os.environ.get("CASTIA_SLOT_ACQUIRE_TIMEOUT_SECONDS", str(3 * 60)))


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
    """Entry point for a song adaptation job - either the RQ task body
    directly (REDIS_URL set - see server/task_queue.py's module
    docstring for why no additional slot logic is needed there) or the
    in-process threading fallback's background-thread target, gated by
    the _run_slots semaphore below."""
    if task_queue.use_queue():
        _run_job_body(
            job_id, request, result_id, text, target_language, source_language, sections, song, ip, started, user_id,
        )
        return

    if not _run_slots.acquire(timeout=SLOT_ACQUIRE_TIMEOUT_SECONDS):
        logger.error("job id=%s timed out waiting %ds for a free run slot", job_id, SLOT_ACQUIRE_TIMEOUT_SECONDS)
        jobs.set_error(job_id, "Castia is at capacity right now. Please try again in a few minutes.")
        return
    try:
        _run_job_body(
            job_id, request, result_id, text, target_language, source_language, sections, song, ip, started, user_id,
        )
    finally:
        _run_slots.release()


def _run_job_body(
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
    jobs.set_running(job_id)
    try:
        experience_result = _run_adaptation(
            request, result_id, text, target_language, source_language, sections, song, ip, started,
            log_prefix="job", user_id=user_id, job_id=job_id,
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
    except Exception as exc:
        # A background thread's uncaught exception is otherwise silent -
        # nothing re-raises it anywhere the poller would see. Whoever's
        # polling deserves an "error" status, not an indefinite "pending".
        logger.exception("job id=%s unexpected failure", job_id)
        # ...and whoever maintains this deserves to hear about it without
        # having to be reading logs at the time. Identifiers only, never
        # the lyrics themselves.
        monitoring.capture_exception(exc, job_id=job_id, kind="song_adapt")
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

    if task_queue.use_queue():
        task_queue.get_queue().enqueue(
            _run_job,
            job_id, request, result_id, text, target_language, source_language, sections, song, ip, started, user_id,
            job_timeout=SONG_JOB_TIMEOUT_SECONDS + 120,
        )
    else:
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


# --- Public API (v1) ---------------------------------------------------
# For third-party callers with an API key (server/api_keys.py), not the
# Next.js server or a signed-in browser session - a genuinely different
# trust chain from every /api/* route above. Thin wrappers: no new
# engine behavior, just the existing adapt flows gated by
# _require_api_key instead of a session, and without the per-IP browser
# quota (the per-key daily limit is the real gate here). Deliberately
# synchronous, same disclosed limitation /api/adapt itself had before
# /api/adapt/start existed - no async job/poll pattern for v1 callers
# yet.


@app.post("/v1/adapt")
def v1_adapt(request: AdaptRequest, http_request: Request) -> dict:
    api_key_context = _require_api_key(http_request)
    return _adapt_or_serve_cached(
        request,
        http_request,
        api_key_context["user_id"],
        enforce_ip_quota=False,
        log_prefix="v1_adapt",
    )


@app.post("/v1/comics/adapt")
def v1_comics_adapt(request: ComicsAdaptRequest, http_request: Request) -> dict:
    api_key_context = _require_api_key(http_request)
    return _comics_adapt_or_serve_cached(
        request, http_request, api_key_context["user_id"], enforce_ip_quota=False
    )
