"""Human translation review: edit, approve, reject, re-translate."""
from __future__ import annotations

from typing import Any

from app.models.enums import ContentType, ReviewStatus, SourceReviewStatus, TranslationStatus
from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.services.arabic import contains_arabic
from app.services.errors import MSG, bad_request, conflict
from app.services.meaning_locks import MeaningLockService
from app.services.segments import SegmentRepository, final_translation, is_quran
from app.services.translation import TranslationService


class ReviewService:
    def __init__(self, repo: DataRepository, segments: SegmentRepository, locks: MeaningLockService,
                 translation: TranslationService) -> None:
        self.repo = repo
        self.segments = segments
        self.locks = locks
        self.translation = translation

    def _log(self, segment: Row, action: str, previous: str | None, new: str | None, note: str | None,
             reviewer: str | None) -> None:
        self.repo.insert(Tables.TRANSLATION_REVIEWS, {
            "project_id": segment["project_id"], "segment_id": segment["id"], "action": action,
            "previous_translation": previous, "new_translation": new, "note": note, "reviewed_by": reviewer,
        })

    def edit(self, segment_id: str, edited: str | None, note: str | None = None,
             content_type: str | None = None, reviewer: str | None = None) -> Row:
        segment = self.segments.get(segment_id)
        patch: Row = {}
        if content_type is not None and content_type != segment.get("content_type"):
            if is_quran(segment):
                raise conflict("لا يمكن تغيير تصنيف مقطع قرآني موثّق يدويًا. استخدم رفض المطابقة المرجعية.")
            patch.update({"content_type": content_type, "review_status": ReviewStatus.PENDING.value,
                          "translation_verified": False, "ready_for_dubbing": False})
            if content_type == ContentType.GENERAL.value:
                patch["quran_suspected"] = False
            self._log(segment, "content_type_change", segment.get("content_type"), content_type, note, reviewer)
        if edited is not None:
            if is_quran(segment):
                raise conflict(MSG["quran_edit_forbidden"], "quran_edit_forbidden")
            text = edited.strip()
            if not text:
                raise bad_request(MSG["empty_translation"])
            previous = final_translation(segment) or None
            patch.update({
                "edited_translation": text, "final_translation": text,
                "review_status": ReviewStatus.EDITED.value, "translation_verified": False, "ready_for_dubbing": False,
                "needs_human_review": True, "translation_error": None,
                # Changing the words invalidates previously generated speech.
                "dubbed_audio_path": None, "audio_duration": None, "audio_review_status": None, "timing_status": None,
            })
            if segment.get("translation_status") != TranslationStatus.TRANSLATED.value or not segment.get("translated_text"):
                patch.update({"translation_status": TranslationStatus.TRANSLATED.value,
                              "translation_source": "Human reviewer", "translation_origin": "human_reviewer"})
            self._log(segment, "edit", previous, text, note, reviewer)
        if note is not None:
            patch["review_note"] = note
        if not patch:
            return segment
        updated = self.segments.update(segment_id, patch)
        if edited is not None:
            status = self.locks.refresh(updated, final_translation(updated))
            updated = self.segments.update(segment_id, {"meaning_lock_status": status})
        return updated

    def approve(self, segment_id: str, note: str | None = None, reviewer: str | None = None) -> Row:
        segment = self.segments.get(segment_id)
        text = final_translation(segment)
        if not text:
            raise conflict(MSG["empty_translation"], "translation_missing")
        target = (segment.get("target_language") or "en").lower()
        if target != "ar" and contains_arabic(text):
            raise conflict(MSG["arabic_in_translation"], "contains_arabic_text")
        patch: Row = {
            "review_status": ReviewStatus.APPROVED.value, "translation_verified": True, "ready_for_dubbing": True,
            "needs_human_review": False, "final_translation": text,
            "translation_status": TranslationStatus.TRANSLATED.value,
        }
        if segment.get("source_review_status") == SourceReviewStatus.PENDING.value and \
                segment.get("source_verification_status") == "verified":
            patch["source_review_status"] = SourceReviewStatus.APPROVED.value
        if segment.get("source_review_status") == SourceReviewStatus.REJECTED.value:
            patch["ready_for_dubbing"] = False
        if note is not None:
            patch["review_note"] = note
        self.locks.approve_pending(segment_id)
        patch["meaning_lock_status"] = self.locks.status_for(segment_id)
        self._log(segment, "approve", text, text, note, reviewer)
        return self.segments.update(segment_id, patch)

    def reject(self, segment_id: str, note: str | None = None, reviewer: str | None = None) -> Row:
        segment = self.segments.get(segment_id)
        patch: Row = {"review_status": ReviewStatus.REJECTED.value, "translation_verified": False,
                      "ready_for_dubbing": False, "needs_human_review": True,
                      "dubbed_audio_path": None, "audio_duration": None, "audio_review_status": None}
        if note is not None:
            patch["review_note"] = note
        self._log(segment, "reject", final_translation(segment) or None, None, note, reviewer)
        return self.segments.update(segment_id, patch)

    def retranslate(self, segment_id: str) -> Row:
        segment = self.segments.get(segment_id)
        project = self.repo.get(Tables.PROJECTS, segment["project_id"]) or {}
        all_segments = {s["segment_index"]: s for s in self.segments.for_project(segment["project_id"])}
        prev_seg = all_segments.get(segment["segment_index"] - 1)
        next_seg = all_segments.get(segment["segment_index"] + 1)
        updated = self.translation.translate_segment(
            segment, project, (prev_seg and prev_seg["original_text"], next_seg and next_seg["original_text"]))
        self._log(segment, "retranslate", final_translation(segment) or None, updated.get("translated_text"), None, None)
        return updated

    def summary(self, project_id: str) -> dict[str, Any]:
        from app.services.segments import review_summary
        return review_summary(self.segments.for_project(project_id))
