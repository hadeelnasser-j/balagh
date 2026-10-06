"""Processing job lifecycle with duplicate-job prevention."""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable

from app.models.enums import TERMINAL_JOB_STATUSES, JobStatus, JobType
from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.services.errors import MSG, AppError, conflict, not_found
from app.workers.runner import BackgroundRunner

logger = logging.getLogger(__name__)

TERMINAL = {s.value for s in TERMINAL_JOB_STATUSES}

# Job types that may not run at the same time for one project.
_EXCLUSIVE = {JobType.UPLOAD, JobType.TRANSCRIPTION, JobType.TRANSLATION, JobType.DUBBING, JobType.RENDERING}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def job_out(job: Row) -> dict[str, Any]:
    return {
        "job_id": job["id"], "project_id": job["project_id"], "job_type": job["job_type"],
        "status": job["status"], "progress": int(job.get("progress") or 0),
        "current_step": job.get("current_step"), "error_message": job.get("error_message"),
        "created_at": job.get("created_at"), "updated_at": job.get("updated_at"),
    }


class JobManager:
    def __init__(self, repo: DataRepository, runner: BackgroundRunner) -> None:
        self.repo = repo
        self.runner = runner
        self._lock = threading.Lock()

    def get(self, job_id: str) -> Row:
        job = self.repo.get(Tables.JOBS, job_id)
        if not job:
            raise not_found(MSG["job_not_found"])
        return job

    def active_jobs(self, project_id: str) -> list[Row]:
        jobs = self.repo.list(Tables.JOBS, {"project_id": project_id}, order_by="created_at", desc=True, limit=20)
        return [j for j in jobs if j["status"] not in TERMINAL]

    def latest(self, project_id: str, job_type: JobType | None = None) -> Row | None:
        filters: Row = {"project_id": project_id}
        if job_type:
            filters["job_type"] = job_type.value
        rows = self.repo.list(Tables.JOBS, filters, order_by="created_at", desc=True, limit=1)
        return rows[0] if rows else None

    def start(self, project_id: str, job_type: JobType, task: Callable[[str], None], *,
              initial_status: JobStatus = JobStatus.QUEUED, initial_step: str = "في قائمة الانتظار") -> tuple[Row, bool]:
        """Create a job and run `task(job_id)` in the background.

        If a job of the same type is already active, it is returned instead (reused=True).
        If a different exclusive job is active, a 409 is raised.
        """
        with self._lock:
            for job in self.active_jobs(project_id):
                if job["job_type"] == job_type.value:
                    return job, True
                if JobType(job["job_type"]) in _EXCLUSIVE and job_type in _EXCLUSIVE:
                    raise conflict(MSG["job_running"], "job_running")
            job = self.repo.insert(Tables.JOBS, {
                "project_id": project_id, "job_type": job_type.value, "status": initial_status.value,
                "progress": 0, "current_step": initial_step, "error_message": None,
            })
        self.runner.submit(self._execute, job["id"], task)
        return self.repo.get(Tables.JOBS, job["id"]) or job, False

    def _execute(self, job_id: str, task: Callable[[str], None]) -> None:
        try:
            task(job_id)
        except AppError as exc:
            self.fail(job_id, exc.detail)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Job %s failed", job_id)
            self.fail(job_id, f"فشلت المعالجة: {exc}")

    def update(self, job_id: str, status: JobStatus | None = None, progress: int | None = None,
               step: str | None = None) -> Row:
        patch: Row = {}
        if status is not None:
            patch["status"] = status.value
            if status.value in TERMINAL:
                patch["finished_at"] = _now()
        if progress is not None:
            patch["progress"] = max(0, min(100, int(progress)))
        if step is not None:
            patch["current_step"] = step
        return self.repo.update(Tables.JOBS, job_id, patch)

    def fail(self, job_id: str, message: str) -> None:
        try:
            self.repo.update(Tables.JOBS, job_id, {"status": JobStatus.FAILED.value, "error_message": message[:2000],
                                                    "current_step": "فشلت المعالجة", "finished_at": _now()})
        except Exception:  # noqa: BLE001
            logger.exception("Could not mark job %s as failed", job_id)

    def recover_stale(self, started_before: str | None = None) -> int:
        """Jobs left active by a previous process can never finish: mark them failed.

        Only jobs created before `started_before` (this process's start time) are touched,
        so the recovery can run in the background without killing new jobs.
        """
        count = 0
        for job in self.repo.list(Tables.JOBS, order_by="created_at", desc=True, limit=500):
            if started_before and str(job.get("created_at") or "") >= started_before:
                continue
            if job["status"] not in TERMINAL:
                self.fail(job["id"], "توقفت المهمة بسبب إعادة تشغيل الخادم. يرجى إعادة المحاولة.")
                count += 1
        return count
