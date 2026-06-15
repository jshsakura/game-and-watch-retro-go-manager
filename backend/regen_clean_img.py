"""Re-render every flagged-language device cover (.img) CLEAN from its high-res
preview, with the flag overlay now disabled in render_cover. This strips the
small flag that got baked into the auto covers during the earlier recovery run,
so the stored .img matches the clean preview. The language flag is then applied
only at SD-export time (see packaging.build_sd_zip).

Non-destructive: previews are read-only here; only the .img files are rewritten.
A clean preview in → a clean .img out. (The 9 auto covers whose preview still has
an old baked flag will keep it — those need re-sourcing, handled separately.)
"""
import json

from app import db
from app.routers.covers import _render_cover, _preview_path, _dirname_of
from app.services import covers, storage

SESSION = "public"


def main() -> None:
    with db.connect() as conn:
        targets = [dict(r) for r in conn.execute(
            "SELECT * FROM roms WHERE session_id=? AND cover_status='ok' "
            "AND cover_flag IS NOT NULL", (SESSION,)).fetchall()]
    print(f"re-baking .img for {len(targets)} flagged covers (by cover_flag)", flush=True)

    ok = skip = err = 0
    for rom in targets:
        pv = _preview_path(SESSION, rom)
        if not pv.exists():
            skip += 1
            continue
        try:
            cb = json.loads(rom["crop_box"]) if rom.get("crop_box") else None
            cover_bytes = _render_cover(rom, pv.read_bytes(), crop_box=cb)
        except Exception as exc:
            err += 1
            print(f"  ERR {rom['stored_name']}: {exc}", flush=True)
            continue
        cover_path = storage.covers_dir(SESSION, _dirname_of(rom)) / covers.cover_filename(rom["stored_name"])
        storage.write_bytes(cover_path, cover_bytes)
        ok += 1
        if ok % 100 == 0:
            print(f"  {ok}/{len(targets)}", flush=True)

    print(f"DONE  regenerated={ok}  no-preview={skip}  errors={err}", flush=True)


if __name__ == "__main__":
    main()
