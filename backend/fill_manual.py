"""Try to clean-fill the flagged manual/crop covers via the normal autofill
chain (IGDB -> TGDB -> libretro -> no-platform variants). Only overwrites on a
successful clean fetch; failures keep their current (flagged) cover. The curated
originals remain backed up at data/_recovery/preflag-20260614.

Prints every rom it managed to fill, and the full list it could NOT (those need
manual/blog sourcing).
"""
import asyncio

from app import db
from app.routers.covers import autofill_rom

SESSION = "public"
FLAG = {"ko", "ja", "en", "zh", "es", "de", "fr", "it", "eu"}
CONCURRENCY = 4


def _lang(r: dict) -> str:
    if r.get("is_korean_patched"):
        return "ko"
    return (r.get("play_lang") or r.get("orig_lang") or "").lower()


def _targets() -> list[dict]:
    with db.connect() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM roms WHERE session_id=? AND cover_status='ok' "
            "AND cover_source IN ('manual','crop')", (SESSION,)).fetchall()]
    return [r for r in rows if _lang(r) in FLAG]


async def main() -> None:
    targets = _targets()
    print(f"flagged manual/crop targets: {len(targets)}", flush=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    filled: list[str] = []
    missed: list[str] = []

    async def one(rom: dict) -> None:
        async with sem:
            try:
                ok = await autofill_rom(SESSION, rom)
            except Exception as exc:
                print(f"  ERR {rom['stored_name']}: {exc}", flush=True)
                ok = False
        (filled if ok else missed).append(rom["stored_name"])
        if ok:
            print(f"  FILLED {rom['stored_name']}", flush=True)

    await asyncio.gather(*(one(r) for r in targets))

    print(f"\nDONE  filled={len(filled)}  still-missing={len(missed)}", flush=True)
    print("\n=== STILL NEEDS MANUAL/BLOG SOURCING ===", flush=True)
    for name in sorted(missed):
        print(f"  {name}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
