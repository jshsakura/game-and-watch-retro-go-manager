"""PICO-8 cart compatibility on the Game & Watch z8lua engine.

Status comes from the community compatibility sheet, bundled as
assets/pico8_compat.json ({normalized_key: {"status", "note"}}). The G&W engine
targets PICO-8 0.2.7, so the real limit is RAM (out-of-memory), not the API
version — hence this curated list rather than a static heuristic.

  lookup(name) -> 'good' | 'partial' | 'broken' | None   (None = untested)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "assets" / "pico8_compat.json"
_COMPAT: dict | None = None


def _load() -> dict:
    global _COMPAT
    if _COMPAT is None:
        try:
            _COMPAT = json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            _COMPAT = {}
    return _COMPAT


def _norm(s: str) -> str:
    """Match the key form used when the JSON was built: drop extension + trailing
    -N version suffix + leading the/a, keep alphanumerics only, lowercased."""
    s = re.sub(r"\.p8(\.png)?$", "", s or "", flags=re.I)
    s = re.sub(r"[-_]\d+$", "", s)
    s = re.sub(r"\b(the|a)\b", "", s.lower())
    return re.sub(r"[^a-z0-9]", "", s)


def lookup(name: str) -> str | None:
    """Known runnability for a PICO-8 cart by its title/filename. None = untested."""
    entry = _load().get(_norm(name))
    return entry["status"] if entry else None
