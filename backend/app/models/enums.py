"""Domain enumerations shared by services, repositories and API schemas."""
from __future__ import annotations

from enum import StrEnum


class ContentType(StrEnum):
    QURAN = "quran"
    HADITH = "hadith"
    GENERAL = "general"
    UNCERTAIN = "uncertain"


class JobType(StrEnum):
    UPLOAD = "upload"            # upload + audio extraction
    TRANSCRIPTION = "transcription"
    TRANSLATION = "translation"
    DUBBING = "dubbing"
    RENDERING = "rendering"


class JobStatus(StrEnum):
    QUEUED = "queued"
    UPLOADED = "uploaded"
    EXTRACTING_AUDIO = "extracting_audio"
    AUDIO_EXTRACTED = "audio_extracted"        # terminal for upload jobs (UI waits on it)
    TRANSCRIBING = "transcribing"
    DETECTING_CONTENT = "detecting_content"
    VERIFYING_SOURCES = "verifying_sources"
    TRANSLATING = "translating"
    AWAITING_REVIEW = "awaiting_review"        # terminal for transcription/translation jobs
    SRT_GENERATED = "srt_generated"
    GENERATING_AUDIO = "generating_audio"
    RENDERING_VIDEO = "rendering_video"        # NOT "rendering": the UI treats that as finished
    COMPLETED = "completed"
    FAILED = "failed"


TERMINAL_JOB_STATUSES = frozenset({
    JobStatus.AUDIO_EXTRACTED, JobStatus.AWAITING_REVIEW, JobStatus.SRT_GENERATED,
    JobStatus.COMPLETED, JobStatus.FAILED,
})


class TranslationStatus(StrEnum):
    PENDING = "pending"
    TRANSLATING = "translating"
    TRANSLATED = "translated"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    EDITED = "edited"
    APPROVED = "approved"
    REJECTED = "rejected"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    REJECTED = "rejected"


class SourceReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MatchStatus(StrEnum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    REJECTED = "rejected"
    CONFLICT = "conflict"


class RecoveredStatus(StrEnum):
    RECOVERED = "recovered"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"


class AudioReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TimingStatus(StrEnum):
    OK = "ok"                # fits the available window as-is
    SPEEDUP = "speedup"      # fits after tempo adjustment <= DUBBING_MAX_TEMPO
    OVERFLOW = "overflow"    # does not fit: blocks rendering
    PASSTHROUGH = "passthrough"  # original audio kept (Quran)


class DubbingMode(StrEnum):
    FAITHFUL = "faithful"
    TIMED = "timed"
    SIMPLIFIED = "simplified"


# Translation provenance (values are matched by the frontend badges).
class TranslationOrigin(StrEnum):
    QURANENC = "quranenc_local_official"
    HADEETHENC = "hadeethenc_official"
    OPENAI_CONSTRAINED = "openai_constrained_draft"
    OPENAI_UNVERIFIED = "openai_unverified_draft"
    OPENAI_GENERAL = "openai_general"
    GEMINI_CONSTRAINED = "gemini_constrained_draft"
    GEMINI_UNVERIFIED = "gemini_unverified_draft"
    GEMINI_GENERAL = "gemini_general"
    HUMAN = "human_reviewer"


TRANSLATION_SOURCE_QURANENC = "QuranEnc Local"
TRANSLATION_SOURCE_HADEETHENC = "HadeethEnc"
VERIFICATION_SOURCE_LOCAL = "LocalSQLite"
