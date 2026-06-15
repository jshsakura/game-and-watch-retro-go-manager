"""IGDB cover search endpoint — powers the in-popup cover 검색기."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..services import igdb

router = APIRouter(prefix="/api", tags=["igdb"])


@router.get("/igdb/search")
async def igdb_search(
    q: str = Query(..., min_length=1),
    system: str | None = Query(None),
    limit: int = Query(12, ge=1, le=20),
) -> dict:
    """Search IGDB for cover art by game name, optionally pinned to a system."""
    return await igdb.search_covers(q, system, limit)
