"""Content-addressed cache for adaptation results.

If two different users paste the exact same song, there's no reason to
pay for and wait on a second engine run — this hashes the normalized
input text into an id, and that same id doubles as the shareable URL
slug (/s/<id> in the frontend). Exact-text matching only, deliberately:
two near-identical pastes of the same song (different line breaks, a
typo) are treated as different songs rather than attempting fuzzy
song-identity matching, which is a harder problem not worth solving until
there's evidence exact-match caching alone isn't catching real repeats.

File-based, not a database — this is still a local-only project, and a
JSON file per id is the simplest thing that actually works at this stage.

VENDORED-COPY NOTE: the canonical version of this file (repo root,
server/cache.py) writes next to itself, which is correct for the
Docker/uvicorn deployment where the process directory is writable and
persists across requests. This copy runs as a Vercel serverless function
instead, where the deployed bundle directory is read-only at runtime —
writing there would raise PermissionError on first use. /tmp is Vercel's
guaranteed-writable directory, so this fork uses it instead. The real
cost of that: /tmp is ephemeral per function instance, not shared across
instances or persisted across cold starts, so caching and the /s/<id>
share links only work best-effort, within a warm instance — not the
durable, cross-request cache the Docker deployment gets. Worth knowing,
not silently swallowed.
"""
from __future__ import annotations

import hashlib
import json
import re
import tempfile
from pathlib import Path

CACHE_DIR = Path(tempfile.gettempdir()) / "aura-cache"

_WHITESPACE_RE = re.compile(r"[ \t]+")


def normalize_text(text: str) -> str:
    lines = [ _WHITESPACE_RE.sub(" ", line).strip() for line in text.strip().splitlines() ]
    return "\n".join(line for line in lines if line)


def content_id(text: str) -> str:
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def get(result_id: str) -> dict | None:
    path = CACHE_DIR / f"{result_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def set(result_id: str, result: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{result_id}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
