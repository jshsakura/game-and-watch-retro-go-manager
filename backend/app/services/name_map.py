"""Canonical ROM name map, keyed by file HASH so renames stay robust/idempotent
even when filenames differ or duplicate. Built from the per-system gamelists the
user dropped in DATA. One JSON artifact: data/name_map.json.

  { "<sha256>": {system, filename, korean_name|null, cover_ref|null} }
"""
from __future__ import annotations

import hashlib
import json

from .. import config
from . import gamelist, storage

MAP_PATH = config.DATA_DIR / "name_map.json"


def hash_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_index(session_id: str) -> dict[str, dict[str, str]]:
    """system_key -> {english_key -> korean_name}, from every gamelist*.xml in the
    bundled Korean-name seed plus the session scratch (see gamelist.gamelist_xmls)."""
    index: dict[str, dict[str, str]] = {}
    for xml in gamelist.gamelist_xmls(session_id):
        games = gamelist.parse_games(xml)
        sysk = gamelist.system_from_filename(xml.name) or gamelist.infer_system(games)
        if not sysk:
            continue
        bucket = index.setdefault(sysk, {})
        for g in games:
            for key in gamelist._gamelist_keys(g["name"], g.get("path", "")):
                bucket.setdefault(key, g["name"])
    return index


def build(conn, session_id: str) -> dict:
    """Hash every library rom, resolve its Korean name from the gamelists, and
    write the map. Returns stats {total, matched, systems, path}."""
    index = build_index(session_id)
    root = storage.session_root(session_id)
    rows = conn.execute(
        "SELECT id, system_key, stored_name, rom_path FROM roms WHERE session_id = ?",
        (session_id,),
    ).fetchall()

    out: dict[str, dict] = {}
    matched = 0
    per_system: dict[str, dict[str, int]] = {}
    for r in rows:
        path = root / r["rom_path"]
        if not path.exists():
            continue
        sysk = r["system_key"]
        key = gamelist._english_key(r["stored_name"].rsplit(".", 1)[0])
        korean = index.get(sysk, {}).get(key)
        out[hash_file(path)] = {
            "system": sysk,
            "filename": r["stored_name"],
            "korean_name": korean,
            "cover_ref": None,
        }
        stat = per_system.setdefault(sysk, {"total": 0, "matched": 0})
        stat["total"] += 1
        if korean:
            stat["matched"] += 1
            matched += 1

    MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    MAP_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"total": len(out), "matched": matched, "systems": per_system, "path": str(MAP_PATH)}


def load() -> dict:
    if not MAP_PATH.exists():
        return {}
    try:
        return json.loads(MAP_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
