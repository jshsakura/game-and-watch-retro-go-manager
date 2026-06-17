"""SteamGridDB cover-art search endpoint (same shape as /api/igdb/search)."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..services import steamgriddb

router = APIRouter(prefix="/api", tags=["sgdb"])


@router.get("/sgdb/search")
async def sgdb_search(
    q: str = Query(..., min_length=1),
    system: str | None = Query(None),   # accepted for parity; SGDB isn't platform-filtered
    limit: int = Query(12, ge=1, le=20),
) -> dict:
    """Search SteamGridDB for box art by game name.

    Returns {available, results:[{name, year, cover_url, thumb_url}]} — the same
    shape as IGDB/TGDB search so the cover popup treats it as another source.
    """
    return await steamgriddb.search(q, limit)
