"""SteamGridDB box-art search (async).

Returns the SAME shape as igdb/tgdb ``search_covers`` so the cover-search popup can
offer it as another source — useful when TheGamesDB's monthly quota is exhausted.
SteamGridDB has broad community-curated box art coverage.

Flow: /search/autocomplete/{title} → game id(s) → /grids/game/{id} → box-art URLs.
Returns {available, results:[{name, year, cover_url, thumb_url}]}.
"""
from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from .. import config

log = logging.getLogger(__name__)

_BASE = "https://www.steamgriddb.com/api/v2"
_TOP_GAMES = 3   # fetch grids from up to this many top matches to fill the grid


def available() -> bool:
    return bool(config.STEAMGRIDDB_API_KEY)


async def search(query: str, limit: int = 12) -> dict:
    """Box-art candidates for a free-text game title (best-match order)."""
    query = (query or "").strip()
    if not query:
        return {"available": available(), "results": []}
    if not available():
        return {"available": False, "results": []}

    headers = {"Authorization": f"Bearer {config.STEAMGRIDDB_API_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            sr = await client.get(f"{_BASE}/search/autocomplete/{quote(query, safe='')}")
            if sr.status_code == 401:
                return {"available": False, "results": [], "error": "SteamGridDB 키가 올바르지 않습니다"}
            if sr.status_code != 200:
                return {"available": True, "results": [], "error": sr.text[:160]}
            games = (sr.json() or {}).get("data") or []
            if not games:
                return {"available": True, "results": []}

            results: list[dict] = []
            for game in games[:_TOP_GAMES]:
                gid, gname = game.get("id"), game.get("name")
                if not gid:
                    continue
                gr = await client.get(
                    f"{_BASE}/grids/game/{gid}",
                    params={"types": "static", "nsfw": "false", "humor": "false"},
                )
                if gr.status_code != 200:
                    continue
                for grid in (gr.json() or {}).get("data") or []:
                    url = grid.get("url")
                    if not url:
                        continue
                    results.append({
                        "name": gname,
                        "year": None,
                        "cover_url": url,
                        "thumb_url": grid.get("thumb") or url,
                    })
                    if len(results) >= limit:
                        return {"available": True, "results": results}
            return {"available": True, "results": results}
    except httpx.HTTPError as exc:
        log.info("SteamGridDB request failed for %r: %s", query, exc)
        return {"available": True, "results": [], "error": "SteamGridDB 요청 실패"}
