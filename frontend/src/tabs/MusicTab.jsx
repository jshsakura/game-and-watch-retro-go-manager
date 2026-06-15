import React, { useState } from "react";
import { Music, Upload, Loader, CheckCircle2, XCircle } from "lucide-react";
import { uploadMusic } from "../api.js";
import { Dropzone } from "../components.jsx";
import { useT } from "../i18n.jsx";

// MP3 → /music. No conversion: the firmware's Music app reads ID3 tags, album
// art and .lrc lyrics straight from the file, so we just store and ship it.
export default function MusicTab({ onChanged }) {
  const t = useT();
  const [items, setItems] = useState([]); // [{name, status:'up'|'ok'|'err', error}]

  async function handleFiles(files, onProgress) {
    const list = Array.from(files);
    if (!list.length) return;
    const total = list.reduce((s, f) => s + f.size, 0) || 1;
    let done = 0;
    setItems((prev) => [...list.map((f) => ({ name: f.name, status: "up" })), ...prev]);
    for (const f of list) {
      try {
        await uploadMusic(f, (loaded) => onProgress?.(done + loaded, total));
        setItems((prev) => prev.map((it) => (it.name === f.name && it.status === "up" ? { ...it, status: "ok" } : it)));
      } catch (e) {
        setItems((prev) => prev.map((it) => (it.name === f.name && it.status === "up" ? { ...it, status: "err", error: e.message } : it)));
      }
      done += f.size;
    }
    onChanged?.();
  }

  return (
    <div className="stack">
      <div className="muted">
        <Music size={13} aria-hidden /> {t("MP3는 그대로,")} <b>{t("영상은 MP3로 추출")}</b>{t("해서 /music에 보관 (기기 Music 앱이 ID3 태그·앨범아트를 직접 읽음)")}
      </div>

      <Dropzone
        accept="audio/mpeg,.mp3,video/*"
        multiple
        label={
          <span className="dz-label">
            <Upload size={16} aria-hidden /> {t("여기로 MP3나 영상을 끌어다 놓거나 클릭 (영상은 mp3로 추출)")}
          </span>
        }
        onFiles={handleFiles}
      />

      {items.length > 0 && (
        <div className="stack">
          {items.map((it, i) => (
            <div className="row" key={`${it.name}-${i}`}>
              <span className="muted">{it.name}</span>
              <span className="muted">
                {it.status === "ok" ? (
                  <><CheckCircle2 size={13} strokeWidth={2.5} aria-hidden /> {t("완료")}</>
                ) : it.status === "err" ? (
                  <><XCircle size={13} strokeWidth={2.5} aria-hidden /> {it.error || t("실패")}</>
                ) : (
                  <><Loader size={13} strokeWidth={2.5} className="spin" aria-hidden /> {t("올리는 중…")}</>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
