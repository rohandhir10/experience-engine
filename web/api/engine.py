"""Vercel Python serverless function entrypoint.

Vercel's Python runtime detects a module-level `app` in a file under
`api/` and serves it as an ASGI application — this file just puts the
vendored copy (web/api/_vendor/, see its README.md for why it's vendored
rather than imported from the repo root) on sys.path and re-exports the
real FastAPI app from server.main unchanged.

vercel.json rewrites /api/adapt and /api/adapt/:id to this one function
(not two), so the single FastAPI `app` can dispatch to its own /api/adapt
and /api/adapt/{result_id} routes internally, exactly as it does when run
locally via uvicorn — rewrites preserve the original request path, so
those route decorators still match.
"""
from __future__ import annotations

import sys
from pathlib import Path

_VENDOR_DIR = Path(__file__).parent / "_vendor"
if str(_VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(_VENDOR_DIR))

from server.main import app  # noqa: E402
