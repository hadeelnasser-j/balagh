"""Projects: creation, lookup and video upload validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO

from app.config import Settings
from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.services.errors import MSG, AppError, bad_request, not_found
from app.services.jobs import JobManager
from app.services.storage import StorageError, StorageService


class ProjectService:
    def __init__(self, settings: Settings, repo: DataRepository, storage: StorageService, jobs: JobManager) -> None:
        self.settings = settings
        self.repo = repo
        self.storage = storage
        self.jobs = jobs

    def create(self, title: str, source_language: str, target_language: str, dubbing_mode: str) -> Row:
        return self.repo.insert(Tables.PROJECTS, {
            "title": title.strip(), "source_language": source_language, "target_language": target_language,
            "dubbing_mode": dubbing_mode, "status": "created",
        })

    def get(self, project_id: str) -> Row:
        project = self.repo.get(Tables.PROJECTS, project_id)
        if not project:
            raise not_found(MSG["project_not_found"])
        return project

    def with_latest_job(self, project: Row) -> dict[str, Any]:
        latest = self.jobs.latest(project["id"])
        out = dict(project)
        out["latest_job"] = ({"job_id": latest["id"], "job_type": latest["job_type"], "status": latest["status"]}
                             if latest else None)
        return out

    def save_upload(self, project: Row, filename: str | None, stream: BinaryIO) -> str:
        ext = Path(filename or "").suffix.lower()
        allowed = self.settings.allowed_video_extensions
        if ext not in allowed:
            raise AppError(415, MSG["invalid_format"].format(formats="، ".join(e.lstrip(".") for e in allowed)),
                           "INVALID_FORMAT")
        key = self.storage.project_key(project["id"], "video", f"original{ext}")
        try:
            size = self.storage.save_stream(key, stream, max_bytes=self.settings.max_upload_mb * 1024 * 1024)
        except StorageError as exc:
            if str(exc) == "FILE_TOO_LARGE":
                raise AppError(413, MSG["file_too_large"].format(mb=self.settings.max_upload_mb),
                               "FILE_TOO_LARGE") from exc
            raise
        if size == 0:
            raise bad_request(MSG["empty_file"], "UPLOAD_FAILED")
        # A new video invalidates everything derived from the previous one.
        for table in (Tables.SOURCE_MATCHES, Tables.MEANING_LOCKS, Tables.RECOVERED_SOURCES,
                      Tables.TRANSLATION_REVIEWS, Tables.AUDIO_REVIEWS, Tables.SEGMENTS):
            self.repo.delete_where(table, {"project_id": project["id"]})
        self.repo.update(Tables.PROJECTS, project["id"], {
            "video_storage_path": key, "original_filename": filename, "status": "uploaded",
            # A new video invalidates everything derived from the previous one.
            "audio_storage_path": None, "srt_storage_path": None, "dubbed_video_path": None,
            "dubbed_audio_path": None, "duration_seconds": None,
        })
        return key
