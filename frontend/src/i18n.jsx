import React, { createContext, useContext, useEffect, useState } from "react";
import EN from "./locales/en.js";
import {
  SOURCE_LOCALE,
  DEFAULT_LOCALE,
  isLocale,
  resolveBrowserLocale,
} from "./i18n.locales.js";

// UI language. Korean is the SOURCE language: in-code strings are Korean and used
// directly as the lookup key. English is the fallback UI language and ships in the
// main bundle (no flash, always available). The remaining locales are lazily
// imported as separate chunks so the initial download stays small on mobile.
const LANG_KEY = "gnw_lang";

// Loaded dictionaries by locale. Korean carries no dictionary (it IS the source);
// English is preloaded. Others populate on first use.
const dictCache = { [SOURCE_LOCALE]: {}, en: EN };

function loadDict(code) {
  if (dictCache[code]) return Promise.resolve(dictCache[code]);
  // Vite bundles each ./locales/*.js as its own chunk for this dynamic import.
  return import(`./locales/${code}.js`)
    .then((m) => (dictCache[code] = m.default || {}))
    .catch(() => (dictCache[code] = {})); // missing/broken dict → full Korean fallback
}

// CJK / Cyrillic web font lazy loader. Only runs for locales that need extra
// glyphs not covered by the bundled Noto Sans KR. Each import() becomes its own
// Vite asset chunk so the initial bundle stays small on mobile.
const fontLoaded = new Set();
function loadFont(code) {
  if (fontLoaded.has(code)) return;
  fontLoaded.add(code);
  const imports = {
    ja:    () => import("@fontsource/noto-sans-jp/japanese-400.css"),
    "zh-CN": () => import("@fontsource/noto-sans-sc/chinese-simplified-400.css"),
    "zh-TW": () => import("@fontsource/noto-sans-tc/chinese-traditional-400.css"),
    ru:    () => import("@fontsource/noto-sans/cyrillic-400.css"),
  };
  if (imports[code]) imports[code]().catch(() => {}); // font failure must not break the app
}

function initialLang() {
  const saved = localStorage.getItem(LANG_KEY);
  if (saved && isLocale(saved)) return saved;
  return resolveBrowserLocale(navigator.language || navigator.userLanguage);
}

const I18nContext = createContext({
  lang: DEFAULT_LOCALE,
  setLang: () => {},
  t: (s) => s,
});

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(initialLang);
  // Active locale's dictionary; the cache hit (ko/en) avoids a first-paint flash.
  const [dict, setDict] = useState(() => dictCache[lang] || null);

  useEffect(() => {
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.setAttribute("lang", lang);
    loadFont(lang); // lazy-load CJK/Cyrillic web font for this locale (no-op for others)
    let cancelled = false;
    loadDict(lang).then((d) => {
      if (!cancelled) setDict(d);
    });
    return () => {
      cancelled = true;
    };
  }, [lang]);

  const setLang = (code) => {
    if (isLocale(code)) setLangState(code);
  };

  // t(ko[, vars]): the Korean source string is the key. Resolution order for a
  // non-Korean locale: that locale's translation → English → Korean source.
  // English is the universal fallback (always bundled), so an untranslated or
  // still-loading locale shows English rather than Korean. Supports {name}-style
  // placeholders: t("총 {n}개", {n: 5}).
  const t = (ko, vars) => {
    let s = ko; // source locale (ko) and ultimate fallback
    if (lang !== SOURCE_LOCALE) {
      s = (dict && dict[ko]) || EN[ko] || ko; // "" = untranslated → English
    }
    if (vars) for (const k in vars) s = s.replaceAll(`{${k}}`, vars[k]);
    return s;
  };

  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}

// Convenience hook: const t = useT();  →  t("문자열")
export function useT() {
  return useContext(I18nContext).t;
}
