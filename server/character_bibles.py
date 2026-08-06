"""Persistent, cross-chapter character voice memory for comics series.

Real gap this closes: engine/comics_adapt.py's Chapter DNA re-derives
every character's voice_description/honorific_register/relationships
from scratch on every single chapter, with nothing carrying forward - a
character's established slang or speech register from chapter 1 has no
memory in chapter 2. This module is the persistence half of the fix;
engine/comics_adapt.py's merge_character_bible (reads, before a chapter
runs) and character_bible_updates (writes, after one finishes) are the
other half.

Same degrade-to-no-op convention as server/accounts.py: everything here
is a no-op/empty result when DATABASE_URL is unset, and everything
requires a real, signed-in user_id - a persisted bible needs an owner,
so there is no anonymous variant of this feature (a deliberate scope
decision, not an oversight).

Series identity is a free-text name the caller supplies, matched
case-insensitively after stripping whitespace - there is no dedicated
"series" entity anywhere else in this product, so this is intentionally
the simplest thing that actually works rather than a speculative schema
for a concept nothing else here has yet.
"""
from __future__ import annotations


def _use_db() -> bool:
    import os

    return bool(os.environ.get("DATABASE_URL"))


def _key(value: str) -> str:
    return value.strip().lower()


def get_bible(user_id: str, series_name: str) -> dict[str, dict]:
    """Every character this user has recorded for this series so far,
    keyed by the same lowercased/stripped name merge_character_bible
    matches against. {} when no database is configured, the series is
    new, or series_name is blank - all three are "nothing to merge in",
    not errors.
    """
    if not _use_db() or not series_name.strip():
        return {}

    import uuid as _uuid

    from . import db
    from .db_models import CharacterBibleEntry

    with db.session_scope() as session:
        rows = (
            session.query(CharacterBibleEntry)
            .filter_by(user_id=_uuid.UUID(user_id), series_name_key=_key(series_name))
            .all()
        )
        return {
            row.character_name_key: {
                "voice_description": row.voice_description,
                "honorific_register": row.honorific_register,
                "relationships": list(row.relationships or []),
            }
            for row in rows
        }


def save_bible(user_id: str, series_name: str, updates: dict[str, dict]) -> None:
    """Upserts one row per character in `updates` (keyed by lowercased
    name, engine/comics_adapt.py::character_bible_updates' own return
    shape) - insert a character never seen before in this series, or
    overwrite an existing one with this chapter's final state. No-op
    when no database is configured, series_name is blank, or updates is
    empty (a chapter with zero attributed characters has nothing worth
    persisting).
    """
    if not _use_db() or not series_name.strip() or not updates:
        return

    import uuid as _uuid

    from . import db
    from .db_models import CharacterBibleEntry

    with db.session_scope() as session:
        uid = _uuid.UUID(user_id)
        series_key = _key(series_name)
        existing = {
            row.character_name_key: row
            for row in session.query(CharacterBibleEntry)
            .filter_by(user_id=uid, series_name_key=series_key)
            .all()
        }
        for character_key, entry in updates.items():
            row = existing.get(character_key)
            if row is None:
                session.add(
                    CharacterBibleEntry(
                        user_id=uid,
                        series_name=series_name,
                        series_name_key=series_key,
                        character_name=entry["name"],
                        character_name_key=character_key,
                        voice_description=entry.get("voice_description") or "",
                        honorific_register=entry.get("honorific_register") or "",
                        relationships=entry.get("relationships") or [],
                    )
                )
            else:
                row.character_name = entry["name"]
                row.voice_description = entry.get("voice_description") or ""
                row.honorific_register = entry.get("honorific_register") or ""
                row.relationships = entry.get("relationships") or []
        session.commit()
