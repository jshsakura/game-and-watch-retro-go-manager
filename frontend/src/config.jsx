import React, { createContext, useContext, useEffect, useState } from "react";
import { getConfig } from "./api.js";

// Runtime feature flags from GET /api/config. korean_mode gates the
// Korea-specific UI (한글패치 toggle, Korean-name resolve/gamelist, 한글명 누락
// 필터). Defaults to false until loaded so non-Korean is the safe default.
const ConfigContext = createContext({ korean_mode: false });

export function ConfigProvider({ children }) {
  const [config, setConfig] = useState({ korean_mode: false });
  useEffect(() => {
    let alive = true;
    getConfig().then((c) => { if (alive) setConfig(c); });
    return () => { alive = false; };
  }, []);
  return <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>;
}

export function useConfig() {
  return useContext(ConfigContext);
}

// Convenience: the Korea-specific feature flag.
export function useKoreanMode() {
  return !!useContext(ConfigContext).korean_mode;
}
