"""
Cover-art generation — faithful port of the firmware's tools/gencovers.py.

Device constraint (do not change without checking the firmware):
  - max 186 x 100 px, aspect ratio preserved (downscale only)
  - LANCZOS resampling
  - JPEG, optimize=True, quality 85
  - saved with a ".img" extension
  - same-system covers should share dimensions or the "CoverLight H" view
    misaligns — callers should keep one target size per system.

Inputs accepted: .png .jpg .jpeg .bmp  (matches gencovers.py)
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps


def _open_upright(source: "bytes | str | Path") -> Image.Image:
    """Open an image, applying its EXIF orientation so it's never sideways, and
    convert to RGB. Returns a new image; the source is left untouched."""
    try:
        opener = BytesIO(source) if isinstance(source, bytes) else source
        with Image.open(opener) as opened:
            return ImageOps.exif_transpose(opened).convert("RGB")
    except (OSError, ValueError) as exc:
        raise CoverError(f"Cannot read image: {exc}") from exc

# Hardware-fixed constraints (gencovers.py: MAX_WIDTH, MAX_HEIGHT = 186, 100)
MAX_WIDTH = 186
MAX_HEIGHT = 100
DEFAULT_QUALITY = 85
# The firmware caches one cover per slot at COVER_SIZE = 10 KB (gui.c). Keep the
# encoded .img at or under this so the device can cache it; drop quality to fit.
COVER_MAX_BYTES = 10 * 1024
SUPPORTED_INPUT_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp")


# JPEG encode loop — same logic/params as gencovers.py _save_jpeg_rgb
# (optimize=True, lower quality by `step` from `quality` down to `min_q`, keep the
# smallest if none fit), so our .img bytes match the official tool's output.
_JPEG_MIN_QUALITY = 25
_JPEG_QUALITY_STEP = 6


def _encode_jpeg(img: Image.Image, quality: int, max_bytes: int | None = COVER_MAX_BYTES) -> bytes:
    """JPEG-encode (optimize), lowering quality until it fits `max_bytes`; if none
    fit, return the smallest produced. Mirrors gencovers.py _save_jpeg_rgb."""
    q = max(1, min(100, quality))
    if max_bytes is None:
        buf = BytesIO()
        img.save(buf, format="JPEG", optimize=True, quality=q)
        return buf.getvalue()
    best: bytes | None = None
    while q >= _JPEG_MIN_QUALITY:
        buf = BytesIO()
        img.save(buf, format="JPEG", optimize=True, quality=q)
        data = buf.getvalue()
        if best is None or len(data) < len(best):
            best = data
        if len(data) <= max_bytes:
            return data
        q -= _JPEG_QUALITY_STEP
    return best if best is not None else b""


# Language flag baked into the cover's top-right corner, so 한글판/일본판 etc. are
# recognizable at a glance — in our list AND on the device's own game list.
_FLAGS_DIR = Path(__file__).resolve().parent.parent / "assets" / "flags"
_LANG_CC = {"ko": "kr", "ja": "jp", "en": "us", "zh": "cn",
            "es": "es", "de": "de", "fr": "fr", "it": "it", "eu": "eu"}
# the flag codes the UI/user may pick (keys of _LANG_CC); NULL/other = no flag
FLAG_CODES = frozenset(_LANG_CC)


def overlay_lang_flag(img: Image.Image, lang: "str | None") -> Image.Image:
    """Composite the language's flag onto the top-right corner. No-op if the lang
    has no flag or the asset is missing."""
    cc = _LANG_CC.get((lang or "").lower())
    if not cc:
        return img
    fp = _FLAGS_DIR / f"{cc}.png"
    if not fp.exists():
        return img
    try:
        flag = Image.open(fp).convert("RGBA")
    except OSError:
        return img
    fh = max(8, round(img.height * 0.115))           # uniform small corner mark
    fw = max(8, round(fh * 1.5))                      # fixed 3:2 box → every flag same size
    flag = _crop_to_fill(flag, fw, fh)               # center-crop to fill (US no longer extra-wide)
    # slightly rounded corners
    rad = max(1, round(fh * 0.15))
    mask = Image.new("L", (fw, fh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, fw - 1, fh - 1], radius=rad, fill=255)
    flag.putalpha(ImageChops.multiply(flag.split()[3], mask))
    # thin border so white-background flags (jp/kr) don't blend into light art
    bw = max(1, round(fh * 0.07))
    ImageDraw.Draw(flag).rounded_rectangle(
        [0, 0, fw - 1, fh - 1], radius=rad, outline=(90, 90, 90, 255), width=bw)
    base = img.convert("RGBA")
    m = max(2, round(img.height * 0.035))
    base.alpha_composite(flag, (max(0, base.width - fw - m), m))
    return base.convert("RGB")


class CoverError(ValueError):
    """Raised when an input image cannot be turned into a device cover."""


def calculate_new_size(
    size: tuple[int, int],
    target_width: int | None = None,
    target_height: int | None = None,
) -> tuple[int, int]:
    """
    New (w, h) preserving aspect ratio so the whole image fits within the
    186x100 envelope. Mirrors gencovers.calculate_new_size().
    """
    original_width, original_height = size
    if original_width <= 0 or original_height <= 0:
        raise CoverError("Image has zero dimension")

    target_width = MAX_WIDTH if target_width is None else min(target_width, MAX_WIDTH)
    target_height = MAX_HEIGHT if target_height is None else min(target_height, MAX_HEIGHT)

    scale = min(target_width / original_width, target_height / original_height)
    return max(1, int(original_width * scale)), max(1, int(original_height * scale))


def _crop_to_fill(img: Image.Image, target_width: int, target_height: int) -> Image.Image:
    """Scale (preserving ratio) to COVER the target box, then center-crop to it.
    Produces exactly target_width x target_height — uniform tiles like the device,
    cropping overflow instead of letterboxing."""
    w, h = img.size
    if w <= 0 or h <= 0:
        raise CoverError("Image has zero dimension")
    scale = max(target_width / w, target_height / h)
    nw, nh = max(target_width, round(w * scale)), max(target_height, round(h * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - target_width) // 2
    top = (nh - target_height) // 2
    return resized.crop((left, top, left + target_width, top + target_height))


def _apply_crop_box(img: Image.Image,
                    crop_box: tuple[float, float, float, float]) -> Image.Image:
    """Crop the 0..1-fractional (x, y, w, h) region out of the image."""
    w0, h0 = img.size
    x, y, bw, bh = crop_box
    left, top = max(0, round(x * w0)), max(0, round(y * h0))
    right, bottom = min(w0, round((x + bw) * w0)), min(h0, round((y + bh) * h0))
    if right <= left or bottom <= top:
        raise CoverError("invalid crop box")
    return img.crop((left, top, right, bottom))


def render_cover(
    source: bytes | str | Path,
    *,
    target_width: int | None = None,
    target_height: int | None = None,
    quality: int = DEFAULT_QUALITY,
    crop: bool = False,
    crop_box: tuple[float, float, float, float] | None = None,
    lang: "str | None" = None,
) -> bytes:
    """
    Turn a source image into device cover bytes (JPEG payload of the .img file).

    When a target size is given (callers pass systems.cover_target()), the cover
    is crop-to-filled to EXACTLY target_width x target_height so every cover in a
    system shares one size — the firmware grid frame then fits them all. With no
    target it fit-withins the 186x100 envelope (the official gencovers.py default).

      - crop_box=(x, y, w, h) as 0..1 fractions → use that region as the source
        (the user's hand-picked crop), then normalize to the target size.

    `source` may be raw image bytes or a path. Returns the encoded bytes; the
    caller decides where to write the ".img" file. Does not mutate input.
    """
    img = _open_upright(source)  # EXIF-corrected, RGB, original untouched
    if crop_box is not None:
        img = _apply_crop_box(img, crop_box)

    fixed = target_width is not None and target_height is not None
    if fixed:
        tw, th = min(target_width, MAX_WIDTH), min(target_height, MAX_HEIGHT)
        out = _crop_to_fill(img, tw, th)              # exact tw x th, full-bleed
    elif crop:
        out = _crop_to_fill(img, MAX_WIDTH, MAX_HEIGHT)
    else:
        out = img.resize(calculate_new_size(img.size, target_width, target_height),
                         Image.Resampling.LANCZOS)

    out = overlay_lang_flag(out, lang)   # pre-bake the flag onto the device .img only
    return _encode_jpeg(out, quality)   # JPEG, capped at COVER_MAX_BYTES (10 KB)


def render_preview(
    source: bytes | str | Path,
    *,
    max_side: int = 512,
    quality: int = 90,
    crop_box: tuple[float, float, float, float] | None = None,
    lang: "str | None" = None,
) -> bytes:
    """High-res WEB preview (the device .img is only 186x100, looks bad on screen).
    Keeps the whole cover (or just `crop_box` region), downscale-only to `max_side`
    on the long edge. WebP."""
    img = _open_upright(source)
    if crop_box is not None:
        w0, h0 = img.size
        x, y, bw, bh = crop_box
        left, top = max(0, round(x * w0)), max(0, round(y * h0))
        right, bottom = min(w0, round((x + bw) * w0)), min(h0, round((y + bh) * h0))
        if right > left and bottom > top:
            img = img.crop((left, top, right, bottom))
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)
    # NOTE: no flag here — the web "원본/전체 모양" preview stays the clean original.
    buf = BytesIO()
    img.save(buf, format="WEBP", quality=max(1, min(100, quality)), method=6)
    return buf.getvalue()


def render_display(
    source: bytes | str | Path,
    target_width: int,
    target_height: int,
    *,
    max_height: int = 400,
    quality: int = 88,
    crop_box: tuple[float, float, float, float] | None = None,
    lang: "str | None" = None,
) -> bytes:
    """High-res WEB display image: the original art cropped to the system ratio
    (target_width:target_height) — the SAME framing the device shows, but crisp.
    When `crop_box` is given (the user's hand-picked region) it's applied first so
    the thumbnail matches the device .img exactly; else center-crop. Downscale-only
    (never upscales past the source), so small art stays native-size. WebP."""
    img = _open_upright(source)
    if crop_box is not None:
        img = _apply_crop_box(img, crop_box)
    ratio = target_width / target_height
    # largest box at this ratio that fits inside the source, capped at max_height
    fit_h = min(img.height, img.width / ratio)
    out_h = max(1, int(min(max_height, fit_h)))
    out_w = max(1, round(out_h * ratio))
    out = _crop_to_fill(img, out_w, out_h)
    out = overlay_lang_flag(out, lang)   # LIVE overlay for the list/card — never written to disk
    buf = BytesIO()
    out.save(buf, format="WEBP", quality=max(1, min(100, quality)), method=6)
    return buf.getvalue()


def cover_filename(rom_filename: str) -> str:
    """ROM basename -> cover basename. '/roms/msx/Aleste.rom' -> 'Aleste.img'."""
    stem = Path(rom_filename).name
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    return f"{stem}.img"
