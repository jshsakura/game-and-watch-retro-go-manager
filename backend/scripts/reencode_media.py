#!/usr/bin/env python3
"""Re-encode existing /media videos with the CURRENT encoder settings.

Why: changing video.py's FRAME_RATE / VIDEO_QSCALE only affects NEW uploads.
Already-encoded .avi files on disk keep their old fps/quality. Run this once
after tuning those constants to bring the back-catalogue in line.

Source = the existing active .avi (the original upload is not retained). Files
are already 320x240, so re-applying the 'fit' filter only changes fps + qscale
(scale/pad become no-ops). Written to a temp file then atomically swapped in, so
a video that's mid-playback keeps reading its old inode and never corrupts.

Run from the backend/ dir:   python3 scripts/reencode_media.py [--dry-run]
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

# Ensure backend/ (this file's grandparent) is importable → `app` package resolves
# regardless of the caller's cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import config                          # noqa: E402
from app.services import storage, video         # noqa: E402


def _abs_path(session_id: str, avi_path: str, avi_name: str) -> Path:
    root = storage.session_root(session_id)
    if avi_path:
        return root / avi_path
    return storage.media_dir(session_id) / avi_name


def _probe(path: Path) -> str:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True).stdout.split()
        return "x".join(out[:2]) + f" @ {out[2]}" if len(out) >= 3 else "?"
    except Exception:
        return "?"


def main() -> int:
    dry = "--dry-run" in sys.argv
    if not video.ffmpeg_available():
        print("ffmpeg not found"); return 1

    conn = sqlite3.connect(config.DB_PATH)
    rows = list(conn.execute(
        "SELECT session_id, avi_name, avi_path FROM videos WHERE status = 'ok'"))
    conn.close()

    print(f"re-encoding {len(rows)} videos at q{video.VIDEO_QSCALE} @ {video.FRAME_RATE}fps"
          + (" (dry run)" if dry else ""))
    done = 0
    for session_id, avi_name, avi_path in rows:
        src = _abs_path(session_id, avi_path or "", avi_name)
        if not src.exists():
            print(f"  SKIP (missing): {avi_name}")
            continue
        before = src.stat().st_size
        print(f"  {avi_name}\n    before: {before // 1024} KB  {_probe(src)}")
        if dry:
            continue

        tmp = src.with_name(src.stem + ".reenc.avi")
        cmd = video.build_command(src, tmp)         # current fps/qscale, 'fit'
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"    FAILED: {e.stderr.decode('utf-8', 'ignore')[-300:]}")
            tmp.unlink(missing_ok=True)
            continue
        os.replace(tmp, src)                        # atomic swap (mid-play safe)
        after = src.stat().st_size
        pct = round((1 - after / before) * 100) if before else 0
        print(f"    after:  {after // 1024} KB  {_probe(src)}   (-{pct}%)")
        done += 1

    print(f"done: {done}/{len(rows)} re-encoded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
