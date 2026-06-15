"""Poll long-running job status (video encoding)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services import jobs as jobs_service

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = await jobs_service.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job")
    return job.as_dict()
