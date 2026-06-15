"""Parse the REGION tag out of a ROM filename so it can live in its own DB column
and be removed from the on-device display name — the title only needs the game
name, not '(Japan)' / '(USA, Europe, Brazil)'.

Strictly region-only: a parenth…group counts as a region tag ONLY when EVERY
comma-separated token inside it is a known region word. This deliberately leaves
alone:
  - English-title parens   '볼 (Ball)'            (Ball is a title, not a region)
  - publisher / hardware    '(VTech, Time & Fun)' '(Nintendo, Wide Screen)'
  - years                   '(1983)'  '(1982-84)'
  - dump flags              '(Unl)' '(Rev 1)' '(Prototype)' '(!)'
so the title's real disambiguators (especially Game & Watch publisher tags) and
genuine name parts are never destroyed.

Pure + immutable: functions return new strings/tuples and never mutate input.
"""
from __future__ import annotations

import re

# No-Intro style region words (lowercased). A tag is "region" iff every
# comma-separated token is in here.
REGION_WORDS = {
    "japan", "usa", "europe", "world", "korea", "taiwan", "china", "asia",
    "brazil", "france", "germany", "spain", "italy", "netherlands", "sweden",
    "australia", "canada", "uk", "hong kong", "russia", "denmark", "finland",
    "norway", "portugal", "greece", "belgium", "switzerland", "austria",
    "poland", "ireland", "new zealand", "mexico", "scandinavia", "latin america",
    "uae", "israel", "south africa", "japan, usa",
}

_PAREN = re.compile(r"\s*[(\[]([^)\]]*)[)\]]")


def _is_region(content: str) -> bool:
    tokens = [t.strip().lower() for t in content.split(",")]
    return bool(tokens) and all(t in REGION_WORDS for t in tokens if t)


def extract_region(name: str) -> tuple[str | None, str]:
    """Split a filename (or stem) into (region, cleaned_name). `region` is the
    content of the region tag(s) joined by ', '; cleaned_name has those tags (and
    only those) removed. Non-region parens are preserved verbatim.

    'Antarctic Adventure (Japan)'     -> ('Japan', 'Antarctic Adventure')
    'Sonic (USA, Europe, Brazil)'     -> ('USA, Europe, Brazil', 'Sonic')
    '볼 (Ball)'                        -> (None, '볼 (Ball)')
    'Baseball (VTech, Time & Fun)'    -> (None, 'Baseball (VTech, Time & Fun)')
    """
    regions: list[str] = []

    def _repl(m: re.Match) -> str:
        content = m.group(1).strip()
        if _is_region(content):
            regions.append(content)
            return ""          # drop this tag from the name
        return m.group(0)      # keep non-region tag exactly as-is

    cleaned = _PAREN.sub(_repl, name)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    region = ", ".join(regions) if regions else None
    return region, cleaned


def region_of(*names: str) -> str | None:
    """Region from the first variant that has one (e.g. original_name then
    stored_name) — original_name keeps the tag even after a Korean rename."""
    for n in names:
        region, _ = extract_region(n or "")
        if region:
            return region
    return None
