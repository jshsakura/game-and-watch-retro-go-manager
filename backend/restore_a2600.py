"""Restore the a2600 entries that hash-dedup removed — they are byte-identical
rebadges but were curated under DIFFERENT names, so keep them (conservative).
Only the gb Zelda (same English title = a true same-game dup) stays deduped."""
from pathlib import Path
from app import db
from app.services import storage, langtag, romtag, name_index

SESSION = "public"
root = storage.session_root(SESSION)
trash = root / "_trash"

NAMES = [
    "아스트로 어택 (Astro Attack).bin",
    "게임 오브 컨센트레이션 (Game of Concentration, A).bin",
    "드래곤 트레저 (Dragon Treasure).bin",
    "스턴트 맨 (Stunt Man).bin",
    "고고 홈 몬스터 (Go Go Home Monster).bin",
    "아스테로이드 벨트 (Asteroid Belt).bin",
    "스쿠버 다이버 (Scuba Diver).bin",
    "스카이 스크레이퍼 (Sky Scraper).bin",
    "스페이스 레이더 (Space Raider).bin",
    "파이터 파일럿 (Fighter Pilot).bin",
    "벌처 어택 (Vulture Attack).bin",
    "스페이스 어드벤처 (Space Adventure).bin",
]
FLAG = {"ko", "ja", "en", "zh", "es", "de", "fr", "it", "eu"}

restored = 0
for name in NAMES:
    stem = name.rsplit(".", 1)[0]
    rom_src = trash / f"roms__a2600__{name}"
    cov_src = trash / f"covers__a2600__{stem}.img"
    if not rom_src.exists():
        print(f"  MISS {name} (no trash file)"); continue
    rom_dst = root / "roms" / "a2600" / name
    rom_dst.parent.mkdir(parents=True, exist_ok=True)
    rom_src.replace(rom_dst)
    cover_rel = None
    cover_status = "none"
    if cov_src.exists():
        cov_dst = root / "covers" / "a2600" / f"{stem}.img"
        cov_dst.parent.mkdir(parents=True, exist_ok=True)
        cov_src.replace(cov_dst)
        cover_rel = f"covers/a2600/{stem}.img"
        cover_status = "ok"
    li = langtag.detect(name)
    region = romtag.region_of(name)
    cf = (li.play_lang or li.orig_lang or "").lower()
    cover_flag = cf if cf in FLAG else None
    chash = name_index.hash_bytes(rom_dst.read_bytes())
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO roms (id, session_id, system_key, original_name, stored_name,
                   korean_name, rom_path, cover_path, cover_status, orig_lang, play_lang,
                   is_korean_patched, lang_source, region, cover_flag, content_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (storage.new_id(), SESSION, "a2600", stem, name, None,
             f"roms/a2600/{name}", cover_rel, cover_status, li.orig_lang, li.play_lang,
             int(li.is_korean_patched), li.source, region, cover_flag, chash),
        )
    restored += 1
    print(f"  OK  {name} (cover={'y' if cover_rel else 'n'})")
print(f"\nrestored {restored}/{len(NAMES)}")
