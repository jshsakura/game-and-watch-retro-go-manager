"""Rename a ROM's on-disk file (and its cover) as a set, updating the DB.
Shared by the single-rename endpoint and the bulk gamelist importer."""
from __future__ import annotations

from pathlib import Path

from . import covers, storage
from ..systems import get_system


def _free_name(target: Path) -> Path:
    """Avoid clobbering: 'Game.nes' → 'Game (2).nes' if taken."""
    if not target.exists():
        return target
    n = 2
    while True:
        cand = target.with_name(f"{target.stem} ({n}){target.suffix}")
        if not cand.exists():
            return cand
        n += 1


def rename_rom(conn, session_id: str, row: dict, new_name: str, *, suffix_on_clash: bool = False):
    """Move the rom file + its cover to `new_name` (extension included), update
    the DB row. Returns {stored_name, rom_path, cover_path}. Raises ValueError on
    a clash unless suffix_on_clash=True (then it appends ' (n)')."""
    new_name = storage.safe_name(new_name)
    dirname = get_system(row["system_key"]).dirname
    root = storage.session_root(session_id)

    old_rom = root / row["rom_path"]
    new_rom = storage.roms_dir(session_id, dirname) / new_name
    if new_rom != old_rom and new_rom.exists():
        if not suffix_on_clash:
            raise ValueError("같은 이름의 파일이 이미 있습니다")
        new_rom = _free_name(new_rom)
    new_name = new_rom.name

    new_rom.parent.mkdir(parents=True, exist_ok=True)
    if old_rom.exists():
        old_rom.rename(new_rom)
    rom_rel = storage.relative_to_session(session_id, new_rom)

    cover_rel = row.get("cover_path")
    if cover_rel:
        old_cover = root / cover_rel
        if old_cover.exists():
            new_cover = storage.covers_dir(session_id, dirname) / covers.cover_filename(new_name)
            new_cover.parent.mkdir(parents=True, exist_ok=True)
            old_cover.rename(new_cover)
            cover_rel = storage.relative_to_session(session_id, new_cover)

    # move the high-res web preview too (named by the rom stem) so it isn't orphaned
    old_prev = storage.previews_dir(session_id, dirname) / (Path(row["stored_name"]).stem + ".webp")
    if old_prev.exists():
        new_prev = storage.previews_dir(session_id, dirname) / (Path(new_name).stem + ".webp")
        new_prev.parent.mkdir(parents=True, exist_ok=True)
        old_prev.rename(new_prev)

    conn.execute(
        "UPDATE roms SET stored_name = ?, rom_path = ?, cover_path = ? WHERE id = ?",
        (new_name, rom_rel, cover_rel, row["id"]),
    )
    return {"stored_name": new_name, "rom_path": rom_rel, "cover_path": cover_rel}
