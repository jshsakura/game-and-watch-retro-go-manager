"""Fuzzy title matching to reject wrong auto-cover hits.

IGDB/TheGamesDB fuzzy-search returns *something* for almost any query, so a miss
comes back as an unrelated popular game (e.g. searching "R-Type" yields "Fire Pro
Wrestling"). We only accept a result whose returned title actually resembles the
query — otherwise that wrong cover gets stamped onto the ROM, and because the same
bad query repeats it ends up duplicated across many unrelated games.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

# Roman numerals → digits so "Final Fight II" matches "Final Fight 2".
_ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6",
          "vii": "7", "viii": "8", "ix": "9", "x": "10"}
# Low-signal words that shouldn't drive a match on their own.
_STOP = {"the", "a", "an", "of", "no", "to", "and", "de", "le", "la"}
# No-Intro region/dump tags — never a real title on their own; a query that is
# only one of these must not match (e.g. "Japan" should not hit "…All Japan…").
_REGION = {"japan", "usa", "world", "europe", "korea", "asia", "france",
           "germany", "spain", "italy", "netherlands", "sweden", "australia",
           "brazil", "china", "taiwan", "unl", "proto", "beta", "sample",
           "demo", "pd", "rev", "en", "jp", "us", "eu", "ko"}

DEFAULT_THRESHOLD = 0.62


def normalize(s: str) -> str:
    """Lowercase, drop bracketed tags, reduce punctuation to spaces. Non-latin
    scripts (한글/かな) collapse away, leaving only the comparable latin tokens."""
    s = (s or "").lower()
    s = re.sub(r"[\(\[].*?[\)\]]", " ", s)     # (Japan), [!], (USA, Europe)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _tokens(s: str) -> set[str]:
    toks = [_ROMAN.get(t, t) for t in normalize(s).split()]
    return {t for t in toks if t not in _STOP}


def score(a: str, b: str) -> float:
    """0..1 similarity between two titles. Combines token-set overlap (Jaccard),
    char-level ratio, and a containment bonus (one title fully inside the other,
    e.g. "Shinobi" within "GG Shinobi")."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    # A query that is just a region/dump tag carries no title signal — refuse it
    # outright so it can't latch onto any game that happens to contain the word.
    if na in _REGION or nb in _REGION:
        return 0.0
    ta, tb = _tokens(a), _tokens(b)
    # Sequel guard: differing series numbers mean different games ("Rockman 2" is
    # not "Rockman"). A lone "1" vs none is tolerated (Final Fight == Final Fight 1).
    nums_a = {t for t in ta if t.isdigit()}
    nums_b = {t for t in tb if t.isdigit()}
    diff = nums_a ^ nums_b
    if diff and diff != {"1"}:
        return 0.4   # capped below threshold → rejected, never a wrong sequel cover
    jacc = len(ta & tb) / len(ta | tb) if (ta or tb) else 0.0
    ratio = SequenceMatcher(None, na, nb).ratio()
    contain = 0.9 if (na in nb or nb in na) else 0.0
    return max(jacc, ratio, contain)


def matches(query: str, candidate: str, threshold: float = DEFAULT_THRESHOLD) -> bool:
    return score(query, candidate) >= threshold


def best(query: str, candidates: list[tuple[str, str]],
         threshold: float = DEFAULT_THRESHOLD) -> tuple[str, str] | None:
    """From [(title, payload)] pick the (title, payload) whose title best matches
    ``query`` and clears ``threshold``. Returns None if nothing is close enough."""
    ranked = sorted(((score(query, title), title, payload)
                     for title, payload in candidates), key=lambda x: x[0], reverse=True)
    if ranked and ranked[0][0] >= threshold:
        _, title, payload = ranked[0]
        return title, payload
    return None
