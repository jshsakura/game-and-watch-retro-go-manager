"""One-off background cover fetch for the Atari 2600 import. Marks every
cover-less a2600 rom 'pending' (UI shows a spinner), then resolves each:
autofill_rom sets 'ok' on a hit, we set 'failed' on a miss."""
import asyncio
from app import db, config
from app.routers.covers import autofill_rom

SID = config.SHARED_SESSION_ID


async def main():
    with db.connect() as conn:
        conn.execute(
            "UPDATE roms SET cover_status='pending' "
            "WHERE session_id=? AND system_key='a2600' AND cover_status='none'",
            (SID,),
        )
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM roms WHERE session_id=? AND system_key='a2600' "
            "AND cover_status IN ('pending','none')", (SID,)).fetchall()]

    total = len(rows)
    ok = failed = 0
    for i, rom in enumerate(rows, 1):
        try:
            got = await autofill_rom(SID, rom)
        except Exception:
            got = False
        if got:
            ok += 1
        else:
            failed += 1
            with db.connect() as conn:
                conn.execute("UPDATE roms SET cover_status='failed' WHERE id=?", (rom["id"],))
        if i % 25 == 0 or i == total:
            print(f"{i}/{total} — ok {ok} · failed {failed}", flush=True)
        await asyncio.sleep(0.1)
    print(f"DONE: {total} 처리 · 커버 {ok} · 실패 {failed}", flush=True)


asyncio.run(main())
