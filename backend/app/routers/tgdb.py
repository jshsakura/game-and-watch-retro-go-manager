"""TheGamesDB cover search endpoint — powers the in-popup cover 검색기."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..services import tgdb

router = APIRouter(prefix="/api", tags=["tgdb"])


@router.get("/tgdb/search")
async def tgdb_search(
    q: str = Query(..., min_length=1),
    system: str | None = Query(None),
    limit: int = Query(12, ge=1, le=20),
) -> dict:
    """Search TheGamesDB for cover art by game name, optionally pinned to a system.

    Returns the same shape as /api/igdb/search, plus `quota_exceeded` so the UI can
    distinguish "monthly allowance used up" (HTTP 429) from a genuine no-match:
    {available, results:[{name, year, cover_url, thumb_url}], quota_exceeded}
    """
    query = (q or "").strip()
    if not query:
        return {"available": tgdb.available(), "results": [], "quota_exceeded": False}

    if not tgdb.available():
        return {"available": False, "results": [], "quota_exceeded": False}

    found = await tgdb.search(query, system or "")
    results = [
        {
            "name": title,
            "year": None,
            "cover_url": url,
            "thumb_url": url,
        }
        for title, url in found["candidates"][:limit]
    ]
    return {"available": True, "results": results, "quota_exceeded": found["quota_exceeded"]}
