from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.dependencies import get_container
from app.dependencies.container import Container
from app.schemas import SrtResult
from app.services.errors import MSG, not_found

router = APIRouter(prefix="/api/projects", tags=["subtitles"])


@router.post("/{project_id}/generate-srt", response_model=SrtResult)
def generate_srt(project_id: str, mode: Literal["draft", "final"] = Query("draft"),
                 c: Container = Depends(get_container)) -> dict:
    return c.srt.generate(c.projects.get(project_id), mode)


@router.get("/{project_id}/srt")
def download_srt(project_id: str, c: Container = Depends(get_container)) -> FileResponse:
    project = c.projects.get(project_id)
    path = c.storage.ensure_local(project.get("srt_storage_path"))
    if path is None:
        raise not_found(MSG["srt_missing"])
    return FileResponse(path, media_type="application/x-subrip; charset=utf-8", filename=f"{project_id}.srt")
