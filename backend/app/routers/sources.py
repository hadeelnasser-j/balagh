"""Source verification, recovery and the local sources status."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_container
from app.dependencies.container import Container
from app.schemas import (
    DubbingCheck, RecoveredReviewBody, RecoveredSourceOut, RecoverSourcesResult, SourcesStatus, SourceSummary,
)

router = APIRouter(prefix="/api", tags=["sources"])


@router.get("/pipeline/sources-status", response_model=SourcesStatus)
def sources_status(c: Container = Depends(get_container)) -> dict:
    return c.reports.sources_status()


@router.post("/projects/{project_id}/verify-sources")
def verify_sources(project_id: str, c: Container = Depends(get_container)) -> dict:
    project = c.projects.get(project_id)
    result = c.verification.reverify_project(project)
    return {"project_id": project_id, **result, "summary": c.verification.source_summary(project_id)}


@router.get("/projects/{project_id}/source-summary", response_model=SourceSummary)
def source_summary(project_id: str, c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    return c.verification.source_summary(project_id)


@router.post("/projects/{project_id}/dubbing-check", response_model=DubbingCheck)
def dubbing_check(project_id: str, c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    r = c.dubbing.readiness(project_id)
    return {"project_id": project_id, "ready": r["generation_ready"], "segments_total": r["segments_total"],
            "segments_ready": r["segments_ready"]}


@router.post("/projects/{project_id}/recover-sources", response_model=RecoverSourcesResult)
def recover_sources(project_id: str, c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    return c.verification.recover(project_id)


@router.get("/projects/{project_id}/recovered-sources", response_model=list[RecoveredSourceOut])
def recovered_sources(project_id: str, c: Container = Depends(get_container)) -> list[dict]:
    c.projects.get(project_id)
    return c.verification.list_recovered(project_id)


@router.post("/projects/{project_id}/recovered-sources/{recovered_id}/review", response_model=RecoveredSourceOut)
def review_recovered(project_id: str, recovered_id: str, body: RecoveredReviewBody,
                     c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    return c.verification.review_recovered(project_id, recovered_id, body.decision, body.reviewed_by)
