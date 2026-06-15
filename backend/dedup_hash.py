"""Backfill content_hash for every rom, then collapse EXACT-duplicate groups
(same bytes, same system) down to ONE entry — keeping the best (Korean-named >
has-cover > shortest name). Losers' files move to _trash (recoverable). Manual
naming is unaffected; this only removes byte-identical dupes."""
from collections import defaultdict
from pathlib import Path
from app import db
from app.services import name_index, storage

SESSION = "public"
root = storage.session_root(SESSION)


def backfill():
    with db.connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, rom_path, content_hash FROM roms WHERE session_id=?", (SESSION,)).fetchall()]
    n = 0
    for r in rows:
        if r["content_hash"]:
            continue
        p = root / r["rom_path"]
        if not p.exists():
            continue
        h = name_index.hash_bytes(p.read_bytes())
        with db.connect() as conn:
            conn.execute("UPDATE roms SET content_hash=? WHERE id=?", (h, r["id"]))
        n += 1
    print(f"backfilled hashes: {n}")


def _has_hangul(s):
    return any("가" <= ch <= "힣" for ch in (s or ""))


def score(r):
    # higher = keep. korean name >> cover ok >> shorter name
    return (2 if _has_hangul(r["stored_name"]) else 0) + (1 if r["cover_status"] == "ok" else 0)


def dedup():
    with db.connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT id, system_key, stored_name, rom_path, cover_path, cover_status, content_hash "
            "FROM roms WHERE session_id=? AND content_hash IS NOT NULL", (SESSION,)).fetchall()]
    groups = defaultdict(list)
    for r in rows:
        groups[(r["system_key"], r["content_hash"])].append(r)
    removed = 0
    for key, grp in groups.items():
        if len(grp) < 2:
            continue
        grp.sort(key=lambda r: (score(r), -len(r["stored_name"])), reverse=True)
        keep, losers = grp[0], grp[1:]
        print(f"\nDUP {key[0]} x{len(grp)} → keep: {keep['stored_name']}")
        for L in losers:
            print(f"   trash: {L['stored_name']}")
            storage.move_to_trash(SESSION, L["rom_path"])
            if L["cover_path"]:
                storage.move_to_trash(SESSION, L["cover_path"])
            with db.connect() as conn:
                conn.execute("DELETE FROM roms WHERE id=?", (L["id"],))
            removed += 1
    print(f"\nDONE removed dupes: {removed}")


if __name__ == "__main__":
    backfill()
    dedup()
