"""Translation layer applying the content-type rules.

quran     -> QuranEnc translation from the local DB only. Never AI.
hadith    -> HadeethEnc published translation when the segment is the whole hadith;
             otherwise an AI draft constrained by the verified hadith (needs review).
uncertain -> no AI if Quran is suspected; else an unverified AI draft (needs review).
general   -> AI translation.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from app.config import Settings
from app.models.enums import (
    TRANSLATION_SOURCE_HADEETHENC, TRANSLATION_SOURCE_QURANENC, ContentType, TranslationStatus,
)
from app.repositories.base import Row
from app.repositories.local_sources import LocalSourcesRepository, SourceEntry, source_coverage
from app.services.arabic import contains_arabic
from app.services.errors import MSG
from app.services.meaning_locks import MeaningLockService, glossary_for
from app.services.providers.base import ProviderError, TranslationProvider, TranslationRequest
from app.services.segments import SegmentRepository

logger = logging.getLogger(__name__)

FULL_SOURCE_COVERAGE = 0.8

W_QURAN_PARTIAL = "المقطع يغطي جزءًا من الآية؛ الترجمة المعروضة هي ترجمة QuranEnc للآية كاملة."
W_QURAN_NO_TRANSLATION = "لا توجد ترجمة QuranEnc لهذه الآية في القاعدة المحلية. لا يُسمح بترجمة القرآن آليًا."
W_HADITH_DRAFT = "ترجمة آلية مقيدة بنص الحديث الموثق، وتحتاج مراجعة بشرية قبل الاعتماد."
W_UNVERIFIED = "محتوى ديني لم يُتحقق من مصدره؛ ترجمة آلية غير موثقة تحتاج مراجعة بشرية."
W_QURAN_SUSPECTED = "يُشتبه بوجود نص قرآني في هذا المقطع، لذلك لا تُستخدم الترجمة الآلية. يرجى تأكيد المصدر أو إدخال الترجمة يدويًا."
W_ARABIC_OUTPUT = "الترجمة تحتوي نصًا عربيًا وتحتاج تصحيحًا."
W_QURAN_PLACEHOLDER = "أشار نموذج الترجمة إلى احتمال وجود اقتباس قرآني؛ يرجى المراجعة."


class TranslationService:
    def __init__(self, settings: Settings, provider: TranslationProvider, sources: LocalSourcesRepository,
                 segments: SegmentRepository, locks: MeaningLockService) -> None:
        self.settings = settings
        self.provider = provider
        self.sources = sources
        self.segments = segments
        self.locks = locks

    # ------------------------------------------------------------------ labels
    def _ai_source(self) -> str:
        return {"openai": "OpenAI", "gemini": "Gemini"}.get(self.provider.name, self.provider.name)

    def _ai_origin(self, kind: str) -> str:
        prefix = self.provider.name if self.provider.name in ("openai", "gemini") else "ai"
        return f"{prefix}_{kind}"

    # ------------------------------------------------------------------ core
    def build_patch(self, segment: Row, project: Row, prev_text: str | None = None,
                    next_text: str | None = None) -> Row:
        """Compute translation fields for one segment. Never raises for provider errors."""
        content = (segment.get("content_type") or ContentType.GENERAL.value).lower()
        reset: Row = {"edited_translation": None, "final_translation": None, "translation_error": None,
                      "translation_warning": None, "review_status": "pending", "translation_verified": False,
                      "ready_for_dubbing": False, "needs_human_review": True,
                      "dubbed_audio_path": None, "audio_duration": None, "timing_status": None,
                      "audio_review_status": None, "tempo_factor": None}
        entry = self.sources.get_by_source_id(segment["source_id"]) if segment.get("source_id") else None

        if content == ContentType.QURAN.value:
            return {**reset, **self._quran_patch(segment, entry)}

        if content == ContentType.HADITH.value and entry is not None:
            if entry.translation and source_coverage(self.sources, segment["original_text"], entry) >= FULL_SOURCE_COVERAGE:
                return {**reset, "translated_text": entry.translation.strip(),
                        "translation_status": TranslationStatus.TRANSLATED.value,
                        "translation_source": TRANSLATION_SOURCE_HADEETHENC,
                        "translation_origin": "hadeethenc_official"}
            return {**reset, **self._ai_patch(segment, project, "constrained", prev_text, next_text, entry)}

        if content == ContentType.UNCERTAIN.value:
            if segment.get("quran_suspected"):
                return {**reset, "translated_text": None, "translation_status": TranslationStatus.FAILED.value,
                        "translation_error": MSG["translation_not_allowed"],
                        "translation_warning": W_QURAN_SUSPECTED, "translation_source": None,
                        "translation_origin": None}
            hadith_ref = entry if entry and entry.kind == "hadith" else None
            return {**reset, **self._ai_patch(segment, project, "unverified", prev_text, next_text, hadith_ref)}

        return {**reset, **self._ai_patch(segment, project, "general", prev_text, next_text, None)}

    def _quran_patch(self, segment: Row, entry: SourceEntry | None) -> Row:
        if entry is None or not entry.translation:
            return {"translated_text": None, "translation_status": TranslationStatus.FAILED.value,
                    "translation_error": W_QURAN_NO_TRANSLATION, "translation_warning": W_QURAN_NO_TRANSLATION,
                    "translation_source": TRANSLATION_SOURCE_QURANENC, "translation_origin": "quranenc_local_official"}
        warning = W_QURAN_PARTIAL if source_coverage(self.sources, segment["original_text"], entry) < FULL_SOURCE_COVERAGE else None
        return {"translated_text": entry.translation.strip(), "translation_status": TranslationStatus.TRANSLATED.value,
                "translation_warning": warning, "translation_source": TRANSLATION_SOURCE_QURANENC,
                "translation_origin": "quranenc_local_official"}

    def _ai_patch(self, segment: Row, project: Row, mode: str, prev_text: str | None, next_text: str | None,
                  reference: SourceEntry | None) -> Row:
        # Defense in depth: never let AI translate anything classified or suspected as Quran.
        if segment.get("content_type") == ContentType.QURAN.value or segment.get("quran_suspected") and mode != "constrained":
            raise RuntimeError("Quran protection: AI translation requested for Quran content")
        request = TranslationRequest(
            text=segment["original_text"],
            source_language=segment.get("source_language") or project.get("source_language") or "ar",
            target_language=segment.get("target_language") or project.get("target_language") or "en",
            mode=mode, dubbing_mode=project.get("dubbing_mode") or "timed",
            duration_seconds=float(segment["end_time"]) - float(segment["start_time"]),
            context_before=prev_text, context_after=next_text,
            reference_text=reference.text if reference else None,
            reference_translation=reference.translation if reference else None,
            glossary=glossary_for(segment["original_text"]),
        )
        origin_kind = {"general": "general", "constrained": "constrained_draft", "unverified": "unverified_draft"}[mode]
        try:
            result = self.provider.translate(request)
        except ProviderError as exc:
            return {"translated_text": None, "translation_status": TranslationStatus.FAILED.value,
                    "translation_error": str(exc), "translation_source": self._ai_source(),
                    "translation_origin": self._ai_origin(origin_kind)}
        warnings = []
        if mode == "constrained":
            warnings.append(W_HADITH_DRAFT)
        elif mode == "unverified":
            warnings.append(W_UNVERIFIED)
        if contains_arabic(result.text):
            warnings.append(W_ARABIC_OUTPUT)
        if "[QURAN]" in result.text.upper():
            warnings.append(W_QURAN_PLACEHOLDER)
        return {"translated_text": result.text, "translation_status": TranslationStatus.TRANSLATED.value,
                "translation_warning": " ".join(warnings) or None, "translation_source": self._ai_source(),
                "translation_origin": self._ai_origin(origin_kind)}

    # ------------------------------------------------------------------ batch
    def translate_segment(self, segment: Row, project: Row, neighbors: tuple[str | None, str | None] = (None, None)) -> Row:
        self.segments.update(segment["id"], {"translation_status": TranslationStatus.TRANSLATING.value})
        patch = self.build_patch(segment, project, *neighbors)
        updated = self.segments.update(segment["id"], patch)
        status = self.locks.refresh(updated, updated.get("translated_text"))
        return self.segments.update(segment["id"], {"meaning_lock_status": status})

    def translate_many(self, project: Row, segments: list[Row], all_segments: list[Row],
                       progress: Callable[[int, int], None] | None = None) -> None:
        by_index = {s["segment_index"]: s for s in all_segments}

        def run(seg: Row) -> Any:
            prev_seg = by_index.get(seg["segment_index"] - 1)
            next_seg = by_index.get(seg["segment_index"] + 1)
            return self.translate_segment(seg, project, (prev_seg and prev_seg["original_text"],
                                                         next_seg and next_seg["original_text"]))

        done = 0
        workers = max(1, self.settings.max_translation_concurrency)
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="balagh-translate") as pool:
            for _ in pool.map(run, segments):
                done += 1
                if progress:
                    progress(done, len(segments))
