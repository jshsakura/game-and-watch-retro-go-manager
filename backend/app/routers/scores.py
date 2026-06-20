"""IGDB rating backfill — score each ROM by its matched game's total_rating
(0-100) so a bloated set can be curated by quality. Stored on roms.igdb_score
(NULL = not fetched, -1 = fetched but no usable score, 0-100 = the score)."""
from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter

from .. import db
from ..services import igdb
from .sessions import require_session

router = APIRouter(prefix="/api", tags=["scores"])

_PAREN = re.compile(r"\(([^()]+)\)\.[a-z0-9]+$")

# IGDB allows ~4 req/s; pace just under that.
_RATE_PAUSE = 0.26


def _english_title(stored_name: str) -> str:
    """The English title from 'Korean (English).ext' (best for IGDB matching),
    falling back to the bare stem."""
    m = _PAREN.search(stored_name or "")
    if m:
        return m.group(1).strip()
    return (stored_name or "").rsplit(".", 1)[0].strip()


def _where(session_id: str, system: str | None, only_missing: bool) -> tuple[str, list]:
    clause = "session_id = ?"
    params: list = [session_id]
    if system:
        clause += " AND system_key = ?"
        params.append(system)
    if only_missing:
        clause += " AND igdb_score IS NULL"
    return clause, params


@router.post("/sessions/{session_id}/scores/backfill")
async def backfill_scores(
    session_id: str, system: str | None = None, limit: int = 60, refresh: bool = False
) -> dict:
    """Fetch IGDB ratings for up to `limit` ROMs (one system or all). By default
    only ROMs with no score yet (igdb_score IS NULL) are processed — pass
    refresh=1 to re-score everything. Returns {processed, rated, remaining} so the
    caller can loop until remaining hits 0."""
    with db.connect() as conn:
        require_session(conn, session_id)
    clause, params = _where(session_id, system, only_missing=not refresh)
    with db.connect() as conn:
        rows = [dict(r) for r in conn.execute(
            f"SELECT id, system_key, stored_name FROM roms WHERE {clause} "
            f"ORDER BY system_key, stored_name LIMIT ?", (*params, limit))]
        remaining = conn.execute(
            f"SELECT COUNT(*) c FROM roms WHERE {clause}", params).fetchone()["c"]

    processed = rated = 0
    for rom in rows:
        title = _english_title(rom["stored_name"])
        try:
            res = await igdb.fetch_rating(title, rom["system_key"])
        except Exception:
            res = None
        if res and res.get("score") is not None:
            score, votes = res["score"], res["votes"]
            rated += 1
        else:
            score, votes = -1, 0   # checked, no usable score (don't retry)
        with db.connect() as conn:
            conn.execute("UPDATE roms SET igdb_score = ?, igdb_votes = ? WHERE id = ?",
                         (score, votes, rom["id"]))
        processed += 1
        await asyncio.sleep(_RATE_PAUSE)

    return {"processed": processed, "rated": rated, "remaining": max(0, remaining - processed)}
