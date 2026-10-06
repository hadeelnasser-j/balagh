"""Service-level errors carrying an HTTP status and an Arabic message for the UI."""
from __future__ import annotations


class AppError(Exception):
    def __init__(self, status_code: int, detail: str, code: str | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code


def not_found(detail: str = "العنصر المطلوب غير موجود.") -> AppError:
    return AppError(404, detail, "not_found")


def conflict(detail: str, code: str | None = None) -> AppError:
    return AppError(409, detail, code or "conflict")


def bad_request(detail: str, code: str | None = None) -> AppError:
    return AppError(400, detail, code or "bad_request")


MSG = {
    "project_not_found": "المشروع غير موجود.",
    "segment_not_found": "المقطع غير موجود.",
    "job_not_found": "مهمة المعالجة غير موجودة.",
    "match_not_found": "المطابقة المرجعية غير موجودة.",
    "lock_not_found": "قفل المعنى غير موجود.",
    "recovered_not_found": "المصدر المسترجع غير موجود.",
    "video_missing": "لم يُرفع فيديو لهذا المشروع بعد.",
    "audio_missing": "لم يُستخرج الصوت من الفيديو بعد.",
    "no_segments": "لا توجد مقاطع في المشروع. يرجى تشغيل التفريغ أولًا.",
    "job_running": "توجد مهمة معالجة أخرى جارية لهذا المشروع. يرجى الانتظار حتى تكتمل.",
    "quran_edit_forbidden": "لا يمكن تعديل ترجمة الآيات القرآنية؛ تُستخدم ترجمة QuranEnc المعتمدة فقط.",
    "quran_tts_forbidden": "لا يمكن توليد صوت لمقطع قرآني؛ يُحفظ الصوت الأصلي للتلاوة.",
    "uncertain_tts_forbidden": "المقطع غير محسوم ويحتاج مراجعة بشرية قبل الدبلجة.",
    "empty_translation": "لا يمكن اعتماد مقطع بلا ترجمة نهائية.",
    "arabic_in_translation": "الترجمة تحتوي نصًا عربيًا؛ يرجى تصحيحها قبل الاعتماد.",
    "srt_missing": "لم يُنشأ ملف الترجمة بعد.",
    "srt_final_blocked": "لا يمكن إنشاء SRT نهائي قبل اعتماد جميع المقاطع.",
    "dubbing_blocked": "المشروع غير جاهز لتوليد الدبلجة.",
    "render_blocked": "المشروع غير جاهز لإنشاء الفيديو المدبلج.",
    "dubbed_missing": "لم يُنشأ الفيديو المدبلج بعد.",
    "segment_audio_missing": "لم يُولَّد صوت لهذا المقطع بعد.",
    "audio_file_missing": "ملف الصوت المعتمد للمقطع {n} غير موجود على الخادم. يرجى إعادة توليده.",
    "audio_corrupted": "ملف الصوت المعتمد للمقطع {n} تالف أو غير قابل للقراءة. يرجى إعادة توليده.",
    "invalid_format": "صيغة الملف غير مدعومة. الصيغ المسموحة: {formats}.",
    "file_too_large": "حجم الملف يتجاوز الحد المسموح ({mb} ميغابايت).",
    "duration_exceeded": "مدة الفيديو تتجاوز الحد المسموح ({seconds} ثانية).",
    "empty_file": "الملف المرفوع فارغ.",
    "translation_not_allowed": "ترجمة هذا المقطع آليًا غير مسموحة لأنه قد يحتوي نصًا قرآنيًا.",
}
