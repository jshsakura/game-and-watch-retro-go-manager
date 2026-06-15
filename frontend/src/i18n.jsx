import React, { createContext, useContext, useEffect, useState } from "react";
import { EN } from "./i18n.dict.js";

// UI language. Korean is the source language (strings live in code as Korean and
// are used as the lookup key); English comes from the EN dictionary. Default
// follows the browser, overridable by the header switcher (persisted).
const LANG_KEY = "gnw_lang";

function browserDefault() {
  const n = (navigator.language || navigator.userLanguage || "en").toLowerCase();
  return n.startsWith("ko") ? "ko" : "en";
}

// Fallback language is English: a non-Korean browser, or any undetermined case,
// resolves to "en".
const I18nContext = createContext({ lang: "en", setLang: () => {}, t: (s) => s });

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem(LANG_KEY) || browserDefault());
  useEffect(() => {
    localStorage.setItem(LANG_KEY, lang);
    document.documentElement.setAttribute("lang", lang);
  }, [lang]);
  // t(ko[, vars]): ko → return source; en → EN map (fallback to ko). Supports
  // {name}-style placeholders: t("총 {n}개", {n: 5}).
  const t = (ko, vars) => {
    let s = lang === "en" ? (EN[ko] ?? ko) : ko;
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
