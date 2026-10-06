"""Source verification: content detection, source matches, recovery and human source review."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.models.enums import (
    VERIFICATION_SOURCE_LOCAL, ContentType, MatchStatus, RecoveredStatus, SourceReviewStatus, VerificationStatus,
)
from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.repositories.local_sources import LocalSourcesRepository, SourceCandidate, SourceEntry
from app.services.content_detection import ContentDetector, Detection
from app.services.errors import MSG, conflict, not_found
from app.services.segments import SegmentRepository, final_translation
from app.services.translation import TranslationService

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def match_out(row: Row) -> dict[str, Any]:
    return {
        "id": row.get("id"), "segment_id": row.get("segment_id"), "source_id": row["source_id"],
        "source_name": row.get("source_name"), "title": row.get("title"), "reference_key": row.get("reference_key"),
        "exact_quote": row.get("exact_quote"), "url": row.get("url"), "match_type": row["match_type"],
        "match_score": float(row["match_score"]), "status": row["status"], "source_type": row.get("source_type"),
        "translation": row.get("translation"), "translation_source": row.get("translation_source"),
        "hadith_grade": row.get("hadith_grade"),
    }


def recovered_out(row: Row) -> dict[str, Any]:
    return {
        "id": row["id"], "type": row["type"], "source": row["source"], "reference": row.get("reference"),
        "section": row.get("section"), "segment_id": row.get("segment_id"), "confidence": float(row["confidence"]),
        "full_text": row["full_text"], "status": row["status"], "translation": row.get("translation"),
    }


class VerificationService:
    def __init__(self, settings: Settings, repo: DataRepository, sources: LocalSourcesRepository,
                 detector: ContentDetector, segments: SegmentRepository, translation: TranslationService) -> None:
        self.settings = settings
        self.repo = repo
        self.sources = sources
        self.detector = detector
        self.segments = segments
        self.translation = translation

    # ------------------------------------------------------------------ detection
    def detection_patch(self, det: Detection) -> Row:
        best = det.best
        verified = det.verification_status == VerificationStatus.VERIFIED
        entry = best.entry if best else None
        return {
            "content_type": det.content_type.value,
            "source_verification_status": det.verification_status.value,
            "source_review_status": SourceReviewStatus.PENDING.value,
            "source_match_score": round(best.score, 4) if best else None,
            "source_id": entry.source_id if entry else None,
            "reference": entry.reference if entry and (verified or det.content_type == ContentType.UNCERTAIN) else None,
            "verification_source": VERIFICATION_SOURCE_LOCAL if verified else None,
            "hadith_grade": entry.grade if entry and entry.kind == "hadith" else None,
            "source_text": entry.text if entry else None,
            "source_url": entry.url if entry else None,
            "text_verified": verified,
            "recitation_verified": verified and det.content_type == ContentType.QURAN,
            "quran_suspected": det.quran_suspected,
            "detection_reason": det.reason,
        }

    def _match_rows(self, segment: Row, det: Detection) -> list[Row]:
        rows: list[Row] = []
        best_id = det.best.entry.source_id if det.best else None
        for cand in det.all_candidates:
            # Sub-threshold scores never become source matches; embedded (mixed) matches only
            # when the detector accepted them as the segment's source.
            if cand.score < self._threshold(cand.entry.kind):
                continue
            if cand.is_mixed and cand.entry.source_id != best_id:
                continue
            if det.best is not None and cand.entry.source_id == det.best.entry.source_id:
                status = {VerificationStatus.VERIFIED: MatchStatus.VERIFIED,
                          VerificationStatus.CONFLICT: MatchStatus.CONFLICT}.get(det.verification_status,
                                                                                  MatchStatus.CANDIDATE)
            else:
                status = MatchStatus.CONFLICT if det.verification_status == VerificationStatus.CONFLICT and \
                    cand.score >= self._threshold(cand.entry.kind) else MatchStatus.CANDIDATE
            rows.append(self._match_row(segment, cand, status))
        return rows

    def _match_row(self, segment: Row, cand: SourceCandidate, status: MatchStatus) -> Row:
        e = cand.entry
        return {
            "project_id": segment["project_id"], "segment_id": segment["id"], "source_id": e.source_id,
            "source_type": e.kind, "source_name": e.source_name, "title": e.title or e.reference,
            "reference_key": e.reference, "exact_quote": e.text, "translation": e.translation,
            "translation_source": e.translation_source, "hadith_grade": e.grade, "url": e.url,
            "match_type": cand.match_type, "match_score": round(cand.score, 4), "status": status.value,
        }

    def _threshold(self, kind: str) -> float:
        return self.settings.quran_match_threshold if kind == "quran" else self.settings.hadith_match_threshold

    def classify_segment(self, segment: Row) -> Row:
        det = self.detector.detect(segment["original_text"])
        self.repo.delete_where(Tables.SOURCE_MATCHES, {"segment_id": segment["id"]})
        rows = self._match_rows(segment, det)
        if rows:
            self.repo.insert_many(Tables.SOURCE_MATCHES, rows)
        return self.segments.update(segment["id"], self.detection_patch(det))

    def classify_project(self, project_id: str, progress: Any = None) -> list[Row]:
        segments = self.segments.for_project(project_id)
        out = []
        for i, seg in enumerate(segments, 1):
            out.append(self.classify_segment(seg))
            if progress:
                progress(i, len(segments))
        return out

    def reverify_project(self, project: Row) -> dict[str, int]:
        """Re-run detection for segments without a human source decision.

        Segments whose content type changes are re-translated under the new rules.
        """
        changed: list[Row] = []
        checked = 0
        all_segments = self.segments.for_project(project["id"])
        for seg in all_segments:
            if seg.get("source_review_status") in (SourceReviewStatus.APPROVED.value, SourceReviewStatus.REJECTED.value):
                continue
            if seg.get("review_status") == "approved":
                continue  # the reviewer's approval is final until it is explicitly revoked
            checked += 1
            before = (seg.get("content_type"), seg.get("source_id"))
            updated = self.classify_segment(seg)
            if (updated.get("content_type"), updated.get("source_id")) != before:
                changed.append(updated)
        if changed:
            self.translation.translate_many(project, changed, self.segments.for_project(project["id"]))
        return {"checked": checked, "changed": len(changed)}

    # ------------------------------------------------------------------ human source review
    def apply_source(self, segment: Row, entry: SourceEntry, score: float, reviewer: str) -> Row:
        """A reviewer confirmed that `segment` is `entry`: reclassify and re-translate under the source rules."""
        kind = ContentType.QURAN if entry.kind == "quran" else ContentType.HADITH
        patch = {
            "content_type": kind.value, "source_verification_status": VerificationStatus.VERIFIED.value,
            "source_review_status": SourceReviewStatus.APPROVED.value, "source_match_score": round(score, 4),
            "source_id": entry.source_id, "reference": entry.reference, "verification_source": VERIFICATION_SOURCE_LOCAL,
            "hadith_grade": entry.grade if kind == ContentType.HADITH else None, "source_text": entry.text,
            "source_url": entry.url, "text_verified": True, "recitation_verified": kind == ContentType.QURAN,
            "quran_suspected": kind == ContentType.QURAN or bool(segment.get("quran_suspected")),
            "detection_reason": f"source_confirmed_by:{reviewer}",
            # Quran protection: drop any synthesized audio immediately.
            "dubbed_audio_path": None, "audio_duration": None, "audio_review_status": None, "timing_status": None,
        }
        updated = self.segments.update(segment["id"], patch)
        project = self.repo.get(Tables.PROJECTS, segment["project_id"]) or {}
        return self.translation.translate_segment(updated, project)

    def list_matches(self, segment_id: str) -> list[Row]:
        self.segments.get(segment_id)
        rows = self.repo.list(Tables.SOURCE_MATCHES, {"segment_id": segment_id}, order_by="match_score", desc=True)
        return [match_out(r) for r in rows]

    def review_match(self, segment_id: str, match_id: str, action: str, reviewer: str) -> Row:
        segment = self.segments.get(segment_id)
        match = self.repo.get(Tables.SOURCE_MATCHES, match_id)
        if not match or match["segment_id"] != segment_id:
            raise not_found(MSG["match_not_found"])
        reviewed = {"reviewed_by": reviewer, "reviewed_at": _now()}
        if action == "approve":
            entry = self.sources.get_by_source_id(match["source_id"])
            if entry is None:
                raise conflict("المصدر غير موجود في قاعدة المصادر المحلية.")
            # Only one verified match per segment.
            for other in self.repo.list(Tables.SOURCE_MATCHES, {"segment_id": segment_id}):
                if other["id"] != match_id and other["status"] in (MatchStatus.VERIFIED.value, MatchStatus.CONFLICT.value):
                    self.repo.update(Tables.SOURCE_MATCHES, other["id"], {"status": MatchStatus.CANDIDATE.value})
            updated = self.repo.update(Tables.SOURCE_MATCHES, match_id, {"status": MatchStatus.VERIFIED.value, **reviewed})
            self.apply_source(segment, entry, float(match["match_score"]), reviewer)
            return match_out(updated)
        updated = self.repo.update(Tables.SOURCE_MATCHES, match_id, {"status": MatchStatus.REJECTED.value, **reviewed})
        if segment.get("source_id") == match["source_id"]:
            remaining = [m for m in self.repo.list(Tables.SOURCE_MATCHES, {"segment_id": segment_id})
                         if m["status"] != MatchStatus.REJECTED.value]
            patch: Row = {"source_review_status": SourceReviewStatus.REJECTED.value,
                          "source_verification_status": VerificationStatus.REJECTED.value,
                          "ready_for_dubbing": False, "text_verified": False, "recitation_verified": False,
                          "verification_source": None, "review_status": "pending", "translation_verified": False}
            if segment.get("content_type") in (ContentType.QURAN.value, ContentType.HADITH.value):
                # The religious source was rejected: the segment is no longer settled.
                patch["content_type"] = ContentType.UNCERTAIN.value
                patch["quran_suspected"] = bool(segment.get("quran_suspected")) or segment.get("content_type") == ContentType.QURAN.value
            if not remaining:
                patch["source_id"] = None
            self.segments.update(segment_id, patch)
        return match_out(updated)

    # ------------------------------------------------------------------ recovery
    def recover(self, project_id: str) -> dict[str, Any]:
        """Search the local DB again (lower threshold) for unsettled segments."""
        threshold = self.settings.recovery_threshold
        self.repo.delete_where(Tables.RECOVERED_SOURCES, {"project_id": project_id,
                                                           "status": [RecoveredStatus.CANDIDATE.value,
                                                                      RecoveredStatus.RECOVERED.value]})
        detected = 0
        for seg in self.segments.for_project(project_id):
            settled = seg.get("source_verification_status") == VerificationStatus.VERIFIED.value or \
                seg.get("source_review_status") == SourceReviewStatus.APPROVED.value
            if settled or seg.get("content_type") == ContentType.QURAN.value:
                continue
            decided = {r["source_id"] for r in self.repo.list(Tables.RECOVERED_SOURCES, {"segment_id": seg["id"]})}
            cands = self.sources.search_quran(seg["original_text"], 2) + self.sources.search_hadith(seg["original_text"], 2)
            for cand in sorted(cands, key=lambda c: c.score, reverse=True):
                if cand.score < threshold or cand.entry.source_id in decided:
                    continue
                if cand.entry.kind == "quran" and (cand.score < self.settings.quran_suspect_threshold
                                                   or cand.is_mixed and len(cand.entry.key)
                                                   < self.settings.min_embedded_quote_chars):
                    continue  # never suggest a Quran source from a weak or accidental match
                strong = cand.score >= self._threshold(cand.entry.kind) and not cand.is_mixed
                e = cand.entry
                self.repo.insert(Tables.RECOVERED_SOURCES, {
                    "project_id": project_id, "segment_id": seg["id"], "type": e.kind, "source": e.source_name,
                    "source_id": e.source_id, "reference": e.reference,
                    "section": (e.extra.get("surah_name") if e.kind == "quran" else e.title),
                    "confidence": round(cand.score, 4), "full_text": e.text, "translation": e.translation,
                    "status": (RecoveredStatus.RECOVERED if strong else RecoveredStatus.CANDIDATE).value,
                })
                detected += 1
        items = [recovered_out(r) for r in self.repo.list(Tables.RECOVERED_SOURCES, {"project_id": project_id},
                                                          order_by="confidence", desc=True)]
        return {
            "threshold": threshold,
            "recovered": [i for i in items if i["status"] in (RecoveredStatus.RECOVERED.value, RecoveredStatus.APPROVED.value)],
            "candidates": [i for i in items if i["status"] == RecoveredStatus.CANDIDATE.value],
            "detected_count": detected,
        }

    def list_recovered(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.repo.list(Tables.RECOVERED_SOURCES, {"project_id": project_id}, order_by="confidence", desc=True)
        return [recovered_out(r) for r in rows]

    def review_recovered(self, project_id: str, recovered_id: str, decision: str, reviewer: str) -> dict[str, Any]:
        row = self.repo.get(Tables.RECOVERED_SOURCES, recovered_id)
        if not row or row["project_id"] != project_id:
            raise not_found(MSG["recovered_not_found"])
        updated = self.repo.update(Tables.RECOVERED_SOURCES, recovered_id,
                                   {"status": decision, "reviewed_by": reviewer})
        if decision == RecoveredStatus.APPROVED.value and row.get("segment_id"):
            entry = self.sources.get_by_source_id(row["source_id"])
            if entry is None:
                raise conflict("المصدر غير موجود في قاعدة المصادر المحلية.")
            segment = self.segments.get(row["segment_id"])
            self.apply_source(segment, entry, float(row["confidence"]), reviewer)
            # Other open suggestions for the same segment are superseded.
            for other in self.repo.list(Tables.RECOVERED_SOURCES, {"segment_id": row["segment_id"]}):
                if other["id"] != recovered_id and other["status"] in (RecoveredStatus.CANDIDATE.value,
                                                                        RecoveredStatus.RECOVERED.value):
                    self.repo.update(Tables.RECOVERED_SOURCES, other["id"], {"status": RecoveredStatus.REJECTED.value})
        return recovered_out(updated)

    # ------------------------------------------------------------------ summaries
    def source_summary(self, project_id: str) -> dict[str, Any]:
        segments = self.segments.for_project(project_id)
        religious = [s for s in segments if s.get("content_type") in ("quran", "hadith", "uncertain")]
        count = lambda status: sum(1 for s in religious if s.get("source_verification_status") == status)  # noqa: E731
        pending_locks = self.repo.count(Tables.MEANING_LOCKS, {"project_id": project_id, "review_status": "pending"})
        blocked: dict[str, list[str]] = {}
        for s in segments:
            reasons = []
            if s.get("content_type") == ContentType.UNCERTAIN.value:
                reasons.append("uncertain_needs_review")
            if s.get("source_review_status") == SourceReviewStatus.REJECTED.value:
                reasons.append("source_rejected")
            if s.get("review_status") != "approved":
                reasons.append("not_approved")
            if not final_translation(s):
                reasons.append("translation_missing")
            if reasons:
                blocked[s["id"]] = reasons
        return {
            "project_id": project_id, "total_segments": len(segments), "religious_segments": len(religious),
            "verified": count("verified"), "candidate": count("candidate"), "not_found": count("not_found"),
            "conflict": count("conflict"), "pending": count("pending"), "pending_locks": pending_locks,
            "ready_for_dubbing": sum(1 for s in segments if s.get("ready_for_dubbing")),
            "blocked_reasons": blocked,
        }
