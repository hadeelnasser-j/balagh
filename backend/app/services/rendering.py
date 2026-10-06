"""Final dubbed video rendering.

The reviewer's audio approval is final. Timing differences never block rendering; they only
produce warnings. The only hard blocks are missing or unreadable audio files (and the human
review gates computed by the readiness rules).
"""
from __future__ import annotations

from pathlib import Path

from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.services.dubbing import DubbingService
from app.services.errors import MSG, conflict
from app.services.ffmpeg import DubClip, FFmpegService
from app.services.segments import SegmentRepository, audio_mode, needs_tts
from app.services.storage import StorageService


class RenderingService:
    def __init__(self, repo: DataRepository, segments: SegmentRepository, dubbing: DubbingService,
                 ffmpeg: FFmpegService, storage: StorageService, duck_volume: float = 0.0) -> None:
        self.repo = repo
        self.segments = segments
        self.dubbing = dubbing
        self.ffmpeg = ffmpeg
        self.storage = storage
        self.duck_volume = duck_volume

    # ------------------------------------------------------------------ checks
    def _audio_file(self, seg: Row) -> tuple[Path, float]:
        """Hard checks: the approved audio file must exist and be decodable."""
        n = seg["segment_index"] + 1
        path = self.storage.ensure_local(seg.get("dubbed_audio_path"))
        if path is None or not path.is_file() or path.stat().st_size == 0:
            raise conflict(MSG["audio_file_missing"].format(n=n), "audio_file_missing")
        duration = self.ffmpeg.probe_duration(path)
        if not duration or duration <= 0:
            raise conflict(MSG["audio_corrupted"].format(n=n), "audio_corrupted")
        return path, duration

    def assert_can_render(self, project_id: str) -> None:
        readiness = self.dubbing.readiness(project_id)
        if not readiness["render_ready"]:
            raise conflict(MSG["render_blocked"], "render_blocked")
        for seg in self.segments.for_project(project_id):
            if needs_tts(seg):
                self._audio_file(seg)

    # ------------------------------------------------------------------ plan
    def plan_clips(self, project: Row, ordered: list[Row]) -> tuple[list[DubClip], list[str]]:
        """Place every approved clip on the timeline without cutting it short.

        - A clip that fits its slot (up to the next segment) plays as approved (sped up when
          timing_status == "speedup").
        - A longer clip is sped up to fit, at most APPROVED_OVERFLOW_MAX_TEMPO. Whatever still does not
          fit runs on over the next segment and is reported as a warning.
        - It is never allowed to play over an original-audio (Quran) segment: there it is cut.
        """
        settings = self.dubbing.settings
        video_end = float(project.get("duration_seconds") or 0) or None
        clips: list[DubClip] = []
        warnings: list[str] = []
        for i, seg in enumerate(ordered):
            if audio_mode(seg) == "original":
                if seg.get("dubbed_audio_path"):
                    raise RuntimeError("Quran protection: an original-audio segment has synthesized audio")
                continue  # original audio (Quran / possible Quran) stays untouched
            if not needs_tts(seg):
                continue
            path, length = self._audio_file(seg)
            start = float(seg["start_time"])
            nxt = ordered[i + 1] if i + 1 < len(ordered) else None
            slot_end = float(nxt["start_time"]) if nxt else (video_end or float(seg["end_time"]))
            slot = max(0.1, slot_end - start)
            n = seg["segment_index"] + 1

            tempo = 1.0
            if length > slot:
                tempo = min(length / slot, max(settings.approved_overflow_max_tempo, settings.dubbing_max_tempo))
            played = length / tempo
            limit_end = slot_end
            if played > slot + 0.05:
                next_is_original = nxt is not None and audio_mode(nxt) == "original"
                if next_is_original:
                    warnings.append(f"segment_{n}: cut by {played - slot:.1f}s to avoid playing over quran audio")
                else:
                    limit_end = video_end or (start + played)
                    warnings.append(f"segment_{n}: approved audio runs {played - slot:.1f}s past its slot")
            clips.append(DubClip(path=path, start=start, window=max(0.1, limit_end - start), tempo=tempo,
                                 segment_end=float(seg["end_time"])))
        return clips, warnings

    # ------------------------------------------------------------------ render
    def render(self, project: Row, job_id: str | None = None) -> Row:
        project_id = project["id"]
        self.assert_can_render(project_id)
        video = self.storage.ensure_local(project.get("video_storage_path"))
        if video is None:
            raise conflict(MSG["video_missing"])
        ordered = self.segments.for_project(project_id)
        clips, warnings = self.plan_clips(project, ordered)
        audio_key = self.storage.project_key(project_id, "output", "dubbed_audio.m4a")
        video_key = self.storage.project_key(project_id, "output", "dubbed_video.mp4")
        self.ffmpeg.render_dubbed(video, clips, self.storage.path(audio_key), self.storage.path(video_key),
                                  duck_volume=self.duck_volume)
        self.storage.register(audio_key)
        self.storage.register(video_key)
        original_count = sum(1 for s in ordered if audio_mode(s) == "original")
        output = self.repo.insert(Tables.DUBBED_OUTPUTS, {
            "project_id": project_id, "job_id": job_id, "video_path": video_key, "audio_path": audio_key,
            "synthesized_segments": len(clips), "original_audio_segments": original_count,
            "duration_seconds": self.ffmpeg.probe_duration(self.storage.path(video_key)),
        })
        self.repo.update(Tables.PROJECTS, project_id, {"dubbed_video_path": video_key, "dubbed_audio_path": audio_key,
                                                       "status": "completed"})
        output["timing_warnings"] = warnings
        return output
