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
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/ engine/
COPY server/ server/

EXPOSE 8000

CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}
