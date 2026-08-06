"""Storage for computed adaptation results.

Two backends, chosen by whether DATABASE_URL is set:

- No DATABASE_URL (local dev, the test suite, the CLI): falls back to a
  JSON file per id under server/.cache, exactly as before. Nobody should
  need Postgres running just to `uvicorn server.main:app --reload`.
- DATABASE_URL set (Railway): results live in the `cached_results` table
  (server/db_models.py::CachedResult) so they survive redeploys without
  needing a volume, and so results are visible to find_similar's
  cross-user reuse below.

Exact matching (content_id/normalize_text) is unchanged from before: it
hashes lightly-normalized text (whitespace collapsed, blank lines
dropped) into an id, and that id doubles as the /s/<id> share-URL slug.

find_similar is new: it catches near-identical pastes of the same song
(a typo, reflowed line breaks, stray punctuation) that would miss the
exact hash and needlessly re-run the engine on what is, for all
practical purposes, the same request. It compares a much more aggressive
normalization (case-folded, punctuation stripped) via difflib's
SequenceMatcher, and only reports a match above a conservative
similarity threshold - a false cache hit here would serve one song's
adaptation for a different song, which is a correctness bug, not just a
wasted cache lookup, so this deliberately errs toward re-running the
engine when in doubt rather than guessing. It's also a plain O(n) scan
over stored results, not a database extension (no pg_trgm dependency) -
fine at today's scale, worth revisiting if the result set ever grows
large enough to make a full scan slow.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import re
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent / ".cache"

_WHITESPACE_RE = re.compile(r"[ \t]+")
_FUZZY_STRIP_RE = re.compile(r"[^\w\s]", re.UNICODE)
_FUZZY_WHITESPACE_RE = re.compile(r"\s+", re.UNICODE)

SIMILARITY_THRESHOLD = 0.92

# Bump this whenever a prompt or pipeline change would make previously
# cached output stale (wrong "why" copy, a fixed bug, a corrected
# heuristic) - server/mapping.py's _WHY_SYSTEM rewrite is what exposed
# the need for this: three real songs kept showing pre-fix output
# indefinitely, because nothing ever told the cache the logic underneath
# it had changed. Folded into content_id() below, so bumping it makes
# every future request for already-cached text miss the cache and
# regenerate, rather than needing a manual per-song cache clear.
#
# Deliberately NOT bumped retroactively for every past change (that
# would be pure busywork with no real value) - only from here forward,
# starting now.
CACHE_VERSION = "8"


def normalize_text(text: str) -> str:
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.strip().splitlines()]
    return "\n".join(line for line in lines if line)


def content_id(
    text: str, target_language: str = "English", source_language: str = "unspecified"
) -> str:
    """The same source text adapted into two different target languages -
    or claimed as two different source languages, now that direct pairs
    like Hindi -> Korean exist - is two different results, not one. Both
    "English" and "unspecified" (every id from before either field existed)
    are deliberately left out of the hash input so every already-computed
    result and already-shared /s/<id> link keeps resolving to the exact
    same id it always has; only a non-default value folds into the hash,
    since no such id existed before that value was possible.
    """
    normalized = normalize_text(text)
    key = normalized
    if target_language != "English":
        key = f"{target_language}::{key}"
    if source_language != "unspecified":
        key = f"{source_language}::{key}"
    # Unlike target_language/source_language above, this always folds in -
    # there's no "default" version to stay silently compatible with, and
    # every id computed before CACHE_VERSION existed still resolves fine
    # by direct lookup (get() reads by literal id; only a fresh POST for
    # the same text computes a new, version-tagged id and misses the old
    # cached row). See CACHE_VERSION's comment for why this exists.
    key = f"{CACHE_VERSION}::{key}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def comics_content_id(
    panel_texts: list[str], target_language: str, source_language: str
) -> str:
    """Same storage (get()/set() below) and same content-addressing idea
    as content_id(), for a whole chapter's worth of panels rather than one
    song's text - this is what gives a comics chapter a real, persistent,
    shareable id for the first time (see server/main.py's
    comics_adapt_endpoint and the future /comics/s/<id> share page).

    Always folds a literal "comics" tag into the hash (unlike
    content_id()'s conditional folding for back-compat with pre-existing
    ids) - there's no prior comics id space to stay compatible with, and
    this guarantees a comics chapter's id can never collide with a song's
    even in the freak case both happened to normalize to the same text,
    since they're stored in the same flat get()/set() id space below.
    Order matters (panel_texts must already be in reading order) - two
    chapters with the same panels in a different order are, correctly,
    different results.
    """
    normalized = "\n\n".join(normalize_text(t) for t in panel_texts)
    key = f"comics::{source_language}::{target_language}::{CACHE_VERSION}::{normalized}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def comics_redraw_content_id(
    image_bytes: bytes, regions: list[dict], default_font: str | None = None
) -> str:
    """Same storage (get()/set() below) and same content-addressing idea as
    content_id()/comics_content_id(), for a single redraw request - this is
    what lets /api/comics/redraw skip re-running the expensive inpainting
    pipeline (OpenCV or LaMa - engine/comics_redraw.py) for a request it's
    already computed, instead of doing that work over on every page reload
    or retry, and gives a redrawn panel a real id to fetch by, the same way
    a song or chapter already has one.

    Hashes the raw image bytes directly (not a lighter-weight perceptual
    hash) plus each region's bbox, adapted_text, and font, in the order
    given - deliberately exact rather than fuzzy, unlike find_similar()'s
    text matching: a false cache hit here would silently return a
    different image's redraw, which is a correctness bug, not just a
    wasted lookup. `default_font`/a region's own `font` MUST fold into
    this hash - otherwise re-requesting the exact same (image, regions)
    with only the font changed would silently serve back the OLD font's
    already-cached image, which is exactly as wrong as serving a
    different image entirely; the caller asked for a real re-render and
    would get a stale one. Image bytes are already bounded by
    MAX_IMAGE_BYTES before this is ever called, so hashing the full
    payload is cheap in practice.
    """
    hasher = hashlib.sha256()
    hasher.update(b"comics_redraw::")
    hasher.update(image_bytes)
    hasher.update(f"::default_font={default_font or ''}".encode("utf-8"))
    for region in regions:
        bbox = region["bbox"]
        font = region.get("font") or ""
        hasher.update(
            f"::{bbox['x']},{bbox['y']},{bbox['width']},{bbox['height']}"
            f"::{region['adapted_text']}::font={font}".encode("utf-8")
        )
    return hasher.hexdigest()[:16]


def fuzzy_key(text: str) -> str:
    """Case-folded, punctuation-stripped, whitespace-collapsed — deliberately
    more aggressive than normalize_text, since this is for *comparing*
    near-duplicates, not for generating a stable id."""
    stripped = _FUZZY_STRIP_RE.sub(" ", text.lower())
    return _FUZZY_WHITESPACE_RE.sub(" ", stripped).strip()


def _use_db() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def get(result_id: str) -> dict | None:
    if _use_db():
        from . import db
        from .db_models import CachedResult

        with db.session_scope() as session:
            row = session.get(CachedResult, result_id)
            return row.result_json if row else None

    path = CACHE_DIR / f"{result_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def set(
    result_id: str,
    result: dict,
    source_text: str | None = None,
    target_language: str = "English",
    source_language: str = "unspecified",
) -> None:
    if _use_db():
        from . import db
        from .db_models import CachedResult

        key = fuzzy_key(source_text) if source_text is not None else ""
        with db.session_scope() as session:
            row = session.get(CachedResult, result_id)
            if row is None:
                session.add(
                    CachedResult(
                        id=result_id,
                        normalized_text=key,
                        target_language=target_language,
                        source_language=source_language,
                        result_json=result,
                        cache_version=CACHE_VERSION,
                    )
                )
            else:
                row.result_json = result
                row.target_language = target_language
                row.source_language = source_language
                row.cache_version = CACHE_VERSION
                if source_text is not None:
                    row.normalized_text = key
            session.commit()
        return

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{result_id}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))


def find_similar(
    text: str,
    target_language: str = "English",
    source_language: str = "unspecified",
    threshold: float = SIMILARITY_THRESHOLD,
) -> tuple[str, dict, float] | None:
    """Only checks the database backend — cross-user reuse is the whole
    point, and there's exactly one user (whoever is running it) in the
    file-based local/test path, where an exact hash already covers every
    real repeat.

    Only ever matches rows asked for in the same target_language AND
    source_language — an English source adapted into Hindi and a Korean
    source adapted into Hindi can have near-identical normalized_text
    (the fuzzy key only looks at the source side today) while being
    entirely different, non-interchangeable results.

    Also only matches rows computed under the CURRENT CACHE_VERSION.
    Unlike content_id()'s exact-hash path (where a version bump naturally
    misses old rows because the id itself changed), this scans stored
    text directly, so it would otherwise keep resurfacing a pre-bump row
    for a near-identical resubmission forever, defeating the whole point
    of bumping CACHE_VERSION in the first place.

    Scans in two passes rather than one to avoid a real scaling problem:
    loading the full ORM row (including result_json - every section,
    candidate, and ruling this song ever computed) for every candidate
    row just to compare its normalized_text is memory/bandwidth that
    grows linearly with the size of the whole cache table, on every
    single cache-miss request, when only the eventual winner's full
    payload is ever actually needed. The first pass fetches only
    (id, normalized_text) for the scan; the second pass fetches the one
    winning row's full result_json, if there is one.

    A second, real scaling problem this used to have entirely unguarded:
    difflib.SequenceMatcher.ratio() is expensive (worse than linear in
    the length of the two strings being compared), and this ran it
    against every single candidate row for the language pair, however
    long the submitted song and however large the cache had grown - a
    long song (the case this exists to help, since that's the run most
    worth not repeating) against a cache with any real history could
    make a single cache-miss request take minutes before it even
    reached the point of starting the actual engine job, which read
    from the frontend as a plain hang, not a slow adaptation.

    Fixed with an exact, not approximate, pre-filter: ratio() is defined
    as 2*M / (len(a) + len(b)) where M <= min(len(a), len(b)), so the
    highest ratio two strings of a given length pair could ever produce
    is 2*min/(min+max). Below `threshold`, no comparison is worth
    running at all - skipping it can never discard a real match, only
    candidates that were mathematically incapable of reaching the bar.
    """
    if not _use_db():
        return None

    from . import db
    from .db_models import CachedResult

    key = fuzzy_key(text)
    if not key:
        return None

    key_len = len(key)
    # threshold <= 2*min/(min+max)  =>  min/max >= threshold/(2-threshold)
    min_length_ratio = threshold / (2 - threshold)

    with db.session_scope() as session:
        candidates = (
            session.query(CachedResult.id, CachedResult.normalized_text)
            .filter_by(
                target_language=target_language,
                source_language=source_language,
                cache_version=CACHE_VERSION,
            )
            .all()
        )

        best_id: str | None = None
        best_ratio = 0.0
        for row_id, normalized_text in candidates:
            if not normalized_text:
                continue
            candidate_len = len(normalized_text)
            shorter_len = key_len if key_len <= candidate_len else candidate_len
            longer_len = candidate_len if key_len <= candidate_len else key_len
            if shorter_len / longer_len < min_length_ratio:
                continue
            ratio = difflib.SequenceMatcher(None, key, normalized_text).ratio()
            if ratio >= threshold and ratio > best_ratio:
                best_id, best_ratio = row_id, ratio

        if best_id is None:
            return None

        winner = session.get(CachedResult, best_id)
        if winner is None:
            # Deleted between the scan above and this lookup - vanishingly
            # unlikely (nothing in this codebase deletes cached_results
            # rows today), but a real cache miss is the correct fallback,
            # not a crash.
            return None
        return best_id, winner.result_json, best_ratio
