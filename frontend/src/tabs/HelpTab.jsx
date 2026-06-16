import React from "react";
import { Gamepad2, Keyboard, Power, Info, ListOrdered, HardDrive } from "lucide-react";
import { useT } from "../i18n.jsx";

// 이 도구로 SD를 준비하는 단계
const STEPS = [
  "UPLOAD 탭(또는 빈 라이브러리)에서 플랫폼을 고르고 롬을 끌어다 놓습니다.",
  "한글명(영문) 이름과 커버가 자동으로 붙습니다. 영상은 VIDEO 탭에서 .avi로 변환돼 /media에 들어갑니다.",
  "필요하면 카드 상세에서 이름 변경·커버 검색/업로드·위치(크롭) 조정을 합니다.",
  "우측 상단 'SD ZIP'(또는 라이브러리의 '현재 플랫폼 ZIP')으로 받습니다. 예상 용량이 라벨로 표시됩니다.",
  "받은 ZIP을 SD카드 루트에 그대로 압축 해제하면 끝 — /roms, /covers, /cores 구조가 맞춰져 있습니다.",
];

// SD카드 / 폴더 구조
const SDCARD = [
  ["포맷", "exFAT 권장 (또는 FAT32)"],
  ["/roms/<플랫폼>/", "플랫폼별 롬 파일 (압축 풀린 상태)"],
  ["/covers/<플랫폼>/", "커버 .img (186×100, 파일명은 롬과 일치) — 자동 생성"],
  ["/cores/", "PICO-8 코어(pico8.bin 등) — SD ZIP에 자동 포함됨"],
  ["/media/", "예능용 영상 .avi (SD ZIP 기본 제외, ?video로 포함)"],
];

// 기기 버튼 단축키 (출처: github.com/sylverb/game-and-watch-retro-go-sd)
const SECTIONS = [
  {
    icon: Gamepad2,
    title: "기본 버튼",
    rows: [
      ["GAME", "시작 (Start)"],
      ["TIME", "선택 (Select)"],
      ["PAUSE/SET", "에뮬레이터 메뉴 열기"],
    ],
  },
  {
    icon: Keyboard,
    title: "게임 중 단축키  ·  PAUSE/SET 를 누른 채로",
    rows: [
      ["PAUSE/SET + GAME", "스크린샷 캡처"],
      ["PAUSE/SET + TIME", "속도 전환 (1x / 1.5x)"],
      ["PAUSE/SET + ▲", "밝기 올리기"],
      ["PAUSE/SET + ▼", "밝기 내리기"],
      ["PAUSE/SET + ▶", "볼륨 올리기"],
      ["PAUSE/SET + ◀", "볼륨 내리기"],
      ["PAUSE/SET + A", "상태 저장 (Save state)"],
      ["PAUSE/SET + B", "상태 불러오기 (Load state)"],
      ["PAUSE/SET + POWER", "전원 끄기 (상태 저장 안 함)"],
    ],
  },
  {
    icon: Power,
    title: "부팅 시 (켤 때 누르고 있기)",
    rows: [
      ["PAUSE/SET", "부트로더 진단 메뉴"],
      ["TIME", "게임 목록으로 강제 부팅 (문제 세이브 우회)"],
    ],
  },
];

// GitHub mark (Octocat) — lucide-react dropped brand icons, so inline the mark.
function GithubMark({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.65 7.65 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

function Combo({ combo }) {
  const keys = combo.split("+").map((k) => k.trim());
  return (
    <span className="help-combo">
      {keys.map((k, i) => (
        <React.Fragment key={i}>
          {i > 0 && <span className="help-plus">+</span>}
          <kbd className="keycap">{k}</kbd>
        </React.Fragment>
      ))}
    </span>
  );
}

export default function HelpTab() {
  const t = useT();
  return (
    <div className="stack help-tab">
      <div className="muted">
        <Info size={13} aria-hidden /> {t("롬·영상을 올리면 한글명·커버를 자동으로 붙여, retro-go SD 카드 구조 그대로 ZIP으로 묶어줍니다.")}
      </div>

      {/* 사용법 */}
      <div className="help-section">
        <div className="help-head"><ListOrdered size={14} strokeWidth={2.5} aria-hidden /> {t("기본 사용법")}</div>
        <ol className="help-steps">
          {STEPS.map((s, i) => <li key={i}>{t(s)}</li>)}
        </ol>
      </div>

      {/* SD 카드 구조 */}
      <div className="help-section">
        <div className="help-head"><HardDrive size={14} strokeWidth={2.5} aria-hidden /> {t("SD 카드 / 폴더 구조")}</div>
        <div className="help-list">
          {SDCARD.map(([k, v]) => (
            <div className="help-row" key={k}>
              <span className="help-combo"><kbd className="keycap">{t(k)}</kbd></span>
              <span className="help-action">{t(v)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 단축키 */}
      {SECTIONS.map((s) => (
        <div className="help-section" key={s.title}>
          <div className="help-head"><s.icon size={14} strokeWidth={2.5} aria-hidden /> {t(s.title)}</div>
          <div className="help-list">
            {s.rows.map(([combo, action]) => (
              <div className="help-row" key={combo + action}>
                <Combo combo={combo} />
                <span className="help-action">{t(action)}</span>
              </div>
            ))}
          </div>
        </div>
      ))}

      <div className="muted help-note">
        {t("MSX·Amstrad는 PAUSE/SET 메뉴에서 가상 키보드 입력이 가능하고, 젤다3·슈퍼마리오월드는 마리오/젤다 기기 버전에 따라 버튼 매핑이 다릅니다. · 출처:")}
      </div>
      <a className="help-project" href="https://github.com/sylverb/game-and-watch-retro-go-sd" target="_blank" rel="noreferrer">
        <GithubMark size={18} />
        <span className="help-project-name">game-and-watch-retro-go-sd</span>
      </a>
    </div>
  );
}
