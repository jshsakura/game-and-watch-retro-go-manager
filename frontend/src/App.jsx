import React, { useEffect, useMemo, useState } from "react";
import RomTab from "./tabs/RomTab.jsx";
import ExtraTab from "./tabs/ExtraTab.jsx";
import MediaTab from "./tabs/MediaTab.jsx";
import LibraryTab from "./tabs/LibraryTab.jsx";
import DataTab from "./tabs/DataTab.jsx";
import HelpTab from "./tabs/HelpTab.jsx";
import { Upload, Clapperboard, Library, Download, Database, Info, Check, X, HardDrive } from "lucide-react";
import { getLibrary, packageUrl, packageSize, formatBytes } from "./api.js";
import { useDownload } from "./download.jsx";
import { useT, useI18n } from "./i18n.jsx";

const THEME_KEY = "gnw_theme";

// Edition mark — swaps with the theme (CSS hides the inactive one).
const TABS = [
  // Primary: LIBRARY (default landing) + UPLOAD. Secondary (gray): MEDIA + DATA + HELP.
  // MEDIA merges the old VIDEO + MUSIC converters into one tab.
  { key: "library", label: "LIBRARY", Icon: Library },
  { key: "rom", label: "UPLOAD", Icon: Upload },
  { key: "extra", label: "EXTRA", Icon: HardDrive },
  { key: "media", label: "MEDIA", Icon: Clapperboard, secondary: true, media: true },
  { key: "data", label: "DATA", Icon: Database, secondary: true, data: true },
  { key: "help", label: "INFO", Icon: Info, secondary: true, help: true },
];

// 8-bit pixel heart (Zelda life heart) — used as the toggle knob.
const HEART_ROWS = ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000"];
function PixelHeart({ size = 14 }) {
  return (
    <svg className="pixheart" width={size} height={size} viewBox="0 0 7 6" shapeRendering="crispEdges" aria-hidden>
      {HEART_ROWS.flatMap((row, y) =>
        row.split("").map((c, x) =>
          c === "1" ? <rect key={`${x}-${y}`} x={x} y={y} width="1" height="1" /> : null
        )
      )}
    </svg>
  );
}

// Edition toggle — simple left/right on-off switch; background colour is the
// edition (Zelda green / Mario red), knob is an 8-bit heart.
function ThemeToggle({ theme, onToggle }) {
  const t = useT();
  const isMario = theme === "mario";
  return (
    <button
      type="button"
      role="switch"
      aria-checked={isMario}
      className={`theme-switch ${isMario ? "mario" : "zelda"}`}
      onClick={onToggle}
      title={t("에디션: {ed} · 클릭해 전환", { ed: isMario ? "Mario" : "Zelda" })}
    >
      <span className="theme-switch-knob"><PixelHeart size={14} /></span>
    </button>
  );
}

// UI language toggle (KO ↔ EN), shown as the current language's flag, in the
// header next to the edition toggle.
function LangToggle() {
  const { lang, setLang } = useI18n();
  const isKo = lang === "ko";
  return (
    <button
      type="button"
      className="lang-switch"
      onClick={() => setLang(isKo ? "en" : "ko")}
      title={isKo ? "언어: 한국어 · 클릭해 English로" : "Language: English · click for 한국어"}
      aria-label="language"
    >
      <img src={`/flags/${isKo ? "kr" : "us"}.png`} alt={isKo ? "한국어" : "English"} />
    </button>
  );
}

export default function App() {
  const t = useT();
  const [theme, setTheme] = useState(() => localStorage.getItem(THEME_KEY) || "zelda");
  const [tab, setTab] = useState("library");
  const [reloadKey, setReloadKey] = useState(0);
  const [count, setCount] = useState(0);
  const [sdSize, setSdSize] = useState(null);
  const [libKeys, setLibKeys] = useState([]);        // system keys that have roms (selectable)
  const [selected, setSelected] = useState(() => new Set()); // checked systems for download
  const [selSize, setSelSize] = useState(null);
  const dl = useDownload();

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    getLibrary()
      .then((l) => {
        setCount(l.roms.length + l.videos.length + (l.music?.length || 0));
        setLibKeys([...new Set(l.roms.map((r) => r.system_key))].sort());
      })
      .catch(() => { setCount(0); setLibKeys([]); });
    packageSize().then(setSdSize).catch(() => setSdSize(null));
  }, [reloadKey]);

  // Download selection (system key == dirname). 전체 선택 + 다운로드 live together top-right.
  const toggleSel = (key) => setSelected((s) => {
    const n = new Set(s); n.has(key) ? n.delete(key) : n.add(key); return n;
  });
  const selectedDirs = useMemo(() => libKeys.filter((k) => selected.has(k)), [libKeys, selected]);
  const allSelected = libKeys.length > 0 && libKeys.every((k) => selected.has(k));
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(libKeys));
  const selKey = selectedDirs.join(",");
  const hasSel = selectedDirs.length > 0;

  // Size of the checked-systems selection (for the top-right download button).
  useEffect(() => {
    let alive = true; setSelSize(null);
    if (selKey) packageSize(selKey).then((b) => alive && setSelSize(b)).catch(() => {});
    return () => { alive = false; };
  }, [selKey, reloadKey]);

  const bumpLibrary = () => setReloadKey((k) => k + 1);
  const zip = packageUrl();

  const toggleTheme = () => setTheme((t) => (t === "mario" ? "zelda" : "mario"));

  return (
    <div className="app">
      <header className="topbar">
        <div
          className="brand-id"
          role="button"
          tabIndex={0}
          title={t("메인으로")}
          onClick={() => setTab("library")}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setTab("library"); } }}
        >
          <div>
            <h1>GAME &amp; WATCH</h1>
            <small>Retro-Go SD Manager</small>
          </div>
        </div>
        <div className="topbar-actions">
          <LangToggle />
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>
      </header>

      <div className="tabbar">
        <nav className="tabs">
          {TABS.map((t, i) => (
            <React.Fragment key={t.key}>
              {t.secondary && !TABS[i - 1]?.secondary && <span className="tab-divider" aria-hidden />}
              <button
                className={`tab ${tab === t.key ? "active" : ""} ${t.secondary ? "tab-secondary" : ""} ${t.media ? "tab-media" : ""} ${t.help ? "tab-help" : ""} ${t.data ? "tab-data" : ""}`}
                onClick={() => setTab(t.key)}
                title={t.label}
              >
                <t.Icon size={15} strokeWidth={2.5} aria-hidden /> {t.label}
              </button>
            </React.Fragment>
          ))}
        </nav>
        {count > 0 && (
          <div className="tabbar-dl">
            {tab === "library" && libKeys.length > 0 && (
              <button className={`btn tab-selall ${allSelected ? "on" : ""}`} onClick={toggleAll} title={t("모든 플랫폼 선택 / 해제")}>
                {allSelected
                  ? <><X size={14} strokeWidth={3} aria-hidden /> ALL</>
                  : <><Check size={14} strokeWidth={3} aria-hidden /> ALL</>}
              </button>
            )}
            <button className="btn tab-dl has-size" disabled={!hasSel || dl.busy}
              onClick={() => dl.download(
                allSelected ? zip : packageUrl(selKey),
                allSelected ? "gnw-sd.zip" : "gnw-sd-selected.zip",
                (allSelected ? sdSize : selSize) || 0,
              )}
              title={hasSel ? (allSelected ? t("전체 SD(펌웨어·바이오스 포함) ZIP으로 받기") : t("체크한 플랫폼을 SD ZIP으로 받기")) : t("플랫폼을 체크(또는 전체 선택)하면 받을 수 있어요")}>
              <Download size={14} strokeWidth={2.5} aria-hidden /> SD ZIP
              {hasSel && (
                <span className="size-tag">{(allSelected ? sdSize : selSize) != null ? formatBytes(allSelected ? sdSize : selSize) : "…"}</span>
              )}
            </button>
          </div>
        )}
      </div>

      <div className="device">
        <div className="lcd">
          {tab === "rom" && <RomTab onChanged={bumpLibrary} />}
          {tab === "extra" && <ExtraTab onChanged={bumpLibrary} />}
          {tab === "media" && <MediaTab onChanged={bumpLibrary} />}
          {tab === "library" && <LibraryTab reloadKey={reloadKey} onChanged={bumpLibrary} selected={selected} onToggleSel={toggleSel} />}
          {tab === "data" && <DataTab onChanged={bumpLibrary} />}
          {tab === "help" && <HelpTab />}
        </div>
      </div>
    </div>
  );
}
