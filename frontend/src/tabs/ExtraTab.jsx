import React, { useEffect, useState } from "react";
import { FolderPlus, Upload, Download, Trash2 } from "lucide-react";
import { getExtra, uploadExtra, deleteExtra, extraDownloadUrl, formatBytes } from "../api.js";
import { Dropzone, Loading } from "../components.jsx";
import { useToast } from "../toast.jsx";
import { useT } from "../i18n.jsx";

// Arbitrary passthrough files → SD root verbatim. Pick a target folder (e.g.
// bios/nes) and the files land at <folder>/<name> in the SD ZIP.
export default function ExtraTab({ onChanged }) {
  const toast = useToast();
  const t = useT();
  const [folder, setFolder] = useState("bios/nes");
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
    const dir = folder.replace(/^\/+|\/+$/g, "");           // trim slashes
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

  async function remove(path) {
    if (!(await toast.confirm(t("'/{path}' 파일을 삭제할까요?", { path }), { confirmText: t("삭제") }))) return;
    try { await deleteExtra(path); await reload(); onChanged?.(); }
    catch (e) { toast.error(e.message); }
  }

  return (
    <div className="stack">
      <div className="muted">
        <FolderPlus size={13} aria-hidden /> {t("아무 파일이나")} <b>{t("SD 경로")}</b>{t("를 정해서 올리면 SD ZIP에 그대로 들어갑니다. (FDS:")} <b>bios/nes</b> {t("에")} <b>disksys.rom</b>)
      </div>

      <label className="field-label">{t("대상 폴더 (SD 경로)")}</label>
      <div className="path-group">
        <span className="path-group-tag"><FolderPlus size={13} strokeWidth={2.5} aria-hidden /> SD</span>
        <span className="path-slash">/</span>
        <input
          className="path-input"
          value={folder}
          spellCheck={false}
          placeholder="bios/nes"
          onChange={(e) => setFolder(e.target.value)}
        />
        <span className="path-trail">/…</span>
      </div>

      <Dropzone
        multiple
        label={
          <span className="dz-label">
            <Upload size={16} aria-hidden /> {t("파일을 끌어다 놓거나 클릭 →")} <b>/{(folder.replace(/^\/+|\/+$/g, "") || "")}/</b> {t("에 저장")}
          </span>
        }
        onFiles={handleFiles}
      />

      {loading ? (
        <Loading text={t("목록 불러오는 중…")} />
      ) : files.length === 0 ? (
        <div className="muted">{t("올려둔 파일이 없습니다 (SD에 포함 안 됨).")}</div>
      ) : (
        <div className="data-list">
          {files.map((f) => (
            <div className="data-row" key={f.path}>
              <span className="data-name">/{f.path}</span>
              <span className="data-size">{formatBytes(f.size_bytes)}</span>
              <a className="icon-btn" href={extraDownloadUrl(f.path)} download title={t("다운로드")}>
                <Download size={13} strokeWidth={2.5} />
              </a>
              <button className="icon-btn danger" onClick={() => remove(f.path)} title={t("삭제")}>
                <Trash2 size={13} strokeWidth={2.5} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
