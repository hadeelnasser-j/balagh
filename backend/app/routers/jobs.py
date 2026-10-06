from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_container
from app.dependencies.container import Container
from app.schemas import ProcessingJobOut
from app.services.jobs import job_out

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=ProcessingJobOut)
def get_job(job_id: str, c: Container = Depends(get_container)) -> dict:
    return job_out(c.jobs.get(job_id))
