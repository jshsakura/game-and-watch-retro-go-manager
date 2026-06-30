"""libretro-thumbnails boxart search — powers the in-popup cover 검색기.

Obscure systems (Game.com, Watara, Odyssey²…) have no usable IGDB/TheGamesDB
platform coverage, but libretro-thumbnails keeps clean per-platform box art. We
list a system's Named_Boxarts once (cached in-memory — the lists are static), then
fuzzy-match the query and return the same shape as the IGDB/TGDB endpoints.
"""
from __future__ import annotations

import re
from urllib.parse import quote

import httpx

from .metadata import _LIBRETRO_REPO, _RAW_BASE

# repo_slug -> [boxart filename, ...]  (static lists → cache for the process)
_LIST_CACHE: dict[str, list[str]] = {}
_TREE_API = "https://api.github.com/repos/libretro-thumbnails/{slug}/git/trees/master?recursive=1"
_BOXART_DIR = "Named_Boxarts/"


def _norm(s: str) -> str:
    """Title key for matching: drop extension + (..)/[..] tags, lowercase, collapse."""
    s = re.sub(r"\.[a-z0-9]+$", "", s, flags=re.I)
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", "", s)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


async def _boxart_files(slug: str) -> list[str]:
    """All Named_Boxarts/*.png basenames for a repo slug (cached). [] on failure."""
    if slug in _LIST_CACHE:
        return _LIST_CACHE[slug]
    names: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(
                _TREE_API.format(slug=slug),
                headers={"Accept": "application/vnd.github+json"},
            )
        if resp.status_code == 200:
            for node in resp.json().get("tree", []):
                path = node.get("path", "")
                if path.startswith(_BOXART_DIR) and path.lower().endswith(".png"):
                    names.append(path[len(_BOXART_DIR):])
    except (httpx.HTTPError, ValueError):
        return []
    if names:
        _LIST_CACHE[slug] = names
    return names


def _score(nq: str, qtokens: set[str], nf: str) -> int:
    """Match score between normalized query and a normalized filename (-1 = no match)."""
    if not nf:
        return -1
    if nf == nq:
        return 100
    if nq and (nf.startswith(nq) or nq.startswith(nf)):
        return 80
    if nq and nq in nf:
        return 60
    ftokens = set(nf.split())
    common = qtokens & ftokens
    if not common:
        return -1
    return 30 + 10 * len(common) - abs(len(ftokens) - len(qtokens))


async def search_covers(q: str, system: str | None, limit: int = 12) -> dict:
    """{available, results:[{name, year, cover_url, thumb_url}]}.
    available=False when the system has no libretro repo or the list can't be fetched."""
    repo = _LIBRETRO_REPO.get(system or "")
    if not repo:
        return {"available": False, "results": []}
    slug = repo.replace(" ", "_")
    files = await _boxart_files(slug)
    if not files:
        return {"available": False, "results": []}

    nq = _norm(q)
    qtokens = set(nq.split())
    scored = [(s, fn) for fn in files if (s := _score(nq, qtokens, _norm(fn))) >= 0]
    scored.sort(key=lambda sf: (-sf[0], len(sf[1])))

    results = []
    for _, fn in scored[:limit]:
        url = f"{_RAW_BASE}/{slug}/master/{_BOXART_DIR}{quote(fn)}"
        results.append({
            "name": re.sub(r"\.[^.]+$", "", fn),
            "year": None,
            "cover_url": url,
            "thumb_url": url,
        })
    return {"available": True, "results": results}
