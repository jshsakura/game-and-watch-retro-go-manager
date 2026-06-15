import React, { useEffect, useState } from "react";
import { Gamepad2, Upload } from "lucide-react";
import { getSystems, uploadRomset, coverUrl } from "../api.js";
import { Dropzone, SystemSelect, RomCard, Loading } from "../components.jsx";
import { useT } from "../i18n.jsx";

export default function RomTab({ onChanged }) {
  const t = useT();
  const [systems, setSystems] = useState([]);
  const [active, setActive] = useState(null);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState([]);
  const [extra, setExtra] = useState(null);   // {covers, skippedAlt}
  const [error, setError] = useState("");

  useEffect(() => {
    getSystems()
      .then((s) => { setSystems(s); setActive(s[0]?.key ?? null); })
      .catch((e) => setError(e.message));
  }, []);

  const current = systems.find((s) => s.key === active);
  const accept = current?.exts?.length ? current.exts.map((e) => "." + e).join(",") : "";
  const okResults = results.filter((r) => r.ok);
  const failed = results.filter((r) => !r.ok);
  const dups = results.filter((r) => r.error === "duplicate");
  const badExt = failed.filter((r) => r.error !== "duplicate");

  async function handleFiles(files, onProgress) {
    if (!active || !current) return;
    setBusy(true); setError(""); setExtra(null);
    try {
      const res = await uploadRomset(active, current.exts, files, onProgress);
      setResults(res.results);
      setExtra({ covers: res.covers || 0, skippedAlt: res.skippedAlt || 0 });
      onChanged?.();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="muted">
        <Gamepad2 size={13} aria-hidden /> {t("플랫폼 선택 → 롬 올리면 한글명·커버 자동. 폴더째 올리면 동봉 이미지(.png)를 커버로 쓰고 alt덤프([a1])는 건너뜀")}
      </div>

      {systems.length === 0 && !error ? (
        <Loading text={t("플랫폼 목록 불러오는 중…")} />
      ) : (
        <SystemSelect systems={systems} value={active} onChange={setActive} />
      )}

      <Dropzone
        accept={accept}
        multiple
        label={
          <span className="dz-label">
            <Upload size={16} aria-hidden /> {t("여기로 {name} 롬을 끌어다 놓거나 클릭", { name: current?.name ?? "" })}
          </span>
        }
        onFiles={handleFiles}
      />

      {error && <div className="badge failed">{error}</div>}

      {results.length > 0 && (
        <div className="muted">
          ✓ {t("{n}개 저장", { n: okResults.length })}
          {extra?.covers > 0 ? ` · ${t("🖼 동봉 커버 {n}개", { n: extra.covers })}` : ""}
          {extra?.skippedAlt > 0 ? ` · ${t("alt덤프 {n}개 건너뜀", { n: extra.skippedAlt })}` : ""}
          {failed.length > 0 ? ` · ${t("{n}개 건너뜀", { n: failed.length })}` : ""}
        </div>
      )}

      {dups.length > 0 && (
        <div className="badge failed">
          ⚠ {t("이미 있는 롬이라 건너뜀 (중복) {n}개", { n: dups.length })}: {dups.map((f) => f.name).join(", ")}
        </div>
      )}

      {badExt.length > 0 && (
        <div className="muted">{t("건너뜀:")} {badExt.map((f) => f.name).join(", ")} {t("(지원 안 하는 확장자)")}</div>
      )}

      {okResults.length > 0 && (
        <div className="grid">
          {okResults.map((r) => (
            <RomCard
              key={r.id}
              rom={r}
              previewSrc={r.cover_status === "ok" ? coverUrl(r.id) : r.screenshot_url}
              onChanged={onChanged}
            />
          ))}
        </div>
      )}
    </div>
  );
}
