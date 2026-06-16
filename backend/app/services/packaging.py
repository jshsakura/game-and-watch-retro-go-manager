"""Bundle a session's library into a ZIP that mirrors the SD card layout."""
from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

from .. import config
from . import pico8core, storage


def _excluded(root: Path, path: Path, include_video: bool, systems: "set[str] | None" = None,
              homebrew_roms: "set[str] | None" = None) -> bool:
    """Files NOT bound for the SD zip: the DATA scratch dir always; video
    (/media) unless explicitly included (video is an extra, not core SD content).
    When `systems` (a set of dirnames) is set, keep only those systems' roms/covers.
    `homebrew_roms` = relative paths of homebrew ROM files the user opted INTO the
    SD (default: none → homebrew ships covers only)."""
    parts = path.relative_to(root).parts
    rel = "/".join(parts)
    if {storage.SCRATCH_DIR_NAME, storage.PREVIEW_DIR_NAME, storage.TRASH_DIR_NAME,
            storage.FIRMWARE_DIR_NAME, storage.EXTRA_DIR_NAME} & set(parts):
        # _firmware / _extra are internal; added at the SD ROOT below (with the
        # firmware filename / the user's chosen passthrough paths).
        return True
    if not include_video and config.MEDIA_DIR_NAME in parts:
        return True
    # Homebrew: .bin apps are bundled IN the firmware (flashed, not loaded from SD)
    # → SD needs only their COVER, unless the user explicitly opts that .bin in.
    # Asset files (.dat — SMW's smw_assets.dat, Zelda3's zelda3_assets.dat) are
    # REQUIRED to run those ports, so they ALWAYS ship.
    if len(parts) >= 2 and parts[0] == config.ROMS_DIR_NAME and parts[1] == "homebrew":
        if path.suffix.lower() == ".bin" and (not homebrew_roms or rel not in homebrew_roms):
            return True
    if systems is not None:
        # roms/<dirname>/... or covers/<dirname>/... for the SELECTED systems only.
        if len(parts) < 2 or parts[1] not in systems:
            return True
    return False


def _write_sd_zip(zf: "zipfile.ZipFile", session_id: str, include_video: bool,
                  systems: "set[str] | None", homebrew_roms: "set[str] | None") -> None:
    """Write the SD-card layout (/roms, /covers, /media?, /cores, bios, firmware)
    into an OPEN ZipFile. Shared by the in-memory and streamed-to-disk builders.

    Cover .img files already carry their baked-in language flag (applied at
    render_cover time), so they are copied as-is here.
    """
    root = storage.session_root(session_id)
    for path in sorted(root.rglob("*")):
        if path.is_file() and not _excluded(root, path, include_video, systems, homebrew_roms):
            zf.write(path, arcname=str(path.relative_to(root)))
    # Bundle the PICO-8 core (required by the firmware to run .p8) when packaging
    # everything, or whenever pico8 is among the selected systems.
    if systems is None or "pico8" in systems:
        cores = pico8core.ensure_cores_dir()
        if cores and cores.exists():
            for cp in sorted(cores.rglob("*")):
                if cp.is_file():
                    zf.write(cp, arcname=f"cores/{cp.relative_to(cores)}")
    # Extra passthrough files (bios/…) → SD root at their stored paths. Cores
    # can't boot without their BIOS, so ship these with ANY selection — not just
    # the full SD (was the bug: ALL-selection dropped bios + firmware).
    extra = storage.extra_dir(session_id)
    if extra.exists():
        for ep in sorted(extra.rglob("*")):
            if ep.is_file():
                zf.write(ep, arcname=str(ep.relative_to(extra)).replace("\\", "/"))
    # Firmware update → SD ROOT, included with ANY download so the card is always
    # complete (the device only flashes it when the user actually chooses to).
    fw = storage.firmware_path(session_id)
    if fw.exists():
        zf.write(fw, arcname=storage.FIRMWARE_FILENAME)


def build_sd_zip_file(session_id: str, include_video: bool = False, systems: "set[str] | None" = None,
                      homebrew_roms: "set[str] | None" = None) -> str:
    """Build the SD zip to a TEMP FILE on disk and return its path. A full library
    can be hundreds of MB — building it in RAM (the old `build_sd_zip`) OOM-killed
    the worker. Writing to disk keeps memory bounded; the caller serves it streamed
    and deletes it afterwards.
    """
    config.TMP_DIR.mkdir(parents=True, exist_ok=True)
    fd, out_path = tempfile.mkstemp(prefix="gnw-sd-", suffix=".zip", dir=str(config.TMP_DIR))
    os.close(fd)
    try:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            _write_sd_zip(zf, session_id, include_video, systems, homebrew_roms)
    except BaseException:
        # don't leave a half-written temp zip behind on error
        try:
            os.unlink(out_path)
        except OSError:
            pass
        raise
    return out_path


def sd_content_size(session_id: str, include_video: bool = False, systems: "set[str] | None" = None,
                    homebrew_roms: "set[str] | None" = None) -> int:
    """Total bytes of the SD-bound files (roms/covers, +video/+system filters) plus
    the PICO-8 core — an estimate of what lands on the card."""
    root = storage.session_root(session_id)
    total = 0
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file() and not _excluded(root, p, include_video, systems, homebrew_roms):
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    if systems is None or "pico8" in systems:
        cores = pico8core.ensure_cores_dir()
        if cores and cores.exists():
            for cp in cores.rglob("*"):
                if cp.is_file():
                    try:
                        total += cp.stat().st_size
                    except OSError:
                        pass
    # Extra (bios) ships with any selection → always counted.
    extra = storage.extra_dir(session_id)
    if extra.exists():
        for ep in extra.rglob("*"):
            if ep.is_file():
                try:
                    total += ep.stat().st_size
                except OSError:
                    pass
    # Firmware ships with any download → always counted.
    fw = storage.firmware_path(session_id)
    if fw.exists():
        total += fw.stat().st_size
    return total


def session_has_content(session_id: str, include_video: bool = False, systems: "set[str] | None" = None) -> bool:
    """Any SD-bound content? Scratch/DATA (and video, by default) don't count."""
    root = storage.session_root(session_id)
    if not root.exists():
        return False
    return any(
        p.is_file() and not _excluded(root, p, include_video, systems)
        for p in root.rglob("*")
    )
