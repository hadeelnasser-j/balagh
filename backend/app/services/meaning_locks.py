"""Meaning locks: key Islamic terms whose translation must stay faithful.

For every glossary term found in the Arabic segment, a lock records whether the
translation contains an accepted English equivalent. Missing equivalents are
flagged so the reviewer checks them before approval.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.tables import Tables
from app.repositories.base import DataRepository, Row
from app.services.arabic import normalize_arabic


@dataclass(frozen=True)
class GlossaryTerm:
    arabic: tuple[str, ...]
    english: tuple[str, ...]
    risk: str           # risk if the equivalent is missing
    preferred: str


GLOSSARY: tuple[GlossaryTerm, ...] = (
    GlossaryTerm(("الله",), ("allah",), "high", "Allah"),
    GlossaryTerm(("رسول الله",), ("messenger of allah", "prophet"), "high", "the Messenger of Allah"),
    GlossaryTerm(("التوحيد", "توحيد"), ("tawhid", "tawheed", "monotheism", "oneness of allah"), "high", "Tawhid (monotheism)"),
    GlossaryTerm(("الشرك", "شرك"), ("shirk", "associating partners", "polytheism"), "high", "shirk (associating partners with Allah)"),
    GlossaryTerm(("البدعه", "بدعه"), ("bid'ah", "bidah", "bid‘ah", "innovation"), "high", "bid‘ah (religious innovation)"),
    GlossaryTerm(("الجهاد", "جهاد"), ("jihad", "striving"), "high", "jihad"),
    GlossaryTerm(("الصلاه", "صلاه"), ("prayer", "salah", "salat", "pray"), "medium", "prayer (salah)"),
    GlossaryTerm(("الزكاه", "زكاه"), ("zakah", "zakat", "obligatory charity"), "medium", "zakah"),
    GlossaryTerm(("الصيام", "الصوم"), ("fast", "fasting", "sawm"), "medium", "fasting"),
    GlossaryTerm(("الحج",), ("hajj", "pilgrimage"), "medium", "Hajj"),
    GlossaryTerm(("الجنه",), ("paradise", "jannah", "garden"), "medium", "Paradise"),
    GlossaryTerm(("جهنم",), ("hell", "hellfire", "jahannam", "the fire"), "medium", "Hellfire"),
    GlossaryTerm(("الايمان", "ايمان"), ("faith", "iman", "belief", "believe"), "medium", "faith (iman)"),
    GlossaryTerm(("التقوي", "تقوي"), ("taqwa", "piety", "god-consciousness", "mindfulness of allah", "fear of allah"), "medium", "taqwa"),
    GlossaryTerm(("القران",), ("quran", "qur'an", "qur’an"), "medium", "the Quran"),
)


def _contains_term(norm_text: str, term: str) -> bool:
    padded = f" {norm_text} "
    if f" {term} " in padded:
        return True
    # Attached prefixes: و ف ب ل ك (e.g. "والصلاه", "بالله", "فالله")
    return any(f" {p}{term} " in padded for p in ("و", "ف", "ب", "ل", "ك", "وب", "ول", "فب"))


def find_terms(arabic_text: str) -> list[tuple[GlossaryTerm, str]]:
    norm = normalize_arabic(arabic_text)
    found: list[tuple[GlossaryTerm, str]] = []
    for term in GLOSSARY:
        for variant in term.arabic:
            if _contains_term(norm, variant):
                found.append((term, variant))
                break
    return found


def glossary_for(arabic_text: str) -> dict[str, str]:
    return {variant: term.preferred for term, variant in find_terms(arabic_text)}


def evaluate(arabic_text: str, translation: str | None) -> list[Row]:
    lowered = (translation or "").lower()
    locks: list[Row] = []
    for term, variant in find_terms(arabic_text):
        hit = next((eq for eq in term.english if eq in lowered), None)
        if hit is None or term.risk == "high":
            locks.append({
                "original_span": variant,
                "translated_span": hit,
                "expected_terms": ", ".join(term.english),
                "lock_type": "islamic_term",
                "risk_level": term.risk if hit is None else "low",
            })
    return locks


class MeaningLockService:
    def __init__(self, repo: DataRepository) -> None:
        self.repo = repo

    def refresh(self, segment: Row, translation: str | None) -> str:
        """Recreate pending locks for a segment; returns the segment's meaning_lock_status."""
        self.repo.delete_where(Tables.MEANING_LOCKS, {"segment_id": segment["id"], "review_status": "pending"})
        rows = [{**lock, "project_id": segment["project_id"], "segment_id": segment["id"], "review_status": "pending"}
                for lock in evaluate(segment["original_text"], translation)]
        if rows:
            self.repo.insert_many(Tables.MEANING_LOCKS, rows)
        return self.status_for(segment["id"])

    def status_for(self, segment_id: str) -> str:
        locks = self.repo.list(Tables.MEANING_LOCKS, {"segment_id": segment_id})
        if not locks:
            return "none"
        if any(lock["review_status"] == "rejected" for lock in locks):
            return "rejected"
        if any(lock["review_status"] == "pending" and not lock.get("translated_span") for lock in locks):
            return "violated"
        if any(lock["review_status"] == "pending" for lock in locks):
            return "pending"
        return "approved"

    def approve_pending(self, segment_id: str) -> None:
        self.repo.update_where(Tables.MEANING_LOCKS, {"segment_id": segment_id, "review_status": "pending"},
                               {"review_status": "approved"})
