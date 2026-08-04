# AURA engine API. Build from the repo root:
#   docker build -t aura-api .
#   docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... aura-api
#
# Mount a volume at /app/server/.cache to persist results (and their
# shareable URLs) across container restarts:
#   docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... \
#     -v aura-cache:/app/server/.cache aura-api
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
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/ engine/
COPY server/ server/

EXPOSE 8000

CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}
