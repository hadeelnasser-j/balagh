"""Service container: wires repositories, providers and services from Settings."""
from __future__ import annotations

import logging
from typing import Any

from app.config import Settings
from app.models.enums import JobStatus, JobType
from app.repositories.base import DataRepository, Row
from app.repositories.local_sources import LocalSourcesRepository
from app.repositories.memory_repo import MemoryRepository
from app.services.content_detection import ContentDetector
from app.services.dubbing import DubbingService
from app.services.errors import MSG, conflict
from app.services.ffmpeg import FFmpegService
from app.services.jobs import JobManager
from app.services.meaning_locks import MeaningLockService
from app.services.projects import ProjectService
from app.services.providers import (
    TranscriptionProvider, TranslationProvider, TTSProvider, build_transcription_provider,
    build_translation_provider, build_tts_provider,
)
from app.services.rendering import RenderingService
from app.services.reports import ReportService
from app.services.review import ReviewService
from app.services.segments import SegmentRepository
from app.services.srt import SrtService
from app.services.storage import StorageService
from app.services.translation import TranslationService
from app.services.verification import VerificationService
from app.workers import tasks
from app.workers.runner import BackgroundRunner

logger = logging.getLogger(__name__)


class Container:
    def __init__(self, settings: Settings, *, repo: DataRepository | None = None,
                 sources: LocalSourcesRepository | None = None,
                 transcriber: TranscriptionProvider | None = None, translator: TranslationProvider | None = None,
                 tts: TTSProvider | None = None, runner: BackgroundRunner | None = None) -> None:
        self.settings = settings
        supabase_client: Any = None
        if repo is None:
            if settings.data_backend == "memory":
                repo = MemoryRepository()
            else:
                from app.repositories.supabase_repo import SupabaseRepository
                supa = SupabaseRepository(settings.supabase_url, settings.supabase_service_role_key,
                                          settings.supabase_timeout_seconds)
                supabase_client = supa.client
                repo = supa
        self.repo = repo
        self.ffmpeg = FFmpegService(settings.ffmpeg_path, settings.ffprobe_path, settings.audio_sample_rate,
                                    settings.dubbed_audio_bitrate)
        buckets = {"video": settings.bucket_videos, "audio": settings.bucket_audio, "tts": settings.bucket_audio,
                   "subtitles": settings.bucket_subtitles, "output": settings.bucket_outputs}
        self.storage = StorageService(settings.storage_dir,
                                      supabase_client if settings.supabase_storage_enabled else None, buckets)
        self.sources = sources or LocalSourcesRepository(settings.sources_db_path,
                                                         min_match_chars=settings.min_match_chars,
                                                         mixed_coverage_threshold=settings.mixed_coverage_threshold)
        self.runner = runner or BackgroundRunner(settings.worker_threads)
        self.jobs = JobManager(self.repo, self.runner)

        self.transcriber = transcriber or build_transcription_provider(settings, self.ffmpeg)
        self.translator = translator or build_translation_provider(settings)
        self.tts = tts or build_tts_provider(settings, self.ffmpeg)

        self.segments = SegmentRepository(self.repo)
        self.locks = MeaningLockService(self.repo)
        self.detector = ContentDetector(self.sources, settings)
        self.translation = TranslationService(settings, self.translator, self.sources, self.segments, self.locks)
        self.verification = VerificationService(settings, self.repo, self.sources, self.detector, self.segments,
                                                self.translation)
        self.review = ReviewService(self.repo, self.segments, self.locks, self.translation)
        self.projects = ProjectService(settings, self.repo, self.storage, self.jobs)
        self.dubbing = DubbingService(settings, self.repo, self.segments, self.tts, self.ffmpeg, self.storage)
        self.rendering = RenderingService(self.repo, self.segments, self.dubbing, self.ffmpeg, self.storage,
                                          settings.original_audio_duck_volume)
        self.srt = SrtService(self.repo, self.segments, self.storage, settings.srt_include_attribution)
        self.reports = ReportService(self.repo, self.segments, self.jobs, self.storage, self.sources)

    # ------------------------------------------------------------------ job starters
    def start_upload_processing(self, project_id: str) -> tuple[Row, bool]:
        return self.jobs.start(project_id, JobType.UPLOAD, lambda jid: tasks.upload_task(self, project_id, jid),
                               initial_status=JobStatus.UPLOADED, initial_step="تم رفع الفيديو")

    def start_transcription(self, project_id: str) -> tuple[Row, bool]:
        project = self.projects.get(project_id)
        if not project.get("audio_storage_path"):
            raise conflict(MSG["audio_missing"], "audio_missing")
        return self.jobs.start(project_id, JobType.TRANSCRIPTION,
                               lambda jid: tasks.transcription_task(self, project_id, jid))

    def start_translation(self, project_id: str) -> tuple[Row, bool]:
        self.projects.get(project_id)
        if not self.segments.for_project(project_id):
            raise conflict(MSG["no_segments"], "no_segments")
        return self.jobs.start(project_id, JobType.TRANSLATION,
                               lambda jid: tasks.translation_task(self, project_id, jid))

    def start_dubbing(self, project_id: str, force: bool = False) -> tuple[Row, bool]:
        self.projects.get(project_id)
        self.dubbing.assert_can_generate(project_id)
        return self.jobs.start(project_id, JobType.DUBBING,
                               lambda jid: tasks.dubbing_task(self, project_id, jid, force))

    def start_render(self, project_id: str) -> tuple[Row, bool]:
        self.projects.get(project_id)
        self.rendering.assert_can_render(project_id)
        return self.jobs.start(project_id, JobType.RENDERING, lambda jid: tasks.render_task(self, project_id, jid))

    def shutdown(self) -> None:
        self.runner.shutdown()
