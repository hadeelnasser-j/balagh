"""Dubbing readiness, audio generation/review, rendering and media downloads."""
from __future__ import annotations

import re

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import FileResponse

from app.dependencies import get_container
from app.dependencies.container import Container
from app.schemas import DubbingReadiness, IntegrityReport, JobRef, ReviewerBody, SegmentOut
from app.services.errors import MSG, not_found
from app.services.segments import segment_out

router = APIRouter(prefix="/api/projects", tags=["dubbing"])


@router.get("/{project_id}/dubbing-readiness", response_model=DubbingReadiness)
def dubbing_readiness(project_id: str, c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    return {**c.dubbing.readiness(project_id), **c.dubbing.output_status(project_id)}


@router.get("/{project_id}/dubbing-status")
def dubbing_status(project_id: str, c: Container = Depends(get_container)) -> dict:
    return c.reports.dubbing_status(c.projects.get(project_id))


@router.get("/{project_id}/dubbing-report")
def dubbing_report(project_id: str, c: Container = Depends(get_container)) -> dict:
    return c.reports.dubbing_report(c.projects.get(project_id))


@router.get("/{project_id}/integrity-report", response_model=IntegrityReport)
def integrity_report(project_id: str, c: Container = Depends(get_container)) -> dict:
    return c.reports.integrity_report(c.projects.get(project_id))


@router.post("/{project_id}/generate-dubbing", response_model=JobRef)
def generate_dubbing(project_id: str, force: bool = Query(False), c: Container = Depends(get_container)) -> dict:
    job, reused = c.start_dubbing(project_id, force)
    return {"job_id": job["id"], "status": job["status"], "reused": reused}


@router.post("/{project_id}/segments/{segment_id}/generate-audio", response_model=SegmentOut)
def generate_segment_audio(project_id: str, segment_id: str, c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    segment = c.segments.get(segment_id)
    if segment["project_id"] != project_id:
        raise not_found(MSG["segment_not_found"])
    return segment_out(c.dubbing.generate_segment(segment_id))


@router.get("/{project_id}/segments/{segment_id}/audio")
def segment_audio(project_id: str, segment_id: str, c: Container = Depends(get_container)) -> FileResponse:
    path = c.dubbing.segment_audio_path(project_id, segment_id)
    media = "audio/wav" if path.suffix == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media)


@router.post("/{project_id}/segments/{segment_id}/approve-audio", response_model=SegmentOut)
def approve_audio(project_id: str, segment_id: str, body: ReviewerBody | None = Body(default=None),
                  c: Container = Depends(get_container)) -> dict:
    return segment_out(c.dubbing.approve_audio(project_id, segment_id, (body or ReviewerBody()).reviewed_by))


@router.post("/{project_id}/segments/{segment_id}/reject-audio", response_model=SegmentOut)
def reject_audio(project_id: str, segment_id: str, body: ReviewerBody | None = Body(default=None),
                 c: Container = Depends(get_container)) -> dict:
    return segment_out(c.dubbing.reject_audio(project_id, segment_id, (body or ReviewerBody()).reviewed_by))


@router.post("/{project_id}/approve-all-audio")
def approve_all_audio(project_id: str, c: Container = Depends(get_container)) -> dict:
    c.projects.get(project_id)
    return {"project_id": project_id, "approved": c.dubbing.approve_all(project_id)}


@router.post("/{project_id}/render-dubbed-video", response_model=JobRef)
def render_dubbed_video(project_id: str, c: Container = Depends(get_container)) -> dict:
    job, reused = c.start_render(project_id)
    return {"job_id": job["id"], "status": job["status"], "reused": reused}


@router.get("/{project_id}/dubbed-audio")
def dubbed_audio(project_id: str, c: Container = Depends(get_container)) -> FileResponse:
    project = c.projects.get(project_id)
    path = c.storage.ensure_local(project.get("dubbed_audio_path"))
    if path is None:
        raise not_found(MSG["dubbed_missing"])
    return FileResponse(path, media_type="audio/mp4", filename=_download_name(project, "dubbed.m4a"))


def _download_name(project: dict, suffix: str) -> str:
    """Readable file name from the project title (Arabic kept; unsafe characters removed)."""
    title = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", project.get("title") or "").strip()
    title = re.sub(r"\s+", "-", title)[:80] or project["id"]
    return f"BALAGH-{title}-{suffix}"


@router.get("/{project_id}/dubbed-video")
def dubbed_video(project_id: str, download: bool = Query(False), c: Container = Depends(get_container)) -> FileResponse:
    """Inline for the player; `?download=1` sends Content-Disposition: attachment (no page navigation)."""
    project = c.projects.get(project_id)
    path = c.storage.ensure_local(project.get("dubbed_video_path"))
    if path is None:
        raise not_found(MSG["dubbed_missing"])
    return FileResponse(path, media_type="video/mp4", filename=_download_name(project, "dubbed.mp4"),
                        content_disposition_type="attachment" if download else "inline")
