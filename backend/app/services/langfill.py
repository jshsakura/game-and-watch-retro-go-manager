"""One-time backfill of derived metadata (language / Korean-patch, region) for
EXISTING library roms. New uploads already set these at insert time, so we only
touch legacy rows that were never classified — making each pass idempotent and
safe to run on every startup. Writes ONLY metadata columns; filenames, covers
and files are never changed."""
from __future__ import annotations

from . import langtag, romtag


def backfill(conn) -> int:
    """Fill orig_lang/play_lang/is_korean_patched for rows that have never been
    classified (lang_source IS NULL). Returns the number of rows updated."""
    rows = conn.execute(
        """SELECT id, original_name, stored_name
           FROM roms WHERE lang_source IS NULL"""
    ).fetchall()

    updated = 0
    for r in rows:
        li = langtag.detect_any(r["original_name"] or "", r["stored_name"] or "")
        conn.execute(
            """UPDATE roms SET orig_lang = ?, play_lang = ?,
                   is_korean_patched = ?, lang_source = 'auto'
               WHERE id = ?""",
            (li.orig_lang, li.play_lang, int(li.is_korean_patched), r["id"]),
        )
        updated += 1
    return updated


def backfill_region(conn) -> int:
    """Fill the `region` column from the filename for rows that don't have it yet
    (region IS NULL). Metadata only — does NOT strip the region from the display
    name (that rename is a separate, gated operation). Region is read from
    original_name first (keeps the tag even after a Korean rename)."""
    rows = conn.execute(
        """SELECT id, original_name, stored_name
           FROM roms WHERE region IS NULL"""
    ).fetchall()

    updated = 0
    for r in rows:
        region = romtag.region_of(r["original_name"] or "", r["stored_name"] or "")
        if region is None:
            continue
        conn.execute("UPDATE roms SET region = ? WHERE id = ?", (region, r["id"]))
        updated += 1
    return updated
