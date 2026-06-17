"""Parse a Korean-patch version/date from a ROM filename tag.

Korean fan-translation dumps carry the patch revision in the filename, e.g.
    (Korea-patch J-K v20231026 v1.0)   → date 2023-10-26, version v1.0
    (Korea-patch J-K 20120124)         → date 2012-01-24 (no 'v', no version)
    (Korea-patch E-K v20181226 v4.0)   → date 2018-12-26, version v4.0
    (K-v1.2)                           → version v1.2 only (no date)
    (Korea-patch J-K ver.proto)        → 'proto' (pre-release)

The DATE is the primary, objective "which is newer" signal (vs upload order); the
version is secondary. We return a SORTABLE descriptor ("YYYY-MM-DD vX.Y") so the
newest patch of the same game can be chosen deterministically. None = no tag.

This is read from `original_name`, which preserves the full uploaded filename even
after the on-device `stored_name` is cleaned to "한글 (영어)".
"""
from __future__ import annotations

import re

# 8-digit date, optionally 'v'-prefixed: v20231026 / 20120124
_DATE = re.compile(r"\bv?(\d{8})\b")
# dotted version: v1.0, v0.95, v1.02, v4.0, v1.1a  (dot required to avoid dates)
_VER = re.compile(r"\bv(\d+\.\d+[a-z]?)\b", re.I)


def _valid_date(s: str) -> str | None:
    y, mo, d = s[:4], s[4:6], s[6:8]
    if "1980" <= y <= "2099" and "01" <= mo <= "12" and "01" <= d <= "31":
        return f"{y}-{mo}-{d}"
    return None


def parse(name: str | None) -> str | None:
    """Extract a sortable patch descriptor from a filename, or None."""
    if not name:
        return None

    date = None
    for m in _DATE.finditer(name):
        d = _valid_date(m.group(1))
        if d:
            date = d
            break

    mv = _VER.search(name)
    ver = f"v{mv.group(1)}" if mv else None
    if ver is None and re.search(r"\bver\.?\s*proto\b|\bproto\b", name, re.I):
        ver = "proto"

    if date and ver:
        return f"{date} {ver}"
    return date or ver
