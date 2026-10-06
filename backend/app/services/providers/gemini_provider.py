"""Google Gemini providers (REST API via httpx): transcription, translation and TTS."""
from __future__ import annotations

import base64
import json
import wave
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.providers.base import (
    ProviderError, TranscriptSegment, TranslationRequest, TranslationResult,
)
from app.services.providers.prompts import SYSTEM_PROMPT, build_user_prompt, parse_translation_json

_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_TRANSCRIBE_INSTRUCTIONS = (
    "Transcribe this Arabic audio verbatim (it may contain Quran recitation and hadith). "
    "Split it into natural sentence-level segments of at most ~12 seconds. Return JSON: "
    '{"segments": [{"start": seconds, "end": seconds, "text": "..."}]}. '
    "Do not translate, summarise or correct the speaker."
)


def _post(settings: Settings, model: str, body: dict[str, Any]) -> dict[str, Any]:
    if not settings.gemini_configured:
        raise ProviderError("مفتاح Gemini غير مضبوط على الخادم.")
    import httpx  # imported lazily

    try:
        response = httpx.post(_API.format(model=model), json=body, timeout=settings.provider_timeout_seconds,
                              headers={"x-goog-api-key": settings.gemini_api_key})
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"فشل الاتصال بـ Gemini: {exc}") from exc


def _first_part(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return payload["candidates"][0]["content"]["parts"][0]
    except (KeyError, IndexError) as exc:
        raise ProviderError("استجابة Gemini غير متوقعة.") from exc


class GeminiTranscriptionProvider:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def transcribe(self, audio_path: Path, language: str | None) -> list[TranscriptSegment]:
        audio = base64.b64encode(audio_path.read_bytes()).decode()
        mime = "audio/mpeg" if audio_path.suffix == ".mp3" else "audio/wav"
        body = {
            "contents": [{"parts": [{"text": _TRANSCRIBE_INSTRUCTIONS},
                                    {"inline_data": {"mime_type": mime, "data": audio}}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        part = _first_part(_post(self.settings, self.settings.gemini_transcription_model, body))
        try:
            data = json.loads(part.get("text", "{}"))
            rows = data.get("segments", data) if isinstance(data, dict) else data
            segments = [TranscriptSegment(float(r["start"]), float(r["end"]), str(r["text"]).strip()) for r in rows]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError("تعذر قراءة نتيجة التفريغ من Gemini.") from exc
        return [s for s in segments if s.text and s.end > s.start]


class GeminiTranslationProvider:
    name = "gemini"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.gemini_translation_model

    def translate(self, request: TranslationRequest) -> TranslationResult:
        body = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": build_user_prompt(request)}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        part = _first_part(_post(self.settings, self.model, body))
        text, notes = parse_translation_json(part.get("text", ""))
        if not text:
            raise ProviderError("أعاد نموذج الترجمة نتيجة فارغة.")
        return TranslationResult(text=text, notes=notes, provider=self.name, model=self.model)


class GeminiTTSProvider:
    name = "gemini"
    SAMPLE_RATE = 24000

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def synthesize(self, text: str, out_path: Path, *, language: str = "en") -> Path:
        body = {
            "contents": [{"parts": [{"text": f"Say calmly and clearly: {text}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.settings.gemini_tts_voice}}},
            },
        }
        part = _first_part(_post(self.settings, self.settings.gemini_tts_model, body))
        inline = part.get("inlineData") or part.get("inline_data") or {}
        if not inline.get("data"):
            raise ProviderError("لم يُرجع Gemini أي صوت.")
        pcm = base64.b64decode(inline["data"])
        out_path = out_path.with_suffix(".wav")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.SAMPLE_RATE)
            wav.writeframes(pcm)
        return out_path
