# CASTIA engine API. Build from the repo root:
#   docker build -t castia-api .
#   docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... castia-api
#
# Mount a volume at /app/server/.cache to persist results (and their
# shareable URLs) across container restarts:
#   docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... \
#     -v castia-cache:/app/server/.cache castia-api
#
# Binds to $PORT if set, defaulting to 8000 for local `docker run` above.
# Platforms like Railway assign their own port and route traffic to it —
# a container that ignores $PORT and always listens on 8000 can build and
# start successfully while still being unreachable from the outside,
# which looks identical to a crash from the platform's health check.
#
# Panel OCR (/api/comics/ocr, engine/comics_ocr.py) calls Google Cloud
# Vision over plain HTTPS with an API key - GOOGLE_CLOUD_VISION_API_KEY
# must be set in this deployment's environment for that endpoint to
# work (unset, it returns a clear error rather than failing silently).
# No system package needed for it (replaces an earlier Tesseract-based
# scaffold that DID need one per language - see docs/CAPABILITY_MATRIX.md).
#
# This same image also runs the worker service (server/worker.py,
# server/task_queue.py) - a second Railway service built from this
# identical Dockerfile, with its Start Command overridden in that
# service's Railway settings to:
#   python -m server.worker
# instead of this file's own CMD below. It needs the same environment
# variables as this web service (OPENAI_API_KEY, ANTHROPIC_API_KEY,
# DATABASE_URL, GOOGLE_CLOUD_VISION_API_KEY, CASTIA_INTERNAL_API_SECRET,
# etc.) plus REDIS_URL, which this web service also needs set for either
# of them to do anything - REDIS_URL is what turns on the whole queue
# path; unset, both this service and the worker fall back to (or in the
# worker's case, refuse to start under) the pre-queue in-process
# threading behavior. See server/task_queue.py's and server/worker.py's
# own module docstrings for the full picture. Scale actual engine-run
# throughput (song/chapter generation) by adding replicas of the WORKER
# service, not this one - that work is already queued off this process
# when REDIS_URL is set.
#
# This service (the web/API tier) still has its own, separate
# concurrency axis: every request that ISN'T a queued engine run - auth,
# quota checks, cached-result lookups, dashboard/history, the two
# synchronous per-panel comics endpoints - is handled right here, and
# until this was measured, this container ran uvicorn as a single
# Python process no matter how many CPUs the instance actually had.
# CASTIA_WEB_CONCURRENCY (default 2, tune to the instance's real vCPU
# count) runs that many independent worker processes, so a burst of
# concurrent requests is spread across real cores instead of a single
# process's GIL and single 40-slot threadpool - see server/main.py's
# THREADPOOL_SIZE and server/db.py's pool-sizing comments for how those
# two scale alongside this. Confirmed empirically (docs/CAPABILITY_MATRIX.md)
# that this materially raises real concurrent-request capacity, not just
# in theory.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/ engine/
COPY server/ server/

EXPOSE 8000

CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${CASTIA_WEB_CONCURRENCY:-2}
