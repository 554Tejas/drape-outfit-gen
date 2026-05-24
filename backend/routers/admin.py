"""
Admin Router
============
Provides admin-facing stats: input counts, generation counts, failed counts,
active jobs, storage usage, and recent job logs.
"""

from fastapi import APIRouter
from models.schemas import AdminStats
from services import storage

router = APIRouter()


@router.get("/stats", response_model=AdminStats)
async def admin_stats():
    """Return admin dashboard statistics."""
    return AdminStats(**storage.storage_stats())


@router.get("/jobs")
async def list_all_jobs():
    """List all jobs with their statuses."""
    return storage.list_jobs()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    from fastapi import HTTPException
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Mark a stuck job as failed (does not kill background tasks)."""
    from fastapi import HTTPException
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    storage.update_job(job_id, status="failed", error_log=job.get("error_log", []) + ["Manually cancelled"])
    return {"message": f"Job {job_id} marked as failed."}
