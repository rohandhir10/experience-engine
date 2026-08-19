---
name: security-capacity-audit
description: >
  Run a security and scalability audit of this repo's FastAPI backend
  (server/, engine/) and its interaction with the Next.js frontend
  (web/) — the same categories that produced real fixes here before:
  auth rate-limiting/brute-force, IP-spoofing via X-Forwarded-For, timing
  attacks on secret comparison, real concurrent-request capacity, DB
  migration races under multiple workers, internal error leakage to end
  users, resource-exhaustion on user uploads, and vulnerable/misplaced
  dependencies. Use this whenever the user asks for a security audit, a
  scalability/capacity review, "will this hold up under load," a
  pen-test-style pass, or mentions rate limiting, DoS, IP spoofing, or
  "thousands of users at once." Every finding this produces gets fixed and
  verified via the fix-verify-document skill — don't stop at the report.
---

# Security & capacity audit (Castia / experience-engine)

This is a checklist of specific failure classes that have actually existed
in this codebase, not a generic OWASP-Top-10 recitation. Work through each
category by reading the real code, not by assuming it's fine because it
was fine last time — code drifts.

For every finding: confirm it's real (don't report a hypothetical), then
hand off to the **fix-verify-document** skill to fix, test, verify, and
document it. Don't just produce a report and stop.

## 1. Auth rate-limiting / brute-force DoS

Check `server/quota.py` (`quota.check_and_increment`) and how
`/api/auth/register`, `/api/auth/login`, and any password-reset endpoints
in `server/main.py` use it. Ask:
- Is there a per-IP AND a per-account limit, or just one?
- Is the limit checked *before* doing expensive work (password hashing,
  DB round-trips), or after — a check placed after expensive work is
  itself a CPU-exhaustion DoS vector even if the limit exists.
- Are the limits (`AUTH_REGISTER_DAILY_LIMIT`, `AUTH_LOGIN_DAILY_LIMIT` in
  `server/main.py`) sane for a real product, not accidentally 0 or
  unlimited in some code path (e.g. an internal/service-to-service bypass
  that's reachable from the public internet).

## 2. IP-spoofing via X-Forwarded-For

Check `server/main.py::_client_ip` and the `TRUSTED_PROXY_HOPS` /
`CASTIA_TRUSTED_PROXY_HOPS` setting. The bug class here: trusting the
*leftmost* entry in `X-Forwarded-For` lets any direct caller set their own
"IP" and walk straight past per-IP quota, since only the real proxy chain
should be trusted, and only from the right. Confirm the code trusts
exactly the rightmost N hops (N = number of proxies actually in front of
this service in production), not an arbitrary or attacker-controlled
depth.

## 3. Timing-attack-unsafe secret comparisons

Grep for `==` or `!=` comparisons against secrets, tokens, or API keys in
`server/main.py` (e.g. `_require_internal_secret`, `_authed_user_id`, any
`X-Castia-*` header check) and in `server/password_auth.py` /
`server/paddle.py` webhook signature checks. Python's `==` on strings
short-circuits on the first mismatched byte, which leaks comparison
timing. Anything comparing a caller-supplied value against a real secret
must use `hmac.compare_digest` (see `_secret_matches` in `server/main.py`
for the existing pattern to follow/extend).

## 4. Real concurrent-request capacity

"Does it work with N concurrent users" is not answered by unit tests. Check:
- `Dockerfile`'s `uvicorn` `CMD` — is `--workers` wired to
  `CASTIA_WEB_CONCURRENCY` (not hardcoded to 1)?
- `server/main.py`'s `_lifespan` — is the AnyIO threadpool sized via
  `anyio.to_thread.current_default_thread_limiter().total_tokens` (see
  `CASTIA_THREADPOOL_SIZE` / `THREADPOOL_SIZE`)? The default AnyIO
  threadpool cap (40) will silently serialize any endpoint that does
  blocking I/O (webhook handling, image processing) under load, well below
  what the process could otherwise handle.
- Any coroutine handler calling something blocking (webhook signature
  verification, image decode/encode, external HTTP calls made
  synchronously) directly instead of via `run_in_threadpool` — that blocks
  the whole event loop for every other concurrent request on that worker.
- `server/db.py`'s pool sizing (`POOL_SIZE`/`MAX_OVERFLOW`) — remember
  these are **per worker process**; the real ceiling is
  `(POOL_SIZE + MAX_OVERFLOW) * CASTIA_WEB_CONCURRENCY`, and that number
  needs to actually fit inside Postgres's `max_connections`.

If you want an empirical answer rather than just a code read, run a real
load test against a locally stood-up stack (see fix-verify-document's
"live verification" section for how to stand one up) with `hey` or a small
async client hammering an endpoint concurrently, and watch for latency
cliffs or connection-pool exhaustion errors.

## 5. Migration races under multiple workers

If `--workers` > 1 and migrations run automatically on startup
(`server/db.py::migrate_to_head`), every worker process races to run
`alembic upgrade head` at boot. Confirm there's a Postgres advisory lock
(`pg_advisory_lock`/`pg_advisory_unlock`, keyed by
`_MIGRATION_LOCK_KEY = zlib.crc32(...)`) wrapping the upgrade call, gated
to `engine.dialect.name == "postgresql"` (sqlite has no advisory locks and
doesn't need this — it's single-file, not a race).

This one doesn't fail loudly without the lock — it can hang indefinitely
rather than error, which falsification-testing (revert the lock, run
concurrent migrations against a real Postgres, watch it hang) is the only
reliable way to catch. See fix-verify-document step 5.

## 6. Internal error message leakage to end users

Search for `detail=str(exc)`, `jobs.set_error(job_id, str(exc))`, or
similar patterns in `server/main.py`'s exception handlers (sync endpoint
handlers and background job handlers, for both `/api/adapt` and
`/api/comics/adapt`). A bare `except Exception`/`except RuntimeError` that
forwards `str(exc)` to the caller can leak configuration details,
stack-trace fragments, or literal secrets (e.g. a misconfigured
`OPENAI_API_KEY=sk-...` embedded in an error string) straight into the
HTTP response or job status the browser polls.

The nuance: not every `RuntimeError` should be genericized.
`EngineTimeoutError` (`engine/pipeline.py`) and `ChapterTimeoutError`
(`engine/comics_adapt.py`) are `RuntimeError` subclasses *deliberately*
carrying actionable, user-safe messages ("taking longer than the
configured time limit... try again with fewer sections"). The fix pattern
is: catch the specific timeout subclasses first (forward their message
verbatim, HTTP 504), and only genericize the remaining, broader
`RuntimeError`/`Exception` catch — while still `logger.error`-ing the real
message server-side. Check all four call sites (sync + background job,
song + comics) stay consistent with each other.

## 7. Resource-exhaustion on user uploads

Check `engine/comics_redraw.py::_load_image` (and any other place that
calls `Image.open` on user-supplied bytes) for a pixel-count ceiling
checked from the image *header* (`image.size`) before the expensive
`.load()`/decode call — a decompression-bomb-style small file that claims
an enormous decoded size can exhaust memory/CPU otherwise. Confirm the
ceiling is configurable (`engine/config.py::MAX_IMAGE_PIXELS`, env
`CASTIA_MAX_IMAGE_PIXELS`) and actually enforced, not just present as a
constant nothing reads.

## 8. Dependency hygiene

- `pip list --outdated` / check `requirements.txt` against known
  advisories for anything with a history of real incidents (not just any
  CVE — e.g. `deep-translator`'s PYSEC-2022-252 account-takeover
  advisory was the trigger for isolating it into
  `requirements-benchmark.txt`, since it's benchmark-only tooling never
  shipped in the production Docker image).
- `npm audit` in `web/` for the frontend.
- Confirm dev/benchmark-only dependencies aren't bundled into what
  actually ships (check the `Dockerfile` COPY/pip install lines against
  what's in `requirements.txt` vs. any `-benchmark`/`-dev` split file).

## After the audit

List findings by severity, then work through them one at a time with the
**fix-verify-document** skill — investigate root cause, fix, test,
falsify (for anything in categories 1-5), verify live if runtime-shaped,
document in `docs/CAPABILITY_MATRIX.md`, commit. Don't batch unrelated
fixes into one commit.
