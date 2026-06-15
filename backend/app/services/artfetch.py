"""Download artwork bytes (screenshot/box art) for cover generation."""
from __future__ import annotations

import httpx

_TIMEOUT = httpx.Timeout(15.0)
_MAX_ART_BYTES = 8 * 1024 * 1024


async def fetch_image(url: str) -> bytes | None:
    """
    GET an image URL, returning its bytes or None on any failure (missing
    art, 404, network error). Never raises — a missing cover is not fatal.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.content
        if not data or len(data) > _MAX_ART_BYTES:
            return None
        return data
    except (httpx.HTTPError, OSError):
        return None
