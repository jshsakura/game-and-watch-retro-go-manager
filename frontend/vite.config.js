import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Frontend dev server on 38081, API proxied to 38080.
// VITE_DEMO=1 builds the static GitHub Pages preview: served from a project
// subpath, so assets need the matching base. The live app stays at root "/".
export default defineConfig({
  base: process.env.VITE_DEMO ? "/game-and-what/" : "/",
  plugins: [react()],
  // Don't pre-bundle ffmpeg.wasm: its internal classWorker is located via
  // import.meta.url, which breaks when Vite rewrites the module into deps/ —
  // the worker then never loads and load() hangs. Excluded = raw ESM, URL resolves.
  optimizeDeps: { exclude: ["@ffmpeg/ffmpeg", "@ffmpeg/util"] },
  server: {
    port: 38081,
    host: true,            // listen on 0.0.0.0 — reachable via Tailscale IP
    allowedHosts: true,    // allow Tailscale hostname/IP Host headers
    // Cross-origin isolation → SharedArrayBuffer for the ffmpeg.wasm MT core.
    // credentialless so cross-origin cover-search <img> still load.
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "credentialless",
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:38080",
        changeOrigin: true,
      },
    },
  },
});
