"""Projects, upload, processing jobs, segments listing and pipeline status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.dependencies import get_container
from app.dependencies.container import Container
from app.schemas import (
    PipelineStatus, ProcessingJobOut, ProjectCreate, ProjectOut, ReviewSummary, SegmentPage,
)
from app.services.jobs import job_out
from app.services.segments import segment_out

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, c: Container = Depends(get_container)) -> dict:
    project = c.projects.create(body.title, body.source_language, body.target_language, body.dubbing_mode)
    return c.projects.with_latest_job(project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, c: Container = Depends(get_container)) -> dict:
    return c.projects.with_latest_job(c.projects.get(project_id))


@router.post("/{project_id}/upload", response_model=ProcessingJobOut)
def upload_video(project_id: str, file: UploadFile = File(...), c: Container = Depends(get_container)) -> dict:
    project = c.projects.get(project_id)
    c.projects.save_upload(project, file.filename, file.file)
    job, _ = c.start_upload_processing(project_id)
    return job_out(job)


@router.post("/{project_id}/extract-audio", response_model=ProcessingJobOut)
def extract_audio(project_id: str, c: Container = Depends(get_container)) -> dict:
    """Re-run validation + audio extraction for the already uploaded video."""
    c.projects.get(project_id)
    job, _ = c.start_upload_processing(project_id)
    return job_out(job)


@router.post("/{project_id}/transcribe", response_model=ProcessingJobOut)
def transcribe(project_id: str, c: Container = Depends(get_container)) -> dict:
    """Transcription -> content detection -> source verification -> translation."""
    job, _ = c.start_transcription(project_id)
    return job_out(job)


@router.post("/{project_id}/translate", response_model=ProcessingJobOut)
def translate(project_id: str, c: Container = Depends(get_container)) -> dict:
    """Translate pending/failed segments (retry)."""
    job, _ = c.start_translation(project_id)
    return job_out(job)


@router.get("/{project_id}/segments", response_model=SegmentPage)
def list_segments(project_id: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=5000),
                  c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    total, items = c.segments.page(project_id, page, page_size)
    return {"project_id": project_id, "total": total, "page": page, "page_size": page_size,
            "items": [segment_out(s) for s in items]}


@router.get("/{project_id}/review-summary", response_model=ReviewSummary)
def review_summary(project_id: str, c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    return c.review.summary(project_id)


@router.get("/{project_id}/pipeline-status", response_model=PipelineStatus)
def pipeline_status(project_id: str, c: Container = Depends(get_container)) -> dict:
    return c.reports.pipeline_status(c.projects.get(project_id))
