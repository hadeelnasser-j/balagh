"""Pydantic request/response schemas.

Field names and shapes mirror frontend/src/services/api.ts exactly.
Extra fields are allowed on responses so the frontend can read optional data.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Out(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)


# ---------------------------------------------------------------- health
class HealthStatus(_Out):
    status: str
    supabase: str
    ffmpeg: str
    ffprobe: str
    transcription_provider: str
    translation_provider: str
    tts_provider: str
    openai_configured: bool
    gemini_configured: bool
    sources_database: str
    data_backend: str


# ---------------------------------------------------------------- projects
class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    source_language: str = Field(default="ar", min_length=2, max_length=10)
    target_language: str = Field(default="en", min_length=2, max_length=10)
    dubbing_mode: Literal["faithful", "timed", "simplified"] = "timed"


class LatestJob(_Out):
    job_id: str
    job_type: str
    status: str


class ProjectOut(_Out):
    id: str
    title: str
    source_language: str
    target_language: str
    dubbing_mode: str
    status: str
    srt_storage_path: str | None = None
    video_storage_path: str | None = None
    audio_storage_path: str | None = None
    dubbed_video_path: str | None = None
    duration_seconds: float | None = None
    latest_job: LatestJob | None = None
    created_at: str | None = None


# ---------------------------------------------------------------- jobs
class ProcessingJobOut(_Out):
    job_id: str
    project_id: str
    job_type: str
    status: str
    progress: int
    current_step: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------- segments
class SegmentOut(_Out):
    id: str
    project_id: str
    segment_index: int
    start_time: float
    end_time: float
    original_text: str
    translated_text: str | None = None
    edited_translation: str | None = None
    final_translation: str | None = None
    translation_status: str
    translation_warning: str | None = None
    review_status: str
    translation_error: str | None = None
    review_note: str | None = None
    source_language: str | None = None
    target_language: str
    content_type: str | None = None
    source_verification_status: str | None = None
    source_review_status: str | None = None
    source_match_score: float | None = None
    reference: str | None = None
    verification_source: str | None = None
    translation_source: str | None = None
    translation_origin: str | None = None
    hadith_grade: str | None = None
    meaning_lock_status: str | None = None
    text_verified: bool = False
    translation_verified: bool = False
    recitation_verified: bool = False
    ready_for_dubbing: bool = False
    needs_human_review: bool = True
    dubbed_audio_path: str | None = None
    audio_duration: float | None = None
    timing_status: str | None = None
    audio_review_status: str | None = None


class SegmentPage(_Out):
    project_id: str
    total: int
    page: int
    page_size: int
    items: list[SegmentOut]


class SegmentPatch(BaseModel):
    edited_translation: str | None = Field(default=None, max_length=5000)
    review_note: str | None = Field(default=None, max_length=2000)
    # Lets a reviewer resolve an "uncertain" segment. Quran can only be set via
    # an approved source match, never by free edit.
    content_type: Literal["general", "hadith"] | None = None
    reviewed_by: str | None = None


class ReviewAction(BaseModel):
    review_note: str | None = None
    reviewed_by: str | None = None


class ReviewSummary(_Out):
    total_segments: int
    translated_segments: int
    failed_segments: int
    pending_review: int
    edited_segments: int
    approved_segments: int
    rejected_segments: int = 0
    can_generate_srt: bool
    can_generate_final_srt: bool = False


# ---------------------------------------------------------------- sources
class SourceMatchOut(_Out):
    id: str | None
    segment_id: str | None
    source_id: str
    source_name: str | None = None
    title: str | None = None
    reference_key: str | None = None
    exact_quote: str | None = None
    url: str | None = None
    match_type: str
    match_score: float
    status: str


class ReviewerBody(BaseModel):
    reviewed_by: str = Field(default="reviewer", max_length=200)


class MeaningLockOut(_Out):
    id: str
    segment_id: str
    original_span: str
    translated_span: str | None = None
    lock_type: str
    risk_level: str
    review_status: str


class MeaningLockPatch(BaseModel):
    review_status: Literal["approved", "rejected"]


class SourceSummary(_Out):
    project_id: str
    total_segments: int
    religious_segments: int
    verified: int
    candidate: int
    not_found: int
    conflict: int
    pending: int
    pending_locks: int
    ready_for_dubbing: int
    blocked_reasons: dict[str, list[str]]


class DubbingCheck(_Out):
    project_id: str
    ready: bool
    segments_total: int
    segments_ready: int


class RecoveredSourceOut(_Out):
    id: str
    type: str
    source: str
    reference: str | None = None
    section: str | None = None
    segment_id: str | None = None
    confidence: float
    full_text: str
    status: str


class RecoverSourcesResult(_Out):
    threshold: float
    recovered: list[RecoveredSourceOut]
    candidates: list[RecoveredSourceOut]
    detected_count: int


class RecoveredReviewBody(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewed_by: str = Field(default="reviewer", max_length=200)


class SourcesStatus(_Out):
    sources: bool
    approved_sources_count: int
    documents_count: int
    passages_count: int
    chunks_count: int
    quran_ayahs: int = 0
    hadiths: int = 0
    database_path: str | None = None


class PipelineStatus(_Out):
    project: bool
    upload: bool
    transcription: bool
    review: bool
    verification: bool
    dubbing: bool
    report: bool


# ---------------------------------------------------------------- dubbing
class DubbingReadiness(_Out):
    dubbed_video_available: bool = False
    dubbed_video_version: int | None = None
    ready: bool
    reasons: list[str]
    generation_ready: bool
    render_ready: bool
    segments_total: int
    segments_ready: int
    total_segments: int
    ready_segments: int
    passthrough_segments: int
    tts_required_segments: int
    generated_tts_segments: int
    approved_tts_segments: int
    blocking_reasons: list[str]
    generation_blocking_reasons: list[str]
    render_blocking_reasons: list[str]
    info_reasons: list[str]


class JobRef(_Out):
    job_id: str
    status: str | None = None
    reused: bool = False


class IntegrityReport(_Out):
    project_id: str
    total_segments: int
    synthesized_segments: int
    original_audio_segments: int
    religious_segments: int
    approved_audio_segments: int
    ready_for_dubbing: bool
    dubbed_video_available: bool
    ai_generated_audio_notice: str
    quran_sent_to_tts: int = 0
    attributions: list[dict[str, Any]] = Field(default_factory=list)


class SrtResult(_Out):
    project_id: str
    srt_storage_path: str
    mode: str
    segments: int
