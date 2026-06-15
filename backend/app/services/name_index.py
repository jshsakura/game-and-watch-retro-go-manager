"""Persistent hash → resolved-name cache (rom_names table). Lets uploads of an
already-seen file skip 꿀렁 matching entirely, and keeps the dictionary even when
the source archives are removed from DATA."""
from __future__ import annotations

import hashlib

from . import storage


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lookup(conn, file_hash: str) -> str | None:
    row = conn.execute(
        "SELECT korean_name FROM rom_names WHERE hash = ?", (file_hash,)
    ).fetchone()
    return row["korean_name"] if row else None


def lookup_by_name(conn, system_key: str, original_name: str, lang: str = "ko") -> str | None:
    """Resolve by (system, original filename) when the content hash misses — e.g.
    a re-uploaded or differently-dumped copy of a game we've already named."""
    if not original_name:
        return None
    row = conn.execute(
        """SELECT korean_name FROM rom_names
           WHERE system_key = ? AND original_name = ? AND lang = ?
             AND korean_name IS NOT NULL
           LIMIT 1""",
        (system_key, storage.nfc(original_name), lang),
    ).fetchone()
    return row["korean_name"] if row else None


def store(conn, file_hash: str, system_key: str, name: str,
          source: str | None = None, original_name: str | None = None) -> None:
    """Persist hash → resolved name, plus (system, original filename) so the map
    is reusable by both content and name. NFC-clean for a stable cache key."""
    conn.execute(
        """INSERT OR REPLACE INTO rom_names
               (hash, system_key, korean_name, source, original_name)
           VALUES (?, ?, ?, ?, ?)""",
        (file_hash, system_key, storage.nfc(name), source,
         storage.nfc(original_name) if original_name else None),
    )
