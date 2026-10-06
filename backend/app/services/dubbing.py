"""Dubbing workflow: readiness rules, TTS generation, audio review and timing.

TTS eligibility (all required): approved, translated, verified, ready_for_dubbing,
non-quran, non-uncertain, has a final translation without Arabic script.
Quran segments are passthrough: their original recitation audio is kept.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from app.config import Settings
from app.models.enums import AudioReviewStatus, ContentType, TimingStatus
from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.services.arabic import contains_arabic
from app.services.errors import MSG, conflict
from app.services.ffmpeg import FFmpegService
from app.services.providers.base import TTSProvider
from app.services.segments import SegmentRepository, audio_mode, final_translation, is_quran, needs_tts
from app.services.storage import StorageService

logger = logging.getLogger(__name__)

AI_AUDIO_NOTICE = "هذا الصوت مُولَّد بالذكاء الاصطناعي. النصوص القرآنية تُحفَظ بصوتها الأصلي ولا يُعاد توليدها."


def generation_reasons(segment: Row) -> list[str]:
    """Reasons a TTS-required segment cannot be synthesized (empty = eligible)."""
    reasons: list[str] = []
    content = (segment.get("content_type") or "").lower()
    mode = audio_mode(segment)
    if mode == "blocked":
        return ["uncertain_needs_review"]
    if mode == "original":
        return []
    text = final_translation(segment)
    if segment.get("translation_status") != "translated":
        reasons.append("translation_not_translated")
    if segment.get("review_status") != "approved":
        reasons.append("translation_not_reviewed")
    if not segment.get("translation_verified"):
        reasons.append("translation_not_verified")
    if not segment.get("ready_for_dubbing"):
        reasons.append("not_ready_for_dubbing")
    if not text:
        reasons.append("translation_missing")
    elif (segment.get("target_language") or "en") != "ar" and contains_arabic(text):
        reasons.append("contains_arabic_text")
    if segment.get("source_review_status") == "rejected":
        reasons.append("source_rejected")
    if content == ContentType.HADITH.value and not segment.get("verification_source"):
        reasons.append("verification_source_missing")
    return reasons


def render_reasons(segment: Row) -> list[str]:
    if not needs_tts(segment):
        return []
    reasons: list[str] = []
    if not segment.get("dubbed_audio_path"):
        reasons.append("audio_missing")
    elif not segment.get("audio_duration"):
        reasons.append("audio_duration_missing")
    # Timing is advisory only: the reviewer's audio approval is final (see timing_warnings()).
    if segment.get("audio_review_status") != AudioReviewStatus.APPROVED.value:
        reasons.append("audio_not_approved")
    return reasons


def timing_warnings(segment: Row) -> list[str]:
    if needs_tts(segment) and segment.get("timing_status") == TimingStatus.OVERFLOW.value:
        return ["timing_overflow"]
    return []


def compute_readiness(segments: list[Row]) -> dict[str, Any]:
    """Per-segment readiness.

    Generation is gated PER SEGMENT: every eligible segment can get TTS even while another
    segment is still unsettled (e.g. uncertain). Unsettled segments block only the final render,
    so an uncertain segment is never dubbed and the video is never produced around it.
    `generation_blocking_reasons` is reserved for problems that leave nothing to generate.
    """
    pending: list[str] = []   # per-segment reasons a segment cannot be synthesized yet
    ren: list[str] = []
    info: list[str] = []
    warnings: list[str] = []  # advisory only (e.g. timing): shown, never blocking
    tts_required = passthrough = generated = approved = eligible = 0
    for s in segments:
        idx = s["segment_index"]
        mode = audio_mode(s)
        if mode == "original":
            passthrough += 1
            info.append(f"segment_{idx}:{'quran_original_audio' if is_quran(s) else 'reviewed_original_audio'}")
            continue
        g = generation_reasons(s)
        pending += [f"segment_{idx}:{r}" for r in g]
        if mode == "blocked":
            continue  # unapproved uncertain: never synthesized; blocks the render until the reviewer decides
        tts_required += 1
        if not g:
            eligible += 1
        if s.get("dubbed_audio_path") and s.get("audio_duration"):
            generated += 1
        if s.get("audio_review_status") == AudioReviewStatus.APPROVED.value:
            approved += 1
        ren += [f"segment_{idx}:{r}" for r in render_reasons(s)]
        warnings += [f"segment_{idx}:{w}" for w in timing_warnings(s)]
    gen: list[str] = []
    if not segments:
        gen.append("no_segments")
    elif tts_required > 0 and eligible == 0:
        gen = list(pending)  # nothing can be generated: show why
    generation_ready = eligible > 0
    render_blocking = pending + ren
    render_ready = bool(segments) and not render_blocking
    total = len(segments)
    return {
        "ready": generation_ready, "reasons": gen, "generation_ready": generation_ready, "render_ready": render_ready,
        "segments_total": total, "segments_ready": eligible + passthrough, "total_segments": total,
        "ready_segments": eligible + passthrough, "eligible_tts_segments": eligible, "passthrough_segments": passthrough,
        "tts_required_segments": tts_required, "generated_tts_segments": generated,
        "approved_tts_segments": approved, "blocking_reasons": gen + render_blocking,
        "generation_blocking_reasons": gen, "render_blocking_reasons": render_blocking,
        # Warnings are also listed in info_reasons so the existing dubbing screen displays them.
        "warning_reasons": warnings, "info_reasons": info + warnings,
    }


class DubbingService:
    def __init__(self, settings: Settings, repo: DataRepository, segments: SegmentRepository, tts: TTSProvider,
                 ffmpeg: FFmpegService, storage: StorageService) -> None:
        self.settings = settings
        self.repo = repo
        self.segments = segments
        self.tts = tts
        self.ffmpeg = ffmpeg
        self.storage = storage

    def readiness(self, project_id: str) -> dict[str, Any]:
        return compute_readiness(self.segments.for_project(project_id))

    def output_status(self, project_id: str) -> dict[str, Any]:
        """Whether the final dubbed video exists on disk, plus a version that changes on every render
        (the frontend appends it to the player URL so a new render is never hidden by a cached 404)."""
        project = self.repo.get(Tables.PROJECTS, project_id) or {}
        path = self.storage.ensure_local(project.get("dubbed_video_path"))
        if path is None or not path.is_file() or path.stat().st_size == 0:
            return {"dubbed_video_available": False, "dubbed_video_version": None}
        return {"dubbed_video_available": True, "dubbed_video_version": int(path.stat().st_mtime * 1000)}

    def assert_can_generate(self, project_id: str) -> dict[str, Any]:
        readiness = self.readiness(project_id)
        if not readiness["generation_ready"]:
            raise conflict(MSG["dubbing_blocked"], "dubbing_blocked")
        return readiness

    # ------------------------------------------------------------------ timing
    def _window(self, segment: Row, ordered: list[Row], video_duration: float | None) -> float:
        later = [s for s in ordered if s["segment_index"] > segment["segment_index"]]
        end = float(later[0]["start_time"]) if later else (video_duration or float(segment["end_time"]))
        return max(0.1, end - float(segment["start_time"]))

    def timing_for(self, duration: float, window: float) -> tuple[str, float]:
        ratio = duration / window if window > 0 else 99.0
        if ratio <= 1.0:
            return TimingStatus.OK.value, 1.0
        if ratio <= self.settings.dubbing_max_tempo:
            return TimingStatus.SPEEDUP.value, round(ratio, 4)
        return TimingStatus.OVERFLOW.value, round(ratio, 4)

    # ------------------------------------------------------------------ generation
    def generate_segment(self, segment_id: str, ordered: list[Row] | None = None,
                         video_duration: float | None = None) -> Row:
        segment = self.segments.get(segment_id)  # always re-read: content may have changed
        mode = audio_mode(segment)
        if mode == "original":
            raise conflict(MSG["quran_tts_forbidden"], "quran_tts_forbidden")
        if mode == "blocked":
            raise conflict(MSG["uncertain_tts_forbidden"], "uncertain_tts_forbidden")
        reasons = generation_reasons(segment)
        if reasons:
            raise conflict(f"{MSG['dubbing_blocked']} ({', '.join(reasons)})", "dubbing_blocked")
        text = final_translation(segment)
        project_id = segment["project_id"]
        if ordered is None:
            ordered = self.segments.for_project(project_id)
        if video_duration is None:
            project = self.repo.get(Tables.PROJECTS, project_id) or {}
            video_duration = project.get("duration_seconds")
        key = self.storage.project_key(project_id, "tts", f"seg_{segment['segment_index']:04d}_{segment_id[:8]}.mp3")
        produced = self.tts.synthesize(text, self.storage.path(key), language=segment.get("target_language") or "en")
        key = str(Path(key).with_suffix(produced.suffix).as_posix())
        self.storage.register(key)
        duration = self.ffmpeg.probe_duration(produced)
        timing, tempo = self.timing_for(duration or 0.0, self._window(segment, ordered, video_duration))
        updated = self.segments.update(segment_id, {
            "dubbed_audio_path": key, "audio_duration": duration, "timing_status": timing, "tempo_factor": tempo,
            "audio_review_status": AudioReviewStatus.PENDING.value,
        })
        self.repo.insert(Tables.AUDIO_REVIEWS, {"project_id": project_id, "segment_id": segment_id,
                                                "action": "generated", "audio_path": key, "audio_duration": duration})
        return updated

    def generate_project(self, project_id: str, force: bool = False,
                         progress: Callable[[int, int], None] | None = None) -> int:
        self.assert_can_generate(project_id)
        ordered = self.segments.for_project(project_id)
        project = self.repo.get(Tables.PROJECTS, project_id) or {}
        targets = [s for s in ordered if needs_tts(s) and not generation_reasons(s)
                   and (force or not s.get("dubbed_audio_path"))]
        done = 0

        def run(seg: Row) -> Row:
            return self.generate_segment(seg["id"], ordered, project.get("duration_seconds"))

        with ThreadPoolExecutor(max_workers=max(1, self.settings.max_tts_concurrency),
                                thread_name_prefix="balagh-tts") as pool:
            for _ in pool.map(run, targets):
                done += 1
                if progress:
                    progress(done, len(targets))
        return done

    # ------------------------------------------------------------------ review
    def approve_audio(self, project_id: str, segment_id: str, reviewer: str | None = None) -> Row:
        segment = self.segments.get(segment_id)
        if segment["project_id"] != project_id:
            raise conflict(MSG["segment_not_found"])
        if audio_mode(segment) == "original":
            raise conflict(MSG["quran_tts_forbidden"], "quran_tts_forbidden")
        if not segment.get("dubbed_audio_path") or not segment.get("audio_duration"):
            raise conflict(MSG["segment_audio_missing"], "audio_missing")
        self.repo.insert(Tables.AUDIO_REVIEWS, {"project_id": project_id, "segment_id": segment_id, "action": "approve",
                                                "audio_path": segment["dubbed_audio_path"],
                                                "audio_duration": segment["audio_duration"], "reviewed_by": reviewer})
        return self.segments.update(segment_id, {"audio_review_status": AudioReviewStatus.APPROVED.value})

    def reject_audio(self, project_id: str, segment_id: str, reviewer: str | None = None) -> Row:
        segment = self.segments.get(segment_id)
        if segment["project_id"] != project_id:
            raise conflict(MSG["segment_not_found"])
        self.repo.insert(Tables.AUDIO_REVIEWS, {"project_id": project_id, "segment_id": segment_id, "action": "reject",
                                                "audio_path": segment.get("dubbed_audio_path"),
                                                "audio_duration": segment.get("audio_duration"), "reviewed_by": reviewer})
        # Clearing the audio lets the dubbing screen regenerate it.
        return self.segments.update(segment_id, {"audio_review_status": AudioReviewStatus.REJECTED.value,
                                                 "dubbed_audio_path": None, "audio_duration": None,
                                                 "timing_status": None, "tempo_factor": None})

    def approve_all(self, project_id: str, reviewer: str | None = None) -> int:
        count = 0
        for s in self.segments.for_project(project_id):
            if needs_tts(s) and s.get("dubbed_audio_path") and s.get("audio_duration") and \
                    s.get("audio_review_status") != AudioReviewStatus.APPROVED.value:
                self.approve_audio(project_id, s["id"], reviewer)
                count += 1
        return count

    def segment_audio_path(self, project_id: str, segment_id: str) -> Path:
        segment = self.segments.get(segment_id)
        if segment["project_id"] != project_id or audio_mode(segment) == "original":
            raise conflict(MSG["segment_audio_missing"])
        local = self.storage.ensure_local(segment.get("dubbed_audio_path"))
        if local is None:
            raise conflict(MSG["segment_audio_missing"], "audio_missing")
        return local
