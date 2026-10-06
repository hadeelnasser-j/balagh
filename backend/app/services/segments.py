"""Segment helpers: loading, output shaping and summary counts."""
from __future__ import annotations

from typing import Any

from app.models.enums import ContentType
from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.services.errors import MSG, not_found

# Internal columns that the frontend does not need.
_HIDDEN = {"source_text", "quran_suspected", "detection_reason", "tempo_factor"}


def final_translation(segment: Row) -> str:
    return ((segment.get("edited_translation") or segment.get("translated_text") or "")).strip()


def segment_out(segment: Row) -> dict[str, Any]:
    out = {k: v for k, v in segment.items() if k not in _HIDDEN}
    out["final_translation"] = segment.get("final_translation") or (final_translation(segment) or None)
    out["audio_mode"] = audio_mode(segment)
    return out


def is_quran(segment: Row) -> bool:
    return (segment.get("content_type") or "").lower() == ContentType.QURAN.value


def is_reviewer_resolved(segment: Row) -> bool:
    """An uncertain segment the reviewer explicitly approved. Approval is the final decision;
    rejecting or editing the segment afterwards revokes it (review_status leaves "approved")."""
    return ((segment.get("content_type") or "").lower() == ContentType.UNCERTAIN.value
            and segment.get("review_status") == "approved")


def audio_mode(segment: Row) -> str:
    """How the segment sounds in the final video — the backend's single source of truth.

    original: original audio kept (Quran, or a reviewer-approved segment that may contain Quran)
    tts:      synthesized from the approved translation
    blocked:  uncertain and not yet approved by a reviewer (blocks the final render)
    """
    content = (segment.get("content_type") or "").lower()
    if content == ContentType.QURAN.value:
        return "original"
    if content == ContentType.UNCERTAIN.value:
        if not is_reviewer_resolved(segment):
            return "blocked"
        # Quran protection outranks dubbing: possible Quran is never synthesized, even after approval.
        return "original" if segment.get("quran_suspected") else "tts"
    return "tts"


def needs_tts(segment: Row) -> bool:
    return audio_mode(segment) == "tts"


class SegmentRepository:
    """Thin convenience layer over the video_segments table."""

    def __init__(self, repo: DataRepository) -> None:
        self.repo = repo

    def get(self, segment_id: str) -> Row:
        segment = self.repo.get(Tables.SEGMENTS, segment_id)
        if not segment:
            raise not_found(MSG["segment_not_found"])
        return segment

    def for_project(self, project_id: str) -> list[Row]:
        return self.repo.list(Tables.SEGMENTS, {"project_id": project_id}, order_by="segment_index")

    def page(self, project_id: str, page: int, page_size: int) -> tuple[int, list[Row]]:
        total = self.repo.count(Tables.SEGMENTS, {"project_id": project_id})
        items = self.repo.list(Tables.SEGMENTS, {"project_id": project_id}, order_by="segment_index",
                               limit=page_size, offset=(page - 1) * page_size)
        return total, items

    def update(self, segment_id: str, patch: Row) -> Row:
        if patch.get("content_type") == ContentType.QURAN.value or (
            "dubbed_audio_path" in patch and patch["dubbed_audio_path"]
        ):
            current = self.repo.get(Tables.SEGMENTS, segment_id) or {}
            merged = {**current, **patch}
            if is_quran(merged) and merged.get("dubbed_audio_path"):
                raise RuntimeError("Quran protection: a Quran segment can never hold synthesized audio")
        return self.repo.update(Tables.SEGMENTS, segment_id, patch)


def review_summary(segments: list[Row]) -> dict[str, Any]:
    total = len(segments)
    translated = sum(1 for s in segments if s.get("translation_status") == "translated")
    failed = sum(1 for s in segments if s.get("translation_status") == "failed")
    approved = sum(1 for s in segments if s.get("review_status") == "approved")
    edited = sum(1 for s in segments if s.get("review_status") == "edited")
    rejected = sum(1 for s in segments if s.get("review_status") == "rejected")
    pending = sum(1 for s in segments if s.get("review_status") in ("pending", "edited"))
    with_text = sum(1 for s in segments if final_translation(s))
    return {
        "total_segments": total,
        "translated_segments": translated,
        "failed_segments": failed,
        "pending_review": pending,
        "edited_segments": edited,
        "approved_segments": approved,
        "rejected_segments": rejected,
        "can_generate_srt": total > 0 and with_text > 0,
        "can_generate_final_srt": total > 0 and approved == total and with_text == total,
    }
