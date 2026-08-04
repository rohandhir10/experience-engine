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

# tesseract-ocr: the system binary engine/comics_ocr.py shells out to
# (via pytesseract) for /api/comics/ocr. Only the English language data
# (tesseract-ocr-eng, pulled in automatically as tesseract-ocr's
# dependency) is installed - see that module's docstring for what that
# means for AURA's other five supported languages until their data
# packages (tesseract-ocr-hin/jpn/kor/spa/urd) are added here too.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY engine/ engine/
COPY server/ server/

EXPOSE 8000

CMD uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8000}
