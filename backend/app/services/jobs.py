"""
In-memory job registry for long-running work (video encoding).

Files persist on disk + DB, but live progress is ephemeral (lost on restart) —
fine for MVP; a restart just means re-checking the DB status. When the app
moves to Docker/multiple workers this should become Redis/RQ or similar.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace

# status: queued -> running -> done | failed
_jobs: dict[str, "Job"] = {}
_lock = asyncio.Lock()


@dataclass(frozen=True)
class Job:
    id: str
    kind: str                 # e.g. "video_encode"
    status: str = "queued"
    progress: float = 0.0     # 0..1 (best-effort; ffmpeg encode is coarse)
    message: str = ""
    result: dict | None = None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": round(self.progress, 3),
            "message": self.message,
            "result": self.result,
        }


async def create(job_id: str, kind: str) -> Job:
    async with _lock:
        job = Job(id=job_id, kind=kind)
        _jobs[job_id] = job
        return job


async def update(job_id: str, **changes) -> Job | None:
    """Immutably replace the stored job with the given field changes."""
    async with _lock:
        current = _jobs.get(job_id)
        if current is None:
            return None
        updated = replace(current, **changes)
        _jobs[job_id] = updated
        return updated


async def get(job_id: str) -> Job | None:
    async with _lock:
        return _jobs.get(job_id)
