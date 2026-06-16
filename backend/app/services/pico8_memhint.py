"""Cheap, static PICO-8 'memory pressure' hint computed at upload time.

We read only the cart's code-section header (a handful of steganographic bytes in
the .p8.png) — NO decompression, NO execution — to get the compressed code size
and character count, then express it as a percentage of PICO-8's hard limits.

This is a ROUGH first-pass hint about cart complexity, NOT the real Game & Watch
RAM figure: a small cart that allocates huge runtime arrays can still OOM on the
device. Use it as a nudge, alongside the manual compatibility status.

  estimate(cart) -> int | None   # percent of PICO-8 code limits (None = unknown)
"""
from __future__ import annotations

from pathlib import Path

# PICO-8 hard limits for cart code.
_COMPRESSED_LIMIT = 0x3d00   # 15616 bytes
_CHAR_LIMIT = 0xffff         # 65535 chars
_CART_W, _CART_H = 160, 205  # standard .p8.png dimensions
_CODE_OFFSET = 0x4300        # start of the code section in cart data


def _read_cart_bytes(cart: Path, start: int, count: int) -> bytes | None:
    """Decode `count` steganographic cart bytes starting at offset `start`.
    Each byte lives in the low 2 bits of one pixel's B,G,R,A channels."""
    try:
        from PIL import Image
        with Image.open(cart) as im:
            if im.size != (_CART_W, _CART_H):
                return None
            px = im.convert("RGBA").load()
    except Exception:
        return None
    out = bytearray()
    for off in range(start, start + count):
        idx = off
        x, y = idx % _CART_W, idx // _CART_W
        if y >= _CART_H:
            break
        r, g, b, a = px[x, y]
        out.append((b & 3) | ((g & 3) << 2) | ((r & 3) << 4) | ((a & 3) << 6))
    return bytes(out)


def _sizes(cart: Path) -> tuple[int | None, int] | None:
    """Return (compressed_bytes_or_None, char_count) for the cart's code, or None.
    Only the new PXA format exposes a usable compressed size in the header."""
    head = _read_cart_bytes(cart, _CODE_OFFSET, 8)
    if not head or len(head) < 8:
        return None
    if head[:4] == b"\x00pxa":                 # new PXA format: chars=4-5, compressed=6-7
        return (head[6] << 8) | head[7], (head[4] << 8) | head[5]
    if head[:4] == b":c:\x00":                  # old format: 4-5 is the CHAR count
        return None, (head[4] << 8) | head[5]
    # uncompressed ASCII: scan up to the limit for the terminating null
    blob = _read_cart_bytes(cart, _CODE_OFFSET, _CHAR_LIMIT)
    if not blob:
        return None
    chars = blob.find(0)
    return None, (chars if chars >= 0 else len(blob))


def estimate(cart: str | Path) -> int | None:
    """Percent (0..100+) of PICO-8 code limits — a rough cart-complexity hint.
    Uses the compressed-size ratio when available, else the character ratio."""
    sizes = _sizes(Path(cart))
    if sizes is None:
        return None
    compressed, chars = sizes
    ratios = [chars / _CHAR_LIMIT]
    if compressed is not None:
        ratios.append(compressed / _COMPRESSED_LIMIT)
    return round(max(ratios) * 100)
