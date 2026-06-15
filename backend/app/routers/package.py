"""Download the session library as an SD-ready ZIP."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

from .. import db
from ..services import packaging
from .sessions import require_session

router = APIRouter(prefix="/api", tags=["package"])


@router.patch("/sessions/{session_id}/roms/{rom_id}/sd-include")
def set_sd_include(session_id: str, rom_id: str, payload: dict = Body(...)) -> dict:
    """Opt a homebrew ROM into the SD ZIP (its ROM file, not just the cover).
    Body: {"include": true|false}. Default for homebrew is false (covers only)."""
    include = bool(payload.get("include"))
    with db.connect() as conn:
        require_session(conn, session_id)
        row = conn.execute(
            "SELECT id FROM roms WHERE id = ? AND session_id = ?", (rom_id, session_id)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="ROM을 찾을 수 없습니다")
        conn.execute("UPDATE roms SET sd_include = ? WHERE id = ?", (int(include), rom_id))
    return {"rom_id": rom_id, "sd_include": include}


def _parse_systems(system: str | None) -> "set[str] | None":
    """`?system=` accepts one dirname or a comma-separated list (selected systems).
    None / empty → the full SD package."""
    if not system:
        return None
    picked = {s.strip() for s in system.split(",") if s.strip()}
    return picked or None


def _homebrew_roms(conn, session_id: str) -> "set[str]":
    """Relative paths of homebrew ROM files the user opted INTO the SD (sd_include=1).
    Homebrew ships covers-only by default; these are the ROMs to also include."""
    rows = conn.execute(
        "SELECT rom_path FROM roms WHERE session_id = ? AND system_key = 'homebrew' "
        "AND sd_include = 1", (session_id,)).fetchall()
    return {r["rom_path"] for r in rows}


@router.get("/sessions/{session_id}/package/size")
def package_size(session_id: str, video: bool = False, system: str | None = None) -> dict:
    """Estimated on-SD byte size for the (optionally filtered) package."""
    with db.connect() as conn:
        require_session(conn, session_id)
        homebrew = _homebrew_roms(conn, session_id)
    systems = _parse_systems(system)
    return {"bytes": packaging.sd_content_size(session_id, include_video=video, systems=systems,
                                               homebrew_roms=homebrew)}


@router.get("/sessions/{session_id}/package")
def download_package(session_id: str, video: bool = False, system: str | None = None) -> Response:
    """ZIP mirroring the SD card (/roms, /covers). Video (/media) is excluded by
    default — pass ?video=1 to include it. Pass ?system=<dirname> (or a
    comma-separated list) to package only those systems."""
    with db.connect() as conn:
        require_session(conn, session_id)
        homebrew = _homebrew_roms(conn, session_id)
    systems = _parse_systems(system)
    if not packaging.session_has_content(session_id, include_video=video, systems=systems):
        raise HTTPException(status_code=404, detail="Nothing to package yet")

    data = packaging.build_sd_zip(session_id, include_video=video, systems=systems,
                                  homebrew_roms=homebrew)
    # filename suffix: single system → its name; multiple → "-selected"; full → none
    if systems and len(systems) == 1:
        suffix = f"-{next(iter(systems))}"
    elif systems:
        suffix = "-selected"
    else:
        suffix = ""
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="gnw-sd{suffix}-{session_id[:8]}.zip"',
            # Freshly built every time; never serve a stale cached zip (an old copy
            # could still carry pre-fix NFD filenames → broken names on the device).
            "Cache-Control": "no-store, must-revalidate",
        },
    )
