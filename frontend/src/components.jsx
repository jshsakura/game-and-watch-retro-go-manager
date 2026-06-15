import React, { useEffect, useRef, useState } from "react";
import Cropper from "react-easy-crop";
import {
  Check, ImageOff, XCircle, ImagePlus, Loader, Play,
  Download, MoreHorizontal, Trash2, X, Film, Music, ChevronDown, Pencil, Search, Hand, Crop, Upload, FolderPlus, Flag,
} from "lucide-react";
import { EmulatorOverlay, canPlay, isExperimental } from "./emulator.jsx";
import {
  uploadCover, coverUrl, deviceCoverUrl, originalCoverUrl, coverDownloadUrl, downloadRomUrl, downloadVideoUrl, downloadMusicUrl,
  videoThumbUrl, videoPreviewUrl, musicCoverUrl, streamMusicUrl, deleteRom, deleteVideo, deleteMusic,
  renameRom, igdbSearch, setCoverFromUrl, deleteCover, recropCover, replaceRomFile, formatBytes, setRomLang, setCoverFlag, setSdInclude,
  addRomFile, deleteRomFile,
} from "./api.js";
import { useToast } from "./toast.jsx";
import { useKoreanMode } from "./config.jsx";
import { useT, useI18n } from "./i18n.jsx";

// System icon keyed 1:1 to the firmware folder name (dirname): the asset at
// /system-icons/<dirname>.svg is THE icon for that system. Until that asset is
// dropped in, fall back to a DISTINCT colored code chip per system (so systems
// never look identical).
const SYS_ABBREV = {
  nes: "NES", gb: "GB", gbc: "GBC", gg: "GG", sms: "SMS", md: "MD", sg: "SG",
  pce: "PCE", col: "COL", msx: "MSX", a2600: "A26", a7800: "A78", amstrad: "CPC",
  wsv: "WSV", tama: "TAM", mini: "MIN", gw: "GW", homebrew: "HB", pico8: "P8",
};

function hueFor(key) {
  let h = 0;
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}

// Distinct vivid accent per system (the hash hues were too similar).
const SYS_PALETTE = {
  nes: "#e23b3b", gb: "#6ab02c", gbc: "#7b3ff2", gg: "#13a8c4", sms: "#2c7be0",
  md: "#e07a1a", sg: "#13a07a", pce: "#d61f6b", col: "#d94f2b", msx: "#3b5bdb",
  a2600: "#9b59b6", a7800: "#b5651d", amstrad: "#0f9d58", wsv: "#d4a017",
  tama: "#1fc4a8", mini: "#e84393", gw: "#c9a227", homebrew: "#6b7280", pico8: "#ff77a8",
};
export function systemColor(key) {
  return SYS_PALETTE[key] || `hsl(${hueFor(key || "x")} 62% 52%)`;
}

// Try the real asset (svg first, then png — RomM ico-derived), then fall back
// to the colored monogram chip when no asset exists (tama/gw/homebrew).
const ICON_EXTS = ["svg", "png"];
export function SystemIcon({ dirname, size = 16 }) {
  const [extIdx, setExtIdx] = useState(0);
  const imgRef = useRef(null);
  useEffect(() => { setExtIdx(0); }, [dirname]);
  const exhausted = extIdx >= ICON_EXTS.length;
  const next = () => setExtIdx((i) => i + 1);

  // A cached/transient broken image won't fire onError (it's already `complete`
  // with naturalWidth 0) → it would show a broken-X. Detect and advance to the
  // next ext, finally the monogram. Guarantees the chip never shows an X.
  useEffect(() => {
    const im = imgRef.current;
    if (im && im.complete && im.naturalWidth === 0) next();
  }, [extIdx, dirname]);

  if (dirname && !exhausted) {
    return (
      <img
        ref={imgRef}
        className="sys-ico"
        src={`/system-icons/${dirname}.${ICON_EXTS[extIdx]}`}
        width={size}
        height={size}
        alt=""
        onError={next}
        onLoad={(e) => { if (e.currentTarget.naturalWidth === 0) next(); }}
      />
    );
  }
  const label = SYS_ABBREV[dirname] || (dirname || "?").slice(0, 3).toUpperCase();
  const hue = hueFor(dirname || "x");
  return (
    <span
      className="sys-mono"
      style={{ background: `hsl(${hue} 48% 38%)`, fontSize: Math.max(6, Math.round(size * 0.5)) }}
      aria-hidden
    >
      {label}
    </span>
  );
}

// "Cartridge slot" dropdown for picking a system — replaces the wall of chips.
// Closes on outside click / Escape. The trigger reads like a cartridge seated
// in a slot; the panel lists all systems with their icon + accepted extensions.
export function SystemSelect({ systems, value, onChange }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const current = systems.find((s) => s.key === value);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className={`sysselect ${open ? "open" : ""}`} ref={ref}>
      <button
        type="button"
        className="sysselect-trigger"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="sysselect-tag">{t("플랫폼")}</span>
        <span className="sysselect-cart">{current?.Icon ? <current.Icon size={18} aria-hidden /> : <SystemIcon dirname={current?.dirname} size={18} />}</span>
        <span className="sysselect-name">{current?.name ?? t("선택")}</span>
        {current?.exts?.length > 0 && <span className="sysselect-ext">.{current.exts.join(" .")}</span>}
        <span className="sysselect-chev"><ChevronDown size={16} strokeWidth={2.5} aria-hidden /></span>
      </button>
      {open && (
        <div className="sysselect-panel" role="listbox">
          {systems.map((s) => (
            <button
              key={s.key}
              type="button"
              role="option"
              aria-selected={s.key === value}
              className={`sysselect-opt ${s.key === value ? "on" : ""}`}
              onClick={() => { onChange(s.key); setOpen(false); }}
            >
              {s.Icon ? <s.Icon size={18} aria-hidden /> : <SystemIcon dirname={s.dirname} size={18} />}
              <span className="sysselect-opt-name">{s.name}</span>
              {s.exts?.length > 0 && <span className="sysselect-opt-ext">.{s.exts.join(" .")}</span>}
              {s.key === value && <Check size={14} strokeWidth={3} aria-hidden />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Recurse a dropped folder (DataTransfer entries) into a flat file list, tagging
// each file with its webkitRelativePath. Falls back to a plain file list.
async function filesFromDrop(dt) {
  const items = dt.items ? Array.from(dt.items) : [];
  const entries = items.map((it) => it.webkitGetAsEntry?.()).filter(Boolean);
  if (!entries.length) return Array.from(dt.files || []);
  const out = [];
  const walk = (entry, prefix) => new Promise((resolve) => {
    if (entry.isFile) {
      entry.file((f) => {
        try { Object.defineProperty(f, "webkitRelativePath", { value: prefix + entry.name }); } catch (_) {}
        out.push(f); resolve();
      }, () => resolve());
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      reader.readEntries(async (ents) => {
        for (const e of ents) await walk(e, prefix + entry.name + "/");
        resolve();
      }, () => resolve());
    } else resolve();
  });
  for (const e of entries) await walk(e, "");
  return out;
}

// Drag-and-drop + click-to-pick file zone. Shows a busy overlay while onFiles
// runs. `folder` adds a button to pick a whole folder (subfolders included).
export function Dropzone({ accept, multiple, label, folder, onFiles }) {
  const t = useT();
  const inputRef = useRef(null);
  const folderRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pct, setPct] = useState(null);   // null = no byte progress yet (indeterminate)

  const handle = async (fileList) => {
    const files = Array.from(fileList || []);
    if (!files.length || busy) return;
    setBusy(true); setPct(null);
    try {
      await Promise.resolve(onFiles(files, (loaded, total) =>
        setPct(total ? Math.min(100, Math.round((loaded / total) * 100)) : null)));
    } finally {
      setBusy(false); setPct(null);
    }
  };

  const processing = pct === 100;   // 100% uploaded, awaiting server response
  return (
    <div
      className={`dropzone ${drag ? "drag" : ""} ${busy ? "busy" : ""}`}
      onClick={() => !busy && inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); if (!busy) setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={async (e) => { e.preventDefault(); setDrag(false); handle(await filesFromDrop(e.dataTransfer)); }}
    >
      {busy ? (
        <div className="dz-busy">
          <span className="dz-busy-label">
            <Loader size={15} className="spin" aria-hidden />
            {pct == null ? ` ${t("업로드 중…")}` : processing ? ` ${t("처리 중…")}` : ` ${t("업로드 중… {pct}%", { pct })}`}
          </span>
          <div className={`dl-bar ${pct == null || processing ? "indet" : ""}`}>
            <div className="dl-fill" style={pct == null || processing ? undefined : { width: `${pct}%` }} />
          </div>
        </div>
      ) : (
        <>
          {label}
          {folder && (
            <button type="button" className="dz-folder-btn" disabled={busy}
              onClick={(e) => { e.stopPropagation(); folderRef.current?.click(); }}>
              <FolderPlus size={13} strokeWidth={2.5} /> {t("폴더 통째로")}
            </button>
          )}
        </>
      )}
      <input ref={inputRef} type="file" accept={accept} multiple={multiple} hidden
        onChange={(e) => { handle(e.target.files); e.target.value = ""; }} />
      {folder && (
        <input ref={folderRef} type="file" webkitdirectory="" directory="" multiple hidden
          onChange={(e) => { handle(e.target.files); e.target.value = ""; }} />
      )}
    </div>
  );
}

// Cover slot — shows the cover (or a beautiful centered placeholder when
// missing/broken) and is clickable to upload your own cover image directly.
export function CoverSlot({ romId, src: initialSrc, bust, alt = "", aspect = 3 / 4, onActivate, badge = null, status = null, overlay = null }) {
  const t = useT();
  const [src, setSrc] = useState(initialSrc || null);
  const [err, setErr] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const imgRef = useRef(null);
  const showImg = src && !err;

  // Cached images can be `complete` before React attaches onLoad, so onLoad never
  // fires and the skeleton would spin forever. Detect that and mark it loaded.
  useEffect(() => {
    const img = imgRef.current;
    if (img && img.complete) {
      if (img.naturalWidth > 0) setLoaded(true);
      else setErr(true);
    }
  }, [src]);

  // Failsafe: if a cover request stalls (e.g. backend busy building the SD zip),
  // stop the skeleton after a timeout so it never spins forever.
  useEffect(() => {
    if (!showImg || loaded) return undefined;
    const t = setTimeout(() => setLoaded(true), 10000);
    return () => clearTimeout(t);
  }, [showImg, loaded, src]);

  // Reflect external src changes (e.g. cover_status flipped to ok after reload).
  useEffect(() => { setSrc(initialSrc || null); setErr(false); setLoaded(false); }, [initialSrc]);
  // A cover (re)applied elsewhere keeps the SAME url → bump the bust to reload.
  useEffect(() => {
    if (bust && romId) { setSrc(`${coverUrl(romId)}?v=${bust}`); setErr(false); setLoaded(false); }
  }, [bust, romId]);

  // Clickable even while 'pending' — opening the detail lets the user upload a
  // cover manually, which acts as a stop/override for the running search.
  return (
    <div
      className={`shot cover-slot ${showImg ? "" : "shot-empty"} ${romId ? "clickable" : ""}`}
      style={{ aspectRatio: aspect }}
      onClick={() => romId && onActivate?.()}
      title={romId ? t("클릭해서 상세 보기") : ""}
    >
      {showImg ? (
        <>
          {!loaded && <div className="skeleton" aria-hidden />}
          <img
            ref={imgRef}
            src={src}
            alt={alt}
            loading="lazy"
            style={{ opacity: loaded ? 1 : 0 }}
            onLoad={() => setLoaded(true)}
            onError={() => { setErr(true); setLoaded(true); }}
          />
        </>
      ) : status === "pending" ? (
        <div className="cover-add cover-searching">
          <Loader size={22} className="spin" aria-hidden />
          <span>{t("커버 검색중…")}</span>
        </div>
      ) : (
        <div className="cover-add">
          <ImagePlus size={24} strokeWidth={2} aria-hidden />
          <span>{t("커버 추가")}</span>
        </div>
      )}
      {overlay && <span className="cover-corner">{overlay}</span>}
      {badge && <span className="cover-badge">{badge}</span>}
    </div>
  );
}

export function ProgressBar({ value }) {
  return (
    <div className="progress">
      <i style={{ width: `${Math.round((value || 0) * 100)}%` }} />
    </div>
  );
}

// Inline loading indicator — shown while a tab fetches its data.
export function Loading({ text }) {
  const t = useT();
  return (
    <div className="loading" role="status" aria-live="polite">
      <Loader size={16} className="spin" aria-hidden /> {text ?? t("불러오는 중…")}
    </div>
  );
}

const BADGE = {
  ok: { Icon: Check, text: "COVER OK" },
  none: { Icon: ImageOff, text: "NO COVER" },
  failed: { Icon: XCircle, text: "FAIL" },
};

export function Badge({ status }) {
  const b = BADGE[status] || { Icon: null, text: status };
  return (
    <span className={`badge ${status}`}>
      {b.Icon && <b.Icon size={11} strokeWidth={2.5} aria-hidden />} {b.text}
    </span>
  );
}

// Centered popup over a dimmed backdrop.
export function Modal({ title, onClose, children }) {
  // Close ONLY on the X button or Escape — never on an outside/backdrop click
  // (avoids losing work by mis-clicking).
  useEffect(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose?.(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-head">
          <span className="modal-title">{title}</span>
          <button className="icon-btn" onClick={onClose} aria-label="close">
            <X size={14} strokeWidth={2.5} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

// IGDB cover search (검색기) — runs inside the ROM popup. Search by name,
// pick a cover thumbnail → it's fetched, rendered to 186x100 .img, and applied.
// Strip the extension and release tags ((..)/[..]) so the name matches IGDB.
function cleanTitle(name = "") {
  return name
    .replace(/\.[^.]+$/, "")
    .replace(/[([{].*?[)\]}]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// No-Intro region/dump tags — NOT titles (so "(USA, Europe)" / "(Japan)" never
// become the search query).
const REGION_RE = /^(japan|usa|world|europe|korea|asia|france|germany|spain|italy|netherlands|sweden|australia|brazil|china|taiwan|unl|proto|beta|sample|demo|pd|rev\b.*|en|jp|us|eu|ko|j|u|e|k)$/i;
function isRegionTag(s) {
  const parts = s.split(/[,/]/).map((p) => p.trim()).filter(Boolean);
  return parts.length > 0 && parts.every((p) => REGION_RE.test(p));
}

// Default cover-search query. The "한글명 (English)" convention only holds when the
// part BEFORE the parens is non-latin (Korean) AND it isn't a region tag —
// otherwise the parens hold a region tag like "(USA, Europe)", so just use the
// filename (tags stripped). e.g. "Untouchable (USA, Europe)" → "Untouchable".
function englishTerm(rom) {
  const stem = (rom.stored_name || "").replace(/\.[^.]+$/, "");
  const m = stem.match(/\(([A-Za-z0-9][^)]*)\)/);
  if (m && !/[A-Za-z]/.test(stem.slice(0, m.index)) && !isRegionTag(m[1].trim())) {
    return m[1].trim();
  }
  return cleanTitle(stem);
}

function CoverSearch({ rom, onPick }) {
  const t = useT();
  const [q, setQ] = useState(englishTerm(rom));
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState(null);
  const [err, setErr] = useState("");

  async function search() {
    const query = q.trim();
    if (!query || busy) return;
    setBusy(true); setErr(""); setResults(null);
    try {
      const d = await igdbSearch(query, rom.system_key);
      if (!d.available) setErr(t("IGDB 키가 설정되지 않았습니다"));
      setResults(d.results || []);
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="cover-search">
      <div className="field-label">{t("커버 검색 (IGDB)")}</div>
      <div className="rename-row">
        <input
          className="text-input"
          value={q}
          disabled={busy}
          spellCheck={false}
          placeholder={t("게임 이름")}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <button className="btn" disabled={busy || !q.trim()} onClick={search}>
          {busy ? <Loader size={13} className="spin" /> : <Search size={13} strokeWidth={2.5} />} {t("검색")}
        </button>
      </div>
      {err && <div className="badge failed">{err}</div>}
      {results && results.length === 0 && !busy && (
        <div className="muted">{t("검색 결과가 없습니다.")}</div>
      )}
      {results && results.length > 0 && (
        <div className="cover-results">
          {results.map((r) => (
            <button
              key={r.cover_url}
              className="cover-result"
              title={`${r.name}${r.year ? ` (${r.year})` : ""}`}
              onClick={() => onPick(r.cover_url)}
            >
              <img src={r.thumb_url} alt={r.name} loading="lazy" />
              <span className="cover-result-name">{r.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Each system pins ONE cover aspect so the firmware grid frame fits every cover
// (gui_draw_coverflow_v sizes the frame from one cover, centers the rest). Square
// for label art (homebrew apps, PICO-8 cart labels), 3:4 box art for everything.
const SQUARE_SYSTEMS = new Set(["homebrew", "pico8"]);
export function coverAspect(systemKey) {
  return SQUARE_SYSTEMS.has(systemKey) ? 1 : 3 / 4;   // 100×100 vs 75×100
}

// Crop to the system's FIXED aspect. The device crop-to-fills the cover to that
// exact size, so the live canvas (sized to the target) fills edge-to-edge.
function CoverCropper({ src, aspect = 3 / 4, busy, onCancel, onDone }) {
  const t = useT();
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const pctRef = useRef(null);   // croppedArea (percent) → backend fraction
  const pxRef = useRef(null);    // croppedAreaPixels → live device preview
  const canvasRef = useRef(null);
  const imgElRef = useRef(null);
  const canvasH = 100, canvasW = Math.round(canvasH * aspect);  // 75×100 or 100×100

  // Load the source once for the live device preview (display only → no CORS read).
  useEffect(() => {
    const im = new Image();
    im.onload = () => { imgElRef.current = im; drawPreview(); };
    im.src = src;
    return () => { imgElRef.current = null; };
  }, [src]);

  // Draw the cropped region FIT-WITHIN 186×100, centered (letterboxed) — exactly
  // how the device coverflow shows a cover at its own aspect.
  function drawPreview() {
    const cv = canvasRef.current, im = imgElRef.current, a = pxRef.current;
    if (!cv || !im || !a) return;
    const ctx = cv.getContext("2d");
    ctx.imageSmoothingQuality = "high";
    ctx.clearRect(0, 0, cv.width, cv.height);
    const scale = Math.min(cv.width / a.width, cv.height / a.height);
    const dw = a.width * scale, dh = a.height * scale;
    const dx = (cv.width - dw) / 2, dy = (cv.height - dh) / 2;
    try { ctx.drawImage(im, a.x, a.y, a.width, a.height, dx, dy, dw, dh); } catch (_) {}
  }

  const cropBox = () => {
    const a = pctRef.current;
    if (!a) return null;
    return { x: a.x / 100, y: a.y / 100, width: a.width / 100, height: a.height / 100 };
  };

  return (
    <div className="cropper">
      <div className="cropper-stage">
        <Cropper
          image={src}
          crop={crop}
          zoom={zoom}
          aspect={aspect}
          restrictPosition={false}
          onCropChange={setCrop}
          onZoomChange={setZoom}
          onCropComplete={(areaPct, areaPx) => { pctRef.current = areaPct; pxRef.current = areaPx; drawPreview(); }}
        />
      </div>
      <input
        className="cropper-zoom" type="range" min="1" max="3" step="0.01"
        value={zoom} onChange={(e) => setZoom(Number(e.target.value))} aria-label="zoom"
      />
      <div className="cropper-preview">
        <canvas ref={canvasRef} width={canvasW} height={canvasH} className="device-canvas"
          style={{ height: 168, width: Math.round(168 * aspect) }} aria-hidden />
        <span>{t("실기기 표시 (정확히 {w}×{h})", { w: canvasW, h: canvasH })}</span>
      </div>
      <div className="cropper-actions">
        <button className="btn ghost" disabled={busy} onClick={onCancel}>{t("취소")}</button>
        <button className="btn ghost" disabled={busy} onClick={() => onDone(null)}>{t("원본 전체")}</button>
        <button className="btn" disabled={busy} onClick={() => onDone(cropBox())}>
          {busy ? <Loader size={13} className="spin" /> : <Check size={13} strokeWidth={2.5} />} {t("이 영역")}
        </button>
      </div>
    </div>
  );
}

// Detail preview: the WEB high-res cover vs the ACTUAL device .img (186×100).
// The device side carries the crop control as an OVERLAY button on the image.
function CoverCompare({ rom, bust, onRecrop }) {
  const t = useT();
  if (rom.cover_status !== "ok") {
    return (
      <div className="cover-compare empty">
        <ImageOff size={18} aria-hidden /> {t("아직 커버가 없습니다. 아래에서 검색·업로드하거나 자동채우기를 쓰세요.")}
      </div>
    );
  }
  const v = bust ? `?v=${bust}` : "";
  const ar = coverAspect(rom.system_key) === 1 ? "1 / 1" : "3 / 4";
  return (
    <div className="cover-compare" style={{ "--cover-ar": ar }}>
      <figure>
        <span className="cmp-imgwrap">
          <img className="cmp-web" src={`${originalCoverUrl(rom.id)}${bust ? `&v=${bust}` : ""}`} alt={t("원본 전체")} />
          <a className="cmp-dl-overlay" href={coverDownloadUrl(rom.id, "original")} download
             title={t("원본 커버 다운로드")} onClick={(e) => e.stopPropagation()}>
            <Download size={12} strokeWidth={2.5} />
          </a>
        </span>
        <figcaption>{t("원본 (전체 모양)")}</figcaption>
      </figure>
      <figure>
        <span className="cmp-imgwrap">
          <img className="cmp-device" src={`${deviceCoverUrl(rom.id)}${bust ? `&v=${bust}` : ""}`} alt={t("기기 표시")} />
          <a className="cmp-dl-overlay" href={coverDownloadUrl(rom.id, "device")} download
             title={t("기기용 커버 다운로드")} onClick={(e) => e.stopPropagation()}>
            <Download size={12} strokeWidth={2.5} />
          </a>
          {onRecrop && (
            <button type="button" className="cmp-crop-overlay" onClick={onRecrop} title={t("기기 커버 위치 조정")}>
              <Crop size={12} strokeWidth={2.5} /> {t("위치 조정")}
            </button>
          )}
        </span>
        <figcaption>{t("실제 기기")} ({coverAspect(rom.system_key) === 1 ? "100×100" : "75×100"})</figcaption>
      </figure>
    </div>
  );
}

// "KO" = the game's CONTENT is Korean — a Korean release (Korea region) OR a
// Korean fan-translation (한글 patch / J-K / (K)/[K] tag). It reads the ORIGINAL
// upload name + stored name; our own Korean *display* title (e.g. "록맨") does NOT
// trigger it — only a real Korea/한글/J-K marker does.
const KO_RE = /한글|korea|\bJ-?K\b|[(\[]\s*K\s*[)\]]/i;
export function isKoreanPatched(rom) {
  // Scanned/auto/manual rows carry the authoritative DB flag (lang_source set);
  // un-scanned legacy rows fall back to the filename heuristic.
  if (rom.lang_source) return !!rom.is_korean_patched;
  return KO_RE.test(`${rom.original_name || ""}  ${rom.stored_name || ""}`);
}

// Language code → Korean label (for the rom edit modal).
const LANG_LABEL = {
  ja: "일본어", en: "영어", ko: "한국어", zh: "중국어",
  es: "스페인어", de: "독일어", fr: "프랑스어", it: "이탈리아어", unl: "비공식",
};
export function langLabel(code) {
  return code ? (LANG_LABEL[code] || code) : "?";
}

// Language/region code → ISO country code for the flag IMAGE. Emoji flags render
// as tofu boxes on Windows (and some Linux), so we ship small flag PNGs locally
// under /public/flags. 'unl'(비공식) has no flag. English → US, PAL/Europe → EU.
const LANG_CC = {
  ko: "kr", ja: "jp", en: "us", zh: "cn",
  es: "es", de: "de", fr: "fr", it: "it", eu: "eu",
};
export function langCC(code) {
  return code ? (LANG_CC[code] || "") : "";
}
export function langFlagUrl(code) {
  const cc = langCC(code);
  return cc ? `/flags/${cc}.png` : "";   // bundled locally — no external CDN
}

// Cover-flag (corner country icon) options for the rom edit modal. "" = no flag.
const FLAG_OPTIONS = [
  { code: "", label: "국기 없음" },
  { code: "ko", label: "한국" },
  { code: "ja", label: "일본" },
  { code: "en", label: "미국/영어" },
  { code: "zh", label: "중국" },
  { code: "es", label: "스페인" },
  { code: "de", label: "독일" },
  { code: "fr", label: "프랑스" },
  { code: "it", label: "이탈리아" },
  { code: "eu", label: "유럽(EU)" },
];

// ROM card: cover (click-to-upload) + name + per-card download + edit/delete popup.
export function RomCard({ rom, previewSrc, onChanged }) {
  const toast = useToast();
  const t = useT();
  const koreanMode = useKoreanMode();
  const { lang } = useI18n();
  // 한글패치 is Korea-specific → show only in Korean UI (Korean deploy + Korean lang).
  const koFeature = koreanMode && lang === "ko";
  // Homebrew cards can hold extra files (e.g. smw_assets.dat). The badge counts
  // only the real SD data files (.dat etc.) — .bin app payloads live in the
  // firmware and aren't shown.
  let extraFiles = [];
  try { extraFiles = JSON.parse(rom.extra_files || "[]"); } catch { extraFiles = []; }
  const dataFileCount = [rom.stored_name, ...extraFiles.map((f) => f.name)]
    .filter((n) => n && !n.toLowerCase().endsWith(".bin")).length;
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);
  const romFileRef = useRef(null);
  const dataFileRef = useRef(null);
  const [name, setName] = useState(rom.stored_name);
  const [nameErr, setNameErr] = useState("");
  const [coverV, setCoverV] = useState(0); // bumped on cover change → instant refresh
  const [cropper, setCropper] = useState(null); // { src, apply, revoke? }
  const [playing, setPlaying] = useState(false); // in-browser emulator overlay
  const dl = downloadRomUrl(rom.id);
  const title = rom.display_name || rom.korean_name || rom.stored_name;
  const runnable = canPlay(rom.system_key);

  async function launch() {
    if (isExperimental(rom.system_key)) {
      const ok = await toast.confirm(t("'{title}' 실행 (실험적 지원)", { title }), {
        detail: t("이 플랫폼은 브라우저 코어와 롬 형식이 다를 수 있어 정상 구동되지 않을 수 있어요. 그래도 실행할까요?"),
        confirmText: t("실행"),
      });
      if (!ok) return;
    }
    setOpen(false);
    setPlaying(true);
  }

  // a cover was (re)applied → reload the preview now, then refresh the library
  function coverChanged() { setCoverV(Date.now()); onChanged?.(); }

  function openModal() {
    setName(rom.stored_name);
    setNameErr("");
    setOpen(true);
  }
  // Picking a cover (IGDB or file) opens the crop step instead of applying直接.
  function pickIgdb(url) {
    setCropper({ src: url, apply: (box) => setCoverFromUrl(rom.id, url, box) });
  }
  // Re-crop the EXISTING cover (no re-download) — pick a region from the UNTOUCHED
  // full original (?full=1), not the cropped display, so it's freely re-adjustable.
  function reCrop() {
    setCropper({ src: `${originalCoverUrl(rom.id)}&v=${coverV || 1}`, apply: (box) => recropCover(rom.id, box) });
  }
  // Replace the ROM binary itself (keep name/cover/slot) — e.g. a better dump.
  async function replaceFile(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || busy) return;
    setBusy(true);
    try {
      await replaceRomFile(rom.id, file);
      toast.success(t("롬 파일을 교체했습니다"));
      onChanged?.();
    } catch (err) {
      toast.error(err.message || t("파일 교체 실패"));
    } finally {
      setBusy(false);
    }
  }
  function replaceCover(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const objUrl = URL.createObjectURL(file);
    setCropper({ src: objUrl, apply: (box) => uploadCover(rom.id, file, box), revoke: objUrl });
  }
  function closeCropper() {
    if (cropper?.revoke) URL.revokeObjectURL(cropper.revoke);
    setCropper(null);
  }
  async function applyCrop(box) {
    if (busy) return;
    setBusy(true);
    try { await cropper.apply(box); coverChanged(); closeCropper(); setOpen(false); toast.success(t("커버를 적용했습니다")); }
    catch (e) { toast.error(e.message || t("커버 적용 실패")); }
    finally { setBusy(false); }
  }
  async function rename() {
    const next = name.trim();
    if (busy || !next || next === rom.stored_name) { setOpen(false); return; }
    setBusy(true); setNameErr("");
    try { await renameRom(rom.id, next); onChanged?.(); setOpen(false); toast.success(t("파일명을 변경했습니다")); }
    catch (e) { setNameErr(e.message); toast.error(e.message); }
    finally { setBusy(false); }
  }
  async function removeCover() {
    if (busy) return;
    const ok = await toast.confirm(t("이 커버만 제거할까요?"), {
      detail: t("롬은 그대로 두고 커버(.img + 미리보기)만 지웁니다. 다시 채울 수 있어요."),
      confirmText: t("커버 제거"),
    });
    if (!ok) return;
    setBusy(true);
    try { await deleteCover(rom.id); coverChanged(); setOpen(false); toast.success(t("커버를 제거했습니다")); }
    catch (e) { toast.error(e.message || t("커버 제거 실패")); }
    finally { setBusy(false); }
  }
  async function remove() {
    if (busy) return;
    const ok = await toast.confirm(t("'{title}' 롬을 삭제할까요?", { title }), {
      detail: t("휴지통(_trash)으로 이동합니다 — 복구할 수 있습니다."),
      confirmText: t("삭제(휴지통)"),
      danger: true,
    });
    if (!ok) return;
    setBusy(true);
    try { await deleteRom(rom.id); onChanged?.(); setOpen(false); toast.success(t("휴지통으로 이동했습니다")); }
    catch (e) { toast.error(e.message || t("삭제 실패")); }
    finally { setBusy(false); }
  }

  const koPatched = isKoreanPatched(rom);

  // Manually flip the 한글패치 flag (protected from future auto-scans). Used by the
  // corner badge (turn OFF) and the modal toggle (either direction).
  async function togglePatch() {
    if (busy) return;
    setBusy(true);
    try {
      await setRomLang(rom.id, !koPatched);
      onChanged?.();
      toast.success(!koPatched ? t("한글패치로 표시했습니다") : t("한글패치 표시를 해제했습니다"));
    } catch (e) { toast.error(e.message || t("변경 실패")); }
    finally { setBusy(false); }
  }

  // Pick the cover's corner flag/country explicitly (independent of 한글패치).
  async function changeFlag(code) {
    if (busy) return;
    setBusy(true);
    try {
      await setCoverFlag(rom.id, code);
      coverChanged();   // re-bake done server-side → bust cover + refresh
      toast.success(code ? t("국기를 변경했습니다") : t("국기를 제거했습니다"));
    } catch (e) { toast.error(e.message || t("국기 변경 실패")); }
    finally { setBusy(false); }
  }

  // Homebrew only: opt this ROM file into the SD ZIP (default = cover only).
  async function changeSdInclude(include) {
    if (busy) return;
    setBusy(true);
    try {
      await setSdInclude(rom.id, include);
      onChanged?.();
    } catch (e) { toast.error(e.message || t("변경 실패")); }
    finally { setBusy(false); }
  }

  // Add/replace a data file on the card (e.g. smw_assets.dat). Same name = replace.
  async function addFile(e) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f || busy) return;
    setBusy(true);
    try { await addRomFile(rom.id, f); onChanged?.(); toast.success(t("파일을 추가했습니다")); }
    catch (err) { toast.error(err.message || t("파일 추가 실패")); }
    finally { setBusy(false); }
  }
  async function removeFile(name) {
    if (busy) return;
    setBusy(true);
    try { await deleteRomFile(rom.id, name); onChanged?.(); toast.success(t("파일을 삭제했습니다")); }
    catch (err) { toast.error(err.message || t("파일 삭제 실패")); }
    finally { setBusy(false); }
  }

  // Cover-state badge, pinned to the cover's bottom-right corner:
  // crop = hand-cropped for the device (original kept) · hand = manually uploaded
  // · image-off = no cover. Auto cover shows nothing.
  const statusBadge =
    rom.cover_status === "ok" && rom.cover_source === "crop" ? (
      <span className="cover-crop" title={t("기기용으로 직접 크롭함 (원본 유지)")}>
        <Crop size={12} strokeWidth={2.5} aria-hidden />
      </span>
    ) : rom.cover_status === "ok" && rom.cover_source === "manual" ? (
      <span className="cover-manual" title={t("직접 넣은 커버 (자동 덮어쓰기 안 함)")}>
        <Hand size={12} strokeWidth={2.5} aria-hidden />
      </span>
    ) : rom.cover_status !== "ok" ? (
      <span className="no-cover" title={t("커버 없음")}><ImageOff size={12} strokeWidth={2.5} aria-hidden /></span>
    ) : null;

  return (
    <div className="card" style={{ borderTopColor: systemColor(rom.system_key) }}>
      <CoverSlot romId={rom.id} src={previewSrc} bust={coverV} alt={title}
        aspect={coverAspect(rom.system_key)} onActivate={openModal} badge={statusBadge}
        status={rom.cover_status}
        overlay={rom.system_key ? <SystemIcon dirname={rom.system_key} size={14} /> : null} />
      <div className="name">
        {title}
        {rom.system_key === "homebrew" && dataFileCount > 0 && (
          <span className="file-count" title={t("파일 {n}개", { n: dataFileCount })}>{dataFileCount}</span>
        )}
      </div>
      <div className="card-actions">
        {dl && (
          <a className="icon-btn" href={dl} download title={t("다운로드 (롬+커버)")}>
            <Download size={13} strokeWidth={2.5} />
          </a>
        )}
        <button className="icon-btn" onClick={openModal} title={t("수정/삭제")}>
          <MoreHorizontal size={13} strokeWidth={2.5} />
        </button>
        {/* ▶ play sits at the FAR RIGHT so download/edit keep a fixed position on
           every card, whether or not the system is browser-playable. */}
        {runnable && (
          <button className="icon-btn play-btn" onClick={launch}
            title={isExperimental(rom.system_key) ? t("웹에서 실행 (실험적)") : t("웹에서 실행")}>
            <Play size={13} strokeWidth={2.5} />
          </button>
        )}
      </div>

      {open && (
        <Modal title={title} onClose={() => { closeCropper(); setOpen(false); }}>
          {cropper ? (
            <CoverCropper src={cropper.src} aspect={coverAspect(rom.system_key)} busy={busy} onCancel={closeCropper} onDone={applyCrop} />
          ) : (
            <>
              <CoverCompare rom={rom} bust={coverV} onRecrop={rom.cover_status === "ok" ? reCrop : null} />

              {/* Homebrew entries are fixed firmware launch templates — the .bin
                  name must stay exact, so no rename field (managed via file list). */}
              {rom.system_key !== "homebrew" && (
                <>
                  <label className="field-label">{t("파일명 (확장자 포함)")}</label>
                  <div className="rename-row">
                    {rom.system_key && <span className="path-prefix">/roms/{rom.system_key}/</span>}
                    <input
                      className="text-input"
                      value={name}
                      disabled={busy}
                      spellCheck={false}
                      onChange={(e) => setName(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && rename()}
                    />
                    <button className="btn" disabled={busy || !name.trim() || name.trim() === rom.stored_name} onClick={rename}>
                      <Pencil size={13} strokeWidth={2.5} /> {t("변경")}
                    </button>
                  </div>
                  {nameErr && <div className="badge failed">{nameErr}</div>}
                </>
              )}

              {koFeature && (
                <div className="lang-row">
                  <label className="lang-toggle" title={t("이 롬이 한글패치 적용판인지 표시합니다 (자동 감지값을 직접 덮어씁니다)")}>
                    <input type="checkbox" checked={koPatched} disabled={busy} onChange={togglePatch} />
                    <span>{t("한글패치")}</span>
                  </label>
                  <span className="lang-info">
                    {t("언어")}: {t(langLabel(rom.orig_lang))}{rom.play_lang && rom.play_lang !== rom.orig_lang ? ` → ${t(langLabel(rom.play_lang))}` : ""}
                    {rom.lang_source === "manual" && <span className="lang-manual" title={t("직접 지정함")}> {t("(수동)")}</span>}
                  </span>
                </div>
              )}

              <div className="lang-row">
                <label className="flag-select" title={t("커버 우측상단에 표시할 국기를 직접 선택합니다 (한글패치와 별개)")}>
                  {rom.cover_flag
                    ? <img className="flag-preview" src={langFlagUrl(rom.cover_flag)} alt="" />
                    : <Flag size={14} strokeWidth={2.5} aria-hidden />}
                  <span>{t("국기")}</span>
                  <select className="text-input" value={rom.cover_flag || ""} disabled={busy}
                    onChange={(e) => changeFlag(e.target.value)}>
                    {FLAG_OPTIONS.map((o) => <option key={o.code} value={o.code}>{t(o.label)}</option>)}
                  </select>
                </label>
              </div>

              {rom.system_key === "homebrew" && (
                <div className="file-list">
                  <label className="field-label">{t("파일 ({n}개)", { n: dataFileCount })}</label>
                  <ul className="files">
                    <li className="file-row">
                      <span className="file-name">{rom.stored_name}</span>
                      <span className="file-tag" title={t("이 파일은 펌웨어에 내장된 실행 항목이라 수정·다운로드되지 않습니다")}>{t("템플릿")}</span>
                    </li>
                    {extraFiles.map((f) => (
                      <li className="file-row" key={f.name}>
                        <span className="file-name">{f.name}</span>
                        <span className="file-size">{formatBytes(f.size)}</span>
                        <button className="icon-btn" disabled={busy} onClick={() => removeFile(f.name)} title={t("삭제")}>
                          <Trash2 size={12} strokeWidth={2.5} />
                        </button>
                      </li>
                    ))}
                  </ul>
                  <button className="btn ghost" disabled={busy} onClick={() => dataFileRef.current?.click()}
                    title={t("데이터 파일(.dat 등)을 추가하거나, 같은 이름으로 올리면 교체됩니다")}>
                    <Upload size={13} strokeWidth={2.5} /> {t("데이터 파일 추가/교체")}
                  </button>
                  <input ref={dataFileRef} type="file" hidden onChange={addFile} />
                </div>
              )}

              <div className="modal-actions">
                {runnable && (
                  <button className="btn play" disabled={busy} onClick={launch}
                    title={isExperimental(rom.system_key) ? t("브라우저에서 바로 실행 (실험적 지원)") : t("브라우저에서 바로 실행")}>
                    <Play size={13} strokeWidth={2.5} /> {t("웹에서 실행")}
                  </button>
                )}
                {rom.system_key !== "homebrew" && (
                  <button className="btn ghost" disabled={busy} onClick={() => romFileRef.current?.click()}
                    title={t("롬 파일 자체를 다른 파일로 교체 (이름·커버 유지)")}>
                    <Upload size={13} strokeWidth={2.5} /> {t("롬 파일 교체")}
                  </button>
                )}
                {dl && (
                  <a className="btn ghost" href={dl} download title={t("롬+커버 ZIP 받기")}>
                    <Download size={13} strokeWidth={2.5} /> {t("롬 다운로드")}
                  </a>
                )}
              </div>
              <input ref={romFileRef} type="file" hidden onChange={replaceFile} />

              <CoverSearch rom={rom} onPick={pickIgdb} />

              <div className="modal-actions">
                <button className="btn" disabled={busy} onClick={() => fileRef.current?.click()}>
                  <ImagePlus size={13} strokeWidth={2.5} /> {t("업로드")}
                </button>
                <button className="btn ghost" disabled={busy} onClick={removeCover}>
                  <ImageOff size={13} strokeWidth={2.5} /> {t("커버 제거")}
                </button>
                <button className="btn danger" disabled={busy} onClick={remove}>
                  <Trash2 size={13} strokeWidth={2.5} /> {t("삭제")}
                </button>
              </div>
              <input ref={fileRef} type="file" accept="image/*" hidden onChange={replaceCover} />
            </>
          )}
        </Modal>
      )}

      {playing && <EmulatorOverlay rom={rom} onClose={() => setPlaying(false)} />}
    </div>
  );
}

// Music card: name + inline MP3 player + download + delete.
// Music library — one sticky player up top, a clickable track list below (a track
// row → loads + plays in that single player). Music app style, not per-card players.
export function MusicList({ tracks, onChanged }) {
  const toast = useToast();
  const t = useT();
  const [curId, setCurId] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const cur = tracks.find((tr) => tr.id === curId);

  async function remove(track, e) {
    e.stopPropagation();
    if (busyId) return;
    if (!(await toast.confirm(t("'{name}' 삭제할까요?", { name: track.original_name || track.stored_name }), { confirmText: t("삭제") }))) return;
    setBusyId(track.id);
    try {
      await deleteMusic(track.id);
      if (curId === track.id) setCurId(null);
      onChanged?.();
    } catch (err) { toast.error(err.message); } finally { setBusyId(null); }
  }

  return (
    <div className="music-lib">
      <div className="music-bar">
        <div className="music-now">
          <Music size={13} strokeWidth={2.5} aria-hidden />
          <span>{cur ? (cur.original_name || cur.stored_name) : t("트랙을 누르면 재생됩니다")}</span>
        </div>
        {/* key reloads the element on track change → autoplay the picked track.
            stream endpoint (not download) so the scrubber/seek works. */}
        <audio key={cur?.id || "none"} className="music-audio" controls autoPlay
          src={cur ? streamMusicUrl(cur.id) : undefined} />
      </div>
      <div className="music-list">
        {tracks.map((tr) => (
          <div key={tr.id} className={`music-row ${tr.id === curId ? "on" : ""}`} onClick={() => setCurId(tr.id)}>
            <span className="music-row-thumb">
              <Music size={13} strokeWidth={2.5} aria-hidden />
              <img src={musicCoverUrl(tr.id)} alt="" loading="lazy"
                onError={(e) => { e.currentTarget.style.display = "none"; }} />
            </span>
            {tr.id === curId
              ? <span className="music-row-icon playing"><Play size={11} strokeWidth={3} aria-hidden /></span>
              : <span className="music-row-icon"><Play size={11} strokeWidth={2.5} aria-hidden /></span>}
            <span className="music-row-name" title={tr.original_name || tr.stored_name}>{tr.original_name || tr.stored_name}</span>
            {tr.size_bytes != null && <span className="music-row-size">{formatBytes(tr.size_bytes)}</span>}
            <a className="icon-btn" href={downloadMusicUrl(tr.id)} download title={t("다운로드")} onClick={(e) => e.stopPropagation()}>
              <Download size={12} strokeWidth={2.5} />
            </a>
            <button className="icon-btn danger" disabled={busyId === tr.id} title={t("삭제")} onClick={(e) => remove(tr, e)}>
              <Trash2 size={12} strokeWidth={2.5} />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

// Video card — YouTube-style: 16:9 thumbnail with an inline player, title, and a
// ⋯ detail modal (format + delete). Plays the browser .mp4 preview, not the .avi.
export function VideoCard({ video, onChanged }) {
  const toast = useToast();
  const t = useT();
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [playing, setPlaying] = useState(false);   // load the <video> only on click
  const dl = downloadVideoUrl(video.id);
  const prev = videoPreviewUrl(video.id);
  const thumb = videoThumbUrl(video.id);
  const title = video.original_name || video.avi_name;

  async function remove() {
    if (busy) return;
    if (!(await toast.confirm(t("'{title}' 삭제할까요?", { title }), { confirmText: t("삭제") }))) return;
    setBusy(true);
    try { await deleteVideo(video.id); onChanged?.(); }
    catch (e) { toast.error(e.message); } finally { setBusy(false); }
  }

  return (
    <div className="media-card">
      <div className="media-thumb">
        {playing
          ? <video className="media-player" controls autoPlay src={prev} />
          : (
            <button type="button" className="media-thumb-btn" onClick={() => setPlaying(true)} aria-label={t("재생")}>
              <img className="media-cover" src={thumb} alt="" loading="lazy" />
              <span className="media-play"><Play size={30} strokeWidth={2.5} aria-hidden /></span>
            </button>
          )}
        <span className="media-kind"><Film size={11} strokeWidth={2.5} aria-hidden /> {t("영상")}</span>
      </div>
      <div className="media-meta">
        <div className="media-title" title={title}>{title}</div>
        <div className="media-actions">
          <button className="icon-btn" onClick={() => setOpen(true)} title={t("상세")}><MoreHorizontal size={13} strokeWidth={2.5} /></button>
          {dl && <a className="icon-btn" href={dl} download title={t("다운로드 (.avi)")}><Download size={13} strokeWidth={2.5} /></a>}
          <button className="icon-btn danger" onClick={remove} disabled={busy} title={t("삭제")}><Trash2 size={13} strokeWidth={2.5} /></button>
        </div>
      </div>
      {open && (
        <Modal title={title} onClose={() => setOpen(false)}>
          <video className="media-detail-player" controls autoPlay poster={thumb} src={prev} />
          <dl className="media-detail-info">
            <dt>{t("원본")}</dt><dd>{video.original_name || "—"}</dd>
            <dt>{t("기기 파일")}</dt><dd>{video.avi_name}</dd>
            <dt>{t("포맷")}</dt><dd>{t("MJPEG · AVI · 320px · 30fps · mono (기기용)")}</dd>
            <dt>{t("용량")}</dt><dd>{video.size_bytes != null ? formatBytes(video.size_bytes) : "—"}</dd>
          </dl>
          <div className="modal-actions">
            {dl && <a className="btn ghost" href={dl} download><Download size={13} strokeWidth={2.5} /> {t("다운로드 (.avi)")}</a>}
            <button className="btn danger" onClick={() => { setOpen(false); remove(); }}><Trash2 size={13} strokeWidth={2.5} /> {t("삭제")}</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
