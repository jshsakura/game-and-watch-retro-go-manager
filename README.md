# gnw-retro-manager

Web converter & file manager for **Nintendo® Game & Watch™ Retro-Go SD**
([sylverb/game-and-watch-retro-go-sd](https://github.com/sylverb/game-and-watch-retro-go-sd)).

Upload games and videos "무지성"으로 올리면 → 한글명 자동 변환 + 기기 규격 커버/영상으로
변환 → SD카드 폴더 구조 그대로 ZIP으로 다시 받습니다. 올린 파일은 서버에 영구 보관됩니다.

## Two pipelines

**A. ROM → cover**
`기종 선택 → ROM 업로드 → 한글명 변환 → 커버 생성 → /roms + /covers ZIP`
- Cover spec (ported from firmware `tools/gencovers.py`): max **186×100**, aspect
  preserved, LANCZOS, **JPEG q85**, saved as `.img`. Cover path mirrors the ROM:
  `/roms/<sys>/Name.<ext>` → `/covers/<sys>/Name.img`.

**B. Video → /media**
`영상 업로드 → ffmpeg MJPEG .avi 인코딩 → /media 보관 → 다운로드`
- The chip has only a HW JPEG decoder → **MJPEG-in-.avi only** (no H.264/HEVC).
  320×240, q:v 5, 30fps, PCM s16le mono 24k. Exact recipe in
  `backend/app/services/video.py`. Requires `ffmpeg` on the server.

## Design

Game & Watch hardware DNA with an **8-bit pixel-art** look. Theme switch:
**🟩 Zelda Edition (green)** ↔ **🟥 Mario Edition (red)**.

## Stack

- Backend: **FastAPI** (`backend/`)
- Frontend: **React + Vite** (`frontend/`)
- Storage: server disk (persistent) + SQLite metadata

## Run (dev — two terminals)

```bash
# Terminal 1 – Backend (port 38080)
cd backend
GNW_API_PORT=38080 python3 -m uvicorn app.main:app --host 0.0.0.0 --port 38080
# http://<tailscale-ip>:38080/api/health

# Terminal 2 – Frontend Vite dev server (port 38081, proxies /api → 38080)
cd frontend
npm install
npm run dev
# http://<tailscale-ip>:38081
```

Provider keys (optional, env only): `SCREENSCRAPER_*`, `IGDB_CLIENT_ID/SECRET`.

## Run (Docker — production, single container)

```bash
# Build + start (host port 38472 by default).
docker compose up -d

# Open the app.
# http://<host>:38472
# Attach a Cloudflare / ngrok / Tailscale Funnel tunnel to port 38472.

# Override the host port without editing docker-compose.yml:
GNW_HOST_PORT=12345 docker compose up -d
```

Uploaded files and the SQLite database are stored in the `gnw-data` named
volume — they survive `docker compose down` and container restarts.

```bash
# View logs
docker compose logs -f

# Stop without removing data
docker compose down

# Remove everything including data (파일 전부 삭제 — 주의!)
docker compose down -v
```

## API endpoints (new in backlog)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sessions/{sid}/roms/{id}/download` | ROM + cover as ZIP |
| GET | `/api/sessions/{sid}/videos/{id}/download` | Encoded .avi file |
| GET | `/api/sessions/{sid}/roms/{id}/cover` | Preview current cover |
| POST | `/api/sessions/{sid}/roms/{id}/cover` | Upload user cover image |
| POST | `/api/sessions/{sid}/roms/{id}/cover/regenerate` | Re-fetch art for cover |
| POST | `/api/sessions/{sid}/uploads` | Init chunked upload |
| PUT | `/api/sessions/{sid}/uploads/{uid}/chunk?index=N` | Send chunk |
| GET | `/api/sessions/{sid}/uploads/{uid}` | Upload status |
| POST | `/api/sessions/{sid}/uploads/{uid}/complete` | Finalise upload |

## Status

Scaffolded: system table, cover & video conversion cores, FastAPI app.
Some system `dirname`/`ext` rows are marked `verified=False` in
`backend/app/systems.py` — confirm against the device before trusting them.
