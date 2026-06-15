"""
PICO-8 cover generation — faithful port of the firmware's tools/pico8covers.py.

PICO-8 carts carry their own 128x128 label, so covers come from the cart
itself (no external art needed):
  - .p8  (text): the `__label__` section, hex/extended color indices.
  - .p8.png    : a 128x128 region at pixel (16, 24) of the 160x205 cart image,
                 re-snapped to the PICO-8 palette.
Rendered with the full 32-color PICO-8 palette, then saved as JPEG (.img).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from .covers import COVER_MAX_BYTES, MAX_HEIGHT, MAX_WIDTH, CoverError, _encode_jpeg

# Standard 16 + extended 16 = full 32-color PICO-8 palette.
_PALETTE = [
    (0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81),
    (171, 82, 54), (95, 87, 79), (194, 195, 199), (255, 241, 232),
    (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54),
    (41, 173, 255), (131, 118, 156), (255, 119, 168), (255, 204, 170),
    (41, 24, 20), (17, 29, 53), (66, 33, 54), (18, 83, 89),
    (116, 47, 41), (73, 51, 59), (162, 136, 121), (243, 239, 125),
    (190, 18, 80), (255, 108, 36), (168, 231, 46), (0, 181, 67),
    (6, 90, 181), (117, 70, 101), (255, 110, 89), (255, 157, 129),
]
_LABEL_SIZE = 128
_LABEL_OFFSET = (16, 24)  # within the 160x205 .p8.png cart image


def _closest_index(r: int, g: int, b: int) -> int:
    best_idx, best_dist = 0, 1 << 30
    for i, (pr, pg, pb) in enumerate(_PALETTE):
        dr, dg, db = pr - r, pg - g, pb - b
        dist = dr * dr + db * db + dg * dg
        if dist < best_dist:
            best_idx, best_dist = i, dist
    return best_idx


def _label_from_p8_text(path: Path) -> Image.Image | None:
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows: list[str] = []
    in_label = False
    for line in text:
        line = line.rstrip("\r")
        if line == "__label__":
            in_label = True
            continue
        if in_label:
            if line.startswith("__"):
                break
            rows.append(line)
    if len(rows) < _LABEL_SIZE:
        return None

    img = Image.new("RGB", (_LABEL_SIZE, _LABEL_SIZE))
    px = img.load()
    for y in range(_LABEL_SIZE):
        row = rows[y]
        for x in range(min(_LABEL_SIZE, len(row))):
            c = row[x]
            if "0" <= c <= "9":
                idx = int(c)
            elif "a" <= c <= "f":
                idx = 10 + ord(c) - ord("a")
            elif "g" <= c <= "v":          # extended palette g=16..v=31
                idx = 16 + ord(c) - ord("g")
            else:
                idx = 0
            if idx < len(_PALETTE):
                px[x, y] = _PALETTE[idx]
    return img


def _label_from_p8_png(path: Path) -> Image.Image | None:
    with Image.open(path) as opened:
        src = opened.convert("RGB")
    lx, ly = _LABEL_OFFSET
    if src.width < lx + _LABEL_SIZE or src.height < ly + _LABEL_SIZE:
        return None
    region = src.crop((lx, ly, lx + _LABEL_SIZE, ly + _LABEL_SIZE))
    out = Image.new("RGB", (_LABEL_SIZE, _LABEL_SIZE))
    src_px, out_px = region.load(), out.load()
    for y in range(_LABEL_SIZE):
        for x in range(_LABEL_SIZE):
            r, g, b = src_px[x, y]
            out_px[x, y] = _PALETTE[_closest_index(r, g, b)]
    return out


def extract_label(cart: str | Path) -> Image.Image | None:
    """Extract the 128x128 PICO-8 label from a .p8 or .p8.png cart."""
    path = Path(cart)
    lower = path.name.lower()
    if lower.endswith(".p8.png") or lower.endswith(".png"):
        return _label_from_p8_png(path)
    if lower.endswith(".p8"):
        return _label_from_p8_text(path)
    return None


def render_pico8_cover(cart: str | Path, quality: int = 85) -> bytes:
    """
    Build cover (.img JPEG) bytes from a PICO-8 cart's embedded label.
    The label is 128x128 square, so fit-within 186x100 lands at exactly 100x100 —
    the square PICO-8 cover. Same pipeline as gencovers.py (extract → fit-within →
    size-capped JPEG at COVER_MAX_BYTES).
    """
    label = extract_label(cart)
    if label is None:
        raise CoverError("No PICO-8 label found in cart")

    scale = min(MAX_WIDTH / label.width, MAX_HEIGHT / label.height)
    new_size = (max(1, int(label.width * scale)), max(1, int(label.height * scale)))
    resized = label.resize(new_size, Image.Resampling.LANCZOS)
    return _encode_jpeg(resized, quality, COVER_MAX_BYTES)


# Device cover is a fixed 100x100 square (label fit-within 186x100). PICO-8 has no
# external high-res art — the cart label IS the source — so the web "original" is
# just that label at the same 100x100 square, not a fake upscale of the cart PNG.
PICO8_PREVIEW_SIDE = 100


def render_pico8_preview(cart: str | Path, side: int = PICO8_PREVIEW_SIDE) -> bytes:
    """Square WebP web preview from the cart's 128x128 label (→ side×side)."""
    from io import BytesIO

    label = extract_label(cart)
    if label is None:
        raise CoverError("No PICO-8 label found in cart")
    img = label.resize((side, side), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="WEBP", quality=92, method=6)
    return buf.getvalue()
