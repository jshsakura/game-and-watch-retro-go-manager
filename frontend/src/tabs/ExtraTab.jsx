import React, { useEffect, useState } from "react";
import { FolderPlus, Upload, Download, Trash2 } from "lucide-react";
import { getExtra, uploadExtra, deleteExtra, extraDownloadUrl, formatBytes } from "../api.js";
import { Dropzone } from "../components.jsx";
import { useToast } from "../toast.jsx";
import { useT } from "../i18n.jsx";
import { BIOS_CATALOG } from "../bios.js";

// Distinct BIOS target folders (bios/nes, bios/coleco, …) derived from the shared
// catalog — offered as one-click example chips so users don't guess the path.
const BIOS_FOLDERS = [
  ...new Set(BIOS_CATALOG.flatMap((b) => b.files.map((f) => f.sdPath.replace(/\/[^/]+$/, "")))),
];

// Arbitrary passthrough files → SD root verbatim. Pick a target folder (e.g.
// bios/nes) and the files land at <folder>/<name> in the SD ZIP.
export default function ExtraTab({ onChanged }) {
  const toast = useToast();
  const t = useT();
  const [folder, setFolder] = useState("");
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  const reload = () => {
    setLoading(true);
    return getExtra().then((d) => setFiles(d.files)).catch(() => setFiles([])).finally(() => setLoading(false));
  };
  useEffect(() => { reload(); }, []);

  async function handleFiles(list, onProgress) {
    const arr = Array.from(list);
    if (!arr.length) return;
    const total = arr.reduce((s, f) => s + f.size, 0) || 1;
    let done = 0;
    for (const f of arr) {
      const rel = (f.webkitRelativePath || f.name).replace(/^\/+/, "");
      const path = dir ? `${dir}/${rel}` : rel;
      try {
        await uploadExtra(f, path, (loaded) => onProgress?.(done + loaded, total));
      } catch (e) {
        toast.error(`${f.name}: ${e.message}`);
      }
      done += f.size;
    }
    await reload();
    onChanged?.();
  }

  const dir = folder.replace(/^\/+|\/+$/g, "");   // trimmed folder; empty = SD root

  async function remove(path) {
    if (!(await toast.confirm(t("Delete the file '/{path}'?", { path }), { confirmText: t("Delete") }))) return;
    try { await deleteExtra(path); await reload(); onChanged?.(); }
    catch (e) { toast.error(e.message); }
  }

  return (
    <div className="stack">
      <div className="muted">
        <FolderPlus size={13} aria-hidden /> {t("Upload passthrough files — BIOS / system ROMs, configs, anything. Set the target SD folder and the file ships in the SD ZIP verbatim at that path. See the BIOS list in the INFO (정보) tab for each system's exact path.")}
      </div>

      <label className="field-label">{t("Target folder (SD path)")}</label>
      <div className="path-group">
        <span className="path-group-tag"><FolderPlus size={13} strokeWidth={2.5} aria-hidden /> SD</span>
        <span className="path-slash">/</span>
        <input
          className="path-input"
          value={folder}
          spellCheck={false}
          placeholder={t("e.g. bios/nes — leave empty for the SD root")}
          onChange={(e) => setFolder(e.target.value)}
        />
        <span className="path-trail">/…</span>
      </div>
      <div className="extra-examples">
        <span className="extra-examples-label">{t("BIOS folders:")}</span>
        {BIOS_FOLDERS.map((f) => (
          <button
            type="button"
            key={f}
            className={`extra-chip ${dir === f ? "on" : ""}`}
            onClick={() => setFolder(f)}
          >
            {f}
          </button>
        ))}
      </div>
      <div className="muted path-hint">{t("Leave empty to save to the SD root.")}</div>

      <Dropzone
        multiple
        label={
          <span className="dz-label">
            <Upload size={16} aria-hidden /> {t("Drag & drop files or click →")}{" "}
            {dir ? <b>/{dir}/</b> : <b>{t("the SD root")}</b>}{" "}
            {t("to save")}
          </span>
        }
        onFiles={handleFiles}
      />

      {loading ? (
        <div className="data-list">
          {Array.from({ length: 5 }).map((_, i) => (
            <div className="skel-row" key={i}>
              <div className="skel-line fill" />
              <div className="skel-line w-sm" />
              <div className="skel-line w-icon" />
              <div className="skel-line w-icon" />
            </div>
          ))}
        </div>
      ) : files.length === 0 ? (
        <div className="muted">{t("No files uploaded (not included in SD).")}</div>
      ) : (
        <div className="data-list">
          {files.map((f) => (
            <div className="data-row" key={f.path}>
              <span className="data-name">/{f.path}</span>
              <span className="data-size">{formatBytes(f.size_bytes)}</span>
              <a className="icon-btn" href={extraDownloadUrl(f.path)} download title={t("Download")}>
                <Download size={13} strokeWidth={2.5} />
              </a>
              <button className="icon-btn danger" onClick={() => remove(f.path)} title={t("Delete")}>
                <Trash2 size={13} strokeWidth={2.5} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
