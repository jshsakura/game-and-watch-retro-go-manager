"""libretro-thumbnails boxart search endpoint — powers the in-popup cover 검색기.

Returns the same shape as /api/igdb/search so the popup can treat it as another
source: {available, results:[{name, year, cover_url, thumb_url}]}.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..services import libretro

router = APIRouter(prefix="/api", tags=["libretro"])


@router.get("/libretro/search")
async def libretro_search(
    q: str = Query(..., min_length=1),
    system: str | None = Query(None),
    limit: int = Query(12, ge=1, le=20),
) -> dict:
    """Search libretro-thumbnails box art by game name, pinned to a system."""
    return await libretro.search_covers(q, system, limit)
