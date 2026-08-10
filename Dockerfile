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
# own module docstrings for the full picture. Scale real concurrent job
# capacity by adding replicas of the WORKER service, not this one -
# server/main.py's own request handling is cheap; the worker is where
# the actual engine runs happen.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/ engine/
COPY server/ server/

EXPOSE 8000

CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}
