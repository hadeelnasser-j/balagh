"""Supabase table names and default row shapes.

The SQL that creates these tables lives in backend/supabase/migrations.
"""
from __future__ import annotations

from typing import Any


class Tables:
    PROJECTS = "projects"
    SEGMENTS = "video_segments"
    JOBS = "processing_jobs"
    SOURCE_MATCHES = "source_matches"
    AUDIO_REVIEWS = "audio_reviews"
    TRANSLATION_REVIEWS = "translation_reviews"
    DUBBED_OUTPUTS = "dubbed_outputs"
    MEANING_LOCKS = "meaning_locks"
    RECOVERED_SOURCES = "recovered_sources"

    ALL = (PROJECTS, SEGMENTS, JOBS, SOURCE_MATCHES, AUDIO_REVIEWS, TRANSLATION_REVIEWS,
           DUBBED_OUTPUTS, MEANING_LOCKS, RECOVERED_SOURCES)


def default_segment(project_id: str, index: int, start: float, end: float, text: str,
                    source_language: str, target_language: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "segment_index": index,
        "start_time": round(float(start), 3),
        "end_time": round(float(end), 3),
        "original_text": text,
        "translated_text": None,
        "edited_translation": None,
        "final_translation": None,
        "translation_status": "pending",
        "translation_warning": None,
        "translation_error": None,
        "review_status": "pending",
        "review_note": None,
        "needs_human_review": True,
        "source_language": source_language,
        "target_language": target_language,
        "content_type": "general",
        "source_verification_status": "pending",
        "source_review_status": "pending",
        "source_match_score": None,
        "reference": None,
        "verification_source": None,
        "translation_source": None,
        "translation_origin": None,
        "hadith_grade": None,
        "source_text": None,
        "source_url": None,
        "source_id": None,
        "quran_suspected": False,
        "detection_reason": None,
        "meaning_lock_status": "none",
        "text_verified": False,
        "translation_verified": False,
        "recitation_verified": False,
        "ready_for_dubbing": False,
        "dubbed_audio_path": None,
        "audio_duration": None,
        "timing_status": None,
        "tempo_factor": None,
        "audio_review_status": None,
    }
