"""One-off recovery: re-fetch covers for the 667 AUTO roms whose previews got a
baked language flag, restoring clean previews + .img. Manual covers are left
untouched. The pre-flag state is backed up at data/_recovery/preflag-20260614.

Failures keep their existing (backed-up) cover — autofill_rom only overwrites on
a successful fetch.
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
            "AND cover_source='auto'", (SESSION,)).fetchall()]
    return [r for r in rows if _lang(r) in FLAG]


async def main() -> None:
    targets = _targets()
    print(f"target auto-flagged roms: {len(targets)}", flush=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    ok = fail = 0
    done = 0

    async def one(rom: dict) -> bool:
        async with sem:
            try:
                return await autofill_rom(SESSION, rom)
            except Exception as exc:  # keep going; failure → old cover stays
                print(f"  ERR {rom.get('display_name') or rom['id']}: {exc}", flush=True)
                return False

    results = []
    tasks = [asyncio.create_task(one(r)) for r in targets]
    for fut in asyncio.as_completed(tasks):
        res = await fut
        done += 1
        if res:
            ok += 1
        else:
            fail += 1
        if done % 25 == 0:
            print(f"  progress {done}/{len(targets)}  ok={ok} fail={fail}", flush=True)
        results.append(res)

    print(f"DONE  re-fetched(ok)={ok}  kept-old(fail)={fail}  total={len(targets)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
