# AURA engine API. Build from the repo root:
#   docker build -t aura-api .
#   docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... aura-api
#
# Mount a volume at /app/server/.cache to persist results (and their
# shareable URLs) across container restarts:
#   docker run -p 8000:8000 -e OPENAI_API_KEY=sk-... \
#     -v aura-cache:/app/server/.cache aura-api
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/ engine/
COPY server/ server/

EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
