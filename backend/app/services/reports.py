"""Pipeline status and reports consumed by the wizard, review and dubbing screens."""
from __future__ import annotations

from typing import Any

from app.models.enums import JobType
from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.repositories.local_sources import LocalSourcesRepository
from app.services.dubbing import AI_AUDIO_NOTICE, compute_readiness
from app.services.jobs import TERMINAL, JobManager, job_out
from app.services.segments import (
    SegmentRepository, audio_mode, final_translation, is_reviewer_resolved, needs_tts,
)
from app.services.storage import StorageService


class ReportService:
    def __init__(self, repo: DataRepository, segments: SegmentRepository, jobs: JobManager,
                 storage: StorageService, sources: LocalSourcesRepository) -> None:
        self.repo = repo
        self.segments = segments
        self.jobs = jobs
        self.storage = storage
        self.sources = sources

    def _dubbed_available(self, project: Row) -> bool:
        return bool(project.get("dubbed_video_path")) and self.storage.ensure_local(project["dubbed_video_path"]) is not None

    def pipeline_status(self, project: Row) -> dict[str, bool]:
        segments = self.segments.for_project(project["id"])
        active_types = {j["job_type"] for j in self.jobs.active_jobs(project["id"])}
        upload = bool(project.get("video_storage_path") and project.get("audio_storage_path"))
        # A translation retry from the review screen must not lock the wizard out of the review step.
        transcription = upload and bool(segments) and JobType.TRANSCRIPTION.value not in active_types
        review = transcription and all(
            s.get("review_status") == "approved" and s.get("translation_verified") and final_translation(s)
            for s in segments)
        verification = review and all(
            s.get("ready_for_dubbing") and s.get("source_review_status") != "rejected" for s in segments)
        readiness = compute_readiness(segments) if segments else None
        quran_only = bool(readiness) and readiness["tts_required_segments"] == 0 and not readiness["render_blocking_reasons"]
        dubbing = verification and (self._dubbed_available(project) or quran_only)
        return {"project": True, "upload": upload, "transcription": transcription, "review": review,
                "verification": verification, "dubbing": dubbing, "report": dubbing}

    def integrity_report(self, project: Row) -> dict[str, Any]:
        """Everything the report screen shows: stats, Quran/Hadith summaries, uncertain segments,
        dubbing readiness and the final validation checklist. Original top-level fields are kept."""
        segments = self.segments.for_project(project["id"])
        attributions = [
            {"segment_id": s["id"], "segment_index": s["segment_index"], "content_type": s.get("content_type"),
             "reference": s.get("reference"), "translation_source": s.get("translation_source"),
             "translation_origin": s.get("translation_origin"), "verification_source": s.get("verification_source"),
             "hadith_grade": s.get("hadith_grade"), "source_url": s.get("source_url")}
            for s in segments if s.get("content_type") in ("quran", "hadith", "uncertain")
        ]
        readiness = compute_readiness(segments)
        by_type = {t: [s for s in segments if s.get("content_type") == t] for t in ("quran", "hadith", "general", "uncertain")}
        quran, hadith = by_type["quran"], by_type["hadith"]
        uncertain = [s for s in by_type["uncertain"] if not is_reviewer_resolved(s)]  # reviewer decision wins
        resolved = [s for s in by_type["uncertain"] if is_reviewer_resolved(s)]
        quran_sent_to_tts = sum(1 for s in quran if s.get("dubbed_audio_path"))
        dubbed_available = self._dubbed_available(project)
        tts_segments = [s for s in segments if needs_tts(s)]

        def seg_ref(s: Row) -> dict[str, Any]:
            return {"segment_id": s["id"], "segment_index": s["segment_index"], "start_time": s.get("start_time"),
                    "end_time": s.get("end_time"), "original_text": s.get("original_text"),
                    "final_translation": final_translation(s) or None, "reference": s.get("reference"),
                    "score": s.get("source_match_score"), "verification_status": s.get("source_verification_status"),
                    "translation_source": s.get("translation_source"), "translation_origin": s.get("translation_origin"),
                    "hadith_grade": s.get("hadith_grade"), "source_url": s.get("source_url"),
                    "review_status": s.get("review_status")}

        def check(key: str, label: str, passed: bool, detail: str | None = None,
                  severity: str = "required") -> dict[str, Any]:
            return {"key": key, "label": label, "passed": bool(passed), "detail": detail, "severity": severity}

        checks = [
            check("segments_present", "توجد مقاطع مفرغة في المشروع", bool(segments)),
            check("all_reviewed", "جميع الترجمات معتمدة بشريًا",
                  bool(segments) and all(s.get("review_status") == "approved" for s in segments),
                  f"{sum(1 for s in segments if s.get('review_status') == 'approved')}/{len(segments)}"),
            check("quran_official_translation", "ترجمة الآيات من QuranEnc فقط",
                  all(s.get("translation_origin") == "quranenc_local_official" for s in quran), f"{len(quran)} آية"),
            check("quran_not_dubbed", "لم يُرسل أي نص قرآني إلى توليد الصوت", quran_sent_to_tts == 0,
                  f"{quran_sent_to_tts} مقطع"),
            check("sources_attributed", "كل آية وحديث موثق مرفق بمصدره",
                  all(s.get("reference") and s.get("verification_source") for s in quran + hadith)),
            check("no_uncertain", "لا توجد مقاطع غير محسومة", not uncertain, f"{len(uncertain)} مقطع"),
            check("tts_audio_approved", "جميع الأصوات المولدة معتمدة",
                  all(s.get("audio_review_status") == "approved" for s in tts_segments),
                  f"{sum(1 for s in tts_segments if s.get('audio_review_status') == 'approved')}/{len(tts_segments)}"),
            check("timing_valid", "توقيت الصوت المولد ضمن مدة كل مقطع (تنبيه فقط؛ اعتماد الصوت هو القرار النهائي)",
                  not any(s.get("timing_status") == "overflow" for s in tts_segments),
                  f"{sum(1 for s in tts_segments if s.get('timing_status') == 'overflow')} مقطع أطول من مدته",
                  severity="warning"),
            check("subtitles_generated", "ملف الترجمة SRT منشأ", bool(project.get("srt_storage_path"))),
            check("dubbed_video", "الفيديو المدبلج النهائي متاح",
                  dubbed_available or (bool(segments) and not tts_segments and not uncertain)),
        ]
        return {
            "project_id": project["id"], "total_segments": len(segments),
            "synthesized_segments": sum(1 for s in segments if s.get("dubbed_audio_path")),
            "original_audio_segments": sum(1 for s in segments if audio_mode(s) == "original"),
            "religious_segments": len(attributions),
            "approved_audio_segments": sum(1 for s in segments if s.get("audio_review_status") == "approved"),
            "ready_for_dubbing": readiness["render_ready"],
            "dubbed_video_available": dubbed_available,
            "ai_generated_audio_notice": AI_AUDIO_NOTICE,
            "quran_sent_to_tts": quran_sent_to_tts,
            "attributions": attributions,
            "project": {
                "title": project.get("title"), "status": project.get("status"),
                "dubbing_mode": project.get("dubbing_mode"), "source_language": project.get("source_language"),
                "target_language": project.get("target_language"), "duration_seconds": project.get("duration_seconds"),
                "created_at": project.get("created_at"), "srt_available": bool(project.get("srt_storage_path")),
            },
            "content_counts": {t: len(v) for t, v in by_type.items()},
            "quran_summary": {
                "count": len(quran),
                "verified": sum(1 for s in quran if s.get("source_verification_status") == "verified"),
                "original_audio_preserved": len(quran) - quran_sent_to_tts,
                "items": [seg_ref(s) for s in quran],
            },
            "hadith_summary": {
                "count": len(hadith),
                "verified": sum(1 for s in hadith if s.get("source_verification_status") == "verified"),
                "official_translations": sum(1 for s in hadith if s.get("translation_origin") == "hadeethenc_official"),
                "ai_drafts": sum(1 for s in hadith if (s.get("translation_origin") or "").endswith("_draft")),
                "items": [seg_ref(s) for s in hadith],
            },
            "uncertain_segments": [
                {**seg_ref(s), "reason": s.get("detection_reason"), "quran_suspected": bool(s.get("quran_suspected"))}
                for s in uncertain
            ],
            "reviewer_resolved_segments": [
                {**seg_ref(s), "reason": s.get("detection_reason"), "audio_mode": audio_mode(s)} for s in resolved
            ],
            "dubbing": {k: readiness[k] for k in (
                "generation_ready", "render_ready", "tts_required_segments", "generated_tts_segments",
                "approved_tts_segments", "passthrough_segments", "generation_blocking_reasons",
                "render_blocking_reasons")},
            # Warnings are reported but never fail the final validation.
            "validation": {"passed": all(c["passed"] for c in checks if c["severity"] == "required"),
                           "checks": checks},
        }

    def dubbing_status(self, project: Row) -> dict[str, Any]:
        segments = self.segments.for_project(project["id"])
        readiness = compute_readiness(segments)
        dub_job = self.jobs.latest(project["id"], JobType.DUBBING)
        render_job = self.jobs.latest(project["id"], JobType.RENDERING)
        return {
            "project_id": project["id"],
            "dubbing_job": job_out(dub_job) if dub_job else None,
            "render_job": job_out(render_job) if render_job else None,
            "is_generating": bool(dub_job and dub_job["status"] not in TERMINAL),
            "is_rendering": bool(render_job and render_job["status"] not in TERMINAL),
            "tts_required_segments": readiness["tts_required_segments"],
            "generated_tts_segments": readiness["generated_tts_segments"],
            "approved_tts_segments": readiness["approved_tts_segments"],
            "passthrough_segments": readiness["passthrough_segments"],
            "generation_ready": readiness["generation_ready"], "render_ready": readiness["render_ready"],
            "dubbed_video_available": self._dubbed_available(project),
        }

    def dubbing_report(self, project: Row) -> dict[str, Any]:
        segments = self.segments.for_project(project["id"])
        rows = []
        for s in segments:
            mode = {"original": "original_audio"}.get(audio_mode(s), audio_mode(s))
            rows.append({
                "segment_id": s["id"], "segment_index": s["segment_index"], "start_time": s["start_time"],
                "end_time": s["end_time"], "content_type": s.get("content_type"), "audio_mode": mode,
                "final_translation": final_translation(s) or None, "reference": s.get("reference"),
                "translation_source": s.get("translation_source"), "translation_origin": s.get("translation_origin"),
                "audio_duration": s.get("audio_duration"), "timing_status": s.get("timing_status"),
                "tempo_factor": s.get("tempo_factor"), "audio_review_status": s.get("audio_review_status"),
            })
        outputs = self.repo.list(Tables.DUBBED_OUTPUTS, {"project_id": project["id"]}, order_by="created_at",
                                 desc=True, limit=1)
        return {"project_id": project["id"], "dubbing_mode": project.get("dubbing_mode"),
                "ai_generated_audio_notice": AI_AUDIO_NOTICE, "segments": rows,
                "latest_output": outputs[0] if outputs else None}

    def sources_status(self) -> dict[str, Any]:
        stats = self.sources.stats()
        ayahs, hadiths = stats["quran_ayahs"], stats["hadiths"]
        return {
            "sources": stats["available"],
            "approved_sources_count": int(ayahs > 0) + int(hadiths > 0),
            "documents_count": ayahs + hadiths, "passages_count": ayahs + hadiths,
            "chunks_count": ayahs + hadiths, "quran_ayahs": ayahs, "hadiths": hadiths,
            "quran_with_translation": stats["quran_with_translation"],
            "hadiths_with_translation": stats["hadiths_with_translation"],
            "database_path": stats["database_path"], "error": stats["error"],
        }
