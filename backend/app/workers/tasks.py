"""Background job bodies. Each receives the job id; status strings match what the frontend polls for."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.models.enums import JobStatus
from app.models.tables import Tables, default_segment
from app.services.errors import MSG, AppError

if TYPE_CHECKING:
    from app.dependencies.container import Container

logger = logging.getLogger(__name__)


def _scaled(start: int, end: int, done: int, total: int) -> int:
    if total <= 0:
        return end
    return start + int((end - start) * done / total)


def upload_task(c: "Container", project_id: str, job_id: str) -> None:
    """Validate the uploaded video and extract audio. Ends in `audio_extracted`."""
    s = c.settings
    project = c.projects.get(project_id)
    c.jobs.update(job_id, JobStatus.EXTRACTING_AUDIO, 10, "جارٍ فحص الفيديو...")
    video = c.storage.ensure_local(project.get("video_storage_path"))
    if video is None:
        raise AppError(409, MSG["video_missing"])
    info = c.ffmpeg.probe(video)
    if not any(st.get("codec_type") == "video" for st in info.get("streams", [])):
        raise AppError(415, "الملف المرفوع لا يحتوي على مسار فيديو.")
    if not any(st.get("codec_type") == "audio" for st in info.get("streams", [])):
        raise AppError(422, "الفيديو لا يحتوي على مسار صوتي لاستخراجه.")
    duration = float(info.get("format", {}).get("duration") or 0)
    if duration > s.max_video_duration_seconds:
        raise AppError(413, MSG["duration_exceeded"].format(seconds=s.max_video_duration_seconds))
    c.jobs.update(job_id, JobStatus.EXTRACTING_AUDIO, 40, "جارٍ استخراج الصوت...")
    wav_key = c.storage.project_key(project_id, "audio", "audio.wav")
    mp3_key = c.storage.project_key(project_id, "audio", "audio.mp3")
    c.ffmpeg.extract_audio(video, c.storage.path(wav_key), c.storage.path(mp3_key))
    c.storage.register(wav_key)
    c.storage.register(mp3_key)
    c.repo.update(Tables.PROJECTS, project_id, {"audio_storage_path": wav_key, "duration_seconds": round(duration, 3),
                                                "status": "audio_extracted"})
    c.jobs.update(job_id, JobStatus.AUDIO_EXTRACTED, 100, "اكتمل رفع الفيديو واستخراج الصوت")


def transcription_task(c: "Container", project_id: str, job_id: str) -> None:
    """Transcribe -> detect content -> verify sources -> translate. Ends in `awaiting_review`."""
    project = c.projects.get(project_id)
    wav = c.storage.ensure_local(project.get("audio_storage_path"))
    if wav is None:
        raise AppError(409, MSG["audio_missing"])
    mp3 = wav.with_suffix(".mp3")
    upload_audio = mp3 if mp3.is_file() else wav

    c.jobs.update(job_id, JobStatus.TRANSCRIBING, 5, "جارٍ تفريغ الصوت إلى نص...")
    pieces = c.transcriber.transcribe(upload_audio, project.get("source_language") or c.settings.transcription_language_hint)
    pieces = [p for p in pieces if p.text.strip()]
    if not pieces:
        raise AppError(422, "لم يُعثر على كلام قابل للتفريغ في الفيديو.")

    # Re-transcription replaces all derived data for this project.
    for table in (Tables.SOURCE_MATCHES, Tables.MEANING_LOCKS, Tables.RECOVERED_SOURCES, Tables.TRANSLATION_REVIEWS,
                  Tables.AUDIO_REVIEWS):
        c.repo.delete_where(table, {"project_id": project_id})
    c.repo.delete_where(Tables.SEGMENTS, {"project_id": project_id})
    rows = [default_segment(project_id, i, p.start, p.end, p.text.strip(), project.get("source_language") or "ar",
                            project.get("target_language") or "en") for i, p in enumerate(pieces)]
    c.repo.insert_many(Tables.SEGMENTS, rows)
    c.repo.update(Tables.PROJECTS, project_id, {"status": "transcribed", "srt_storage_path": None,
                                                "dubbed_video_path": None, "dubbed_audio_path": None})

    c.jobs.update(job_id, JobStatus.DETECTING_CONTENT, 35, "جارٍ تحديد نوع المحتوى (قرآن، حديث، عام)...")
    c.jobs.update(job_id, JobStatus.VERIFYING_SOURCES, 40, "جارٍ التحقق من المصادر المعتمدة...")
    c.verification.classify_project(
        project_id, progress=lambda d, t: c.jobs.update(job_id, progress=_scaled(40, 55, d, t)))

    c.jobs.update(job_id, JobStatus.TRANSLATING, 55, "جارٍ الترجمة...")
    segments = c.segments.for_project(project_id)
    c.translation.translate_many(
        project, segments, segments,
        progress=lambda d, t: c.jobs.update(job_id, progress=_scaled(55, 98, d, t),
                                            step=f"جارٍ الترجمة ({d}/{t})"))
    c.repo.update(Tables.PROJECTS, project_id, {"status": "awaiting_review"})
    c.jobs.update(job_id, JobStatus.AWAITING_REVIEW, 100, "اكتملت المعالجة، بانتظار المراجعة البشرية")


def translation_task(c: "Container", project_id: str, job_id: str) -> None:
    """(Re)translate segments that are pending or failed. Ends in `awaiting_review`."""
    project = c.projects.get(project_id)
    all_segments = c.segments.for_project(project_id)
    if not all_segments:
        raise AppError(409, MSG["no_segments"])
    targets = [s for s in all_segments if s.get("translation_status") in ("pending", "failed", "translating")]
    c.jobs.update(job_id, JobStatus.TRANSLATING, 5, f"جارٍ ترجمة {len(targets)} مقطع...")
    c.translation.translate_many(
        project, targets, all_segments,
        progress=lambda d, t: c.jobs.update(job_id, progress=_scaled(5, 98, d, t), step=f"جارٍ الترجمة ({d}/{t})"))
    c.jobs.update(job_id, JobStatus.AWAITING_REVIEW, 100, "اكتملت الترجمة، بانتظار المراجعة البشرية")


def dubbing_task(c: "Container", project_id: str, job_id: str, force: bool = False) -> None:
    """Generate TTS for eligible segments. Ends in `completed`."""
    c.jobs.update(job_id, JobStatus.GENERATING_AUDIO, 5, "جارٍ توليد الصوت...")
    count = c.dubbing.generate_project(
        project_id, force=force,
        progress=lambda d, t: c.jobs.update(job_id, progress=_scaled(5, 98, d, t),
                                            step=f"جارٍ توليد الصوت: المقطع {d} من {t}"))
    c.repo.update(Tables.PROJECTS, project_id, {"status": "waiting_audio_review"})
    c.jobs.update(job_id, JobStatus.COMPLETED, 100, f"اكتمل توليد الصوت ({count} مقطع)")


def render_task(c: "Container", project_id: str, job_id: str) -> None:
    """Render the final dubbed video. Ends in `completed`."""
    project = c.projects.get(project_id)
    c.jobs.update(job_id, JobStatus.RENDERING_VIDEO, 10, "جارٍ إنشاء الفيديو المدبلج...")
    output = c.rendering.render(project, job_id)
    warnings = output.get("timing_warnings") or []
    step = "اكتمل إنشاء الفيديو المدبلج"
    if warnings:
        step += f" (تنبيه: {len(warnings)} مقطع صوته المعتمد أطول من مدته، استُخدم كما اعتُمد)"
    c.jobs.update(job_id, JobStatus.COMPLETED, 100, step)
