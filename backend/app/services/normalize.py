"""Plan the normalization of a rom's on-device name:
  1. strip the region tag out of the display name (it lives in the `region` col),
  2. if the name has no Korean title, fill one from the blog (tistory).

plan_rom is PURE — it takes a `resolver` callable (system, stored) -> match|None
so it can be unit-tested without network. The router/runner applies the plan via
the existing renames.rename_rom (which moves the rom + cover + preview together).
"""
from __future__ import annotations

import re

from . import gamelist, romtag, storage

NO_KOREAN_SYSTEMS = {"homebrew", "pico8"}   # indie carts: no Korean release
_HANGUL = re.compile(r"[가-힣]")


def needs_korean(stored_name: str, system_key: str) -> bool:
    """True when this rom should get a Korean title: not an excluded system, no
    Hangul yet, and the name has a real translatable word (2+ letters incl. a
    lowercase one) — so '1942', 'NBA', 'Z.O.E' are skipped."""
    if system_key in NO_KOREAN_SYSTEMS:
        return False
    stem = stored_name.rsplit(".", 1)[0] if "." in stored_name else stored_name
    if _HANGUL.search(stem):
        return False
    return any(len(w) >= 2 and re.search(r"[a-z]", w) for w in re.findall(r"[A-Za-z]+", stem))


def plan_rom(system_key: str, stored_name: str, resolver) -> dict:
    """Return the proposed change for one rom (pure):
      {region, new_stored, changed, korean, confidence}
    `resolver(system, stored) -> {korean, confidence, url}|None` supplies the blog
    match; pass a no-op resolver to do region-strip only."""
    ext = stored_name.rsplit(".", 1)[-1] if "." in stored_name else ""
    region, cleaned = romtag.extract_region(stored_name)
    eng_title = cleaned.rsplit(".", 1)[0] if "." in cleaned else cleaned

    korean = None
    confidence = None
    new_base = eng_title
    if needs_korean(stored_name, system_key):
        match = resolver(system_key, stored_name)
        if match and match.get("korean"):
            korean = match["korean"]
            confidence = match.get("confidence")
            new_base = gamelist.compose_name(korean, eng_title)

    new_stored = storage.safe_name(new_base) + (f".{ext}" if ext else "")
    return {
        "region": region,
        "new_stored": new_stored,
        "changed": new_stored != stored_name,
        "korean": korean,
        "confidence": confidence,
    }
