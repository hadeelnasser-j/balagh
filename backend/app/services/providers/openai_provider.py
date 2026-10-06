"""OpenAI providers: transcription, translation and TTS."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.ffmpeg import FFmpegService
from app.services.providers.base import (
    ProviderError, TranscriptSegment, TranslationRequest, TranslationResult,
)
from app.services.providers.prompts import SYSTEM_PROMPT, build_user_prompt, parse_translation_json

logger = logging.getLogger(__name__)

_TRANSCRIBE_PROMPT = ("نص عربي فصيح من درس ديني، قد يتضمن آيات قرآنية وأحاديث نبوية. "
                      "اكتب الكلام كما نُطق بدقة دون تلخيص.")


def _client(settings: Settings) -> Any:
    if not settings.openai_configured:
        raise ProviderError("مفتاح OpenAI غير مضبوط على الخادم.")
    from openai import OpenAI  # imported lazily

    kwargs: dict[str, Any] = {"api_key": settings.openai_api_key, "timeout": settings.provider_timeout_seconds,
                              "max_retries": 2}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def _get(obj: Any, key: str) -> Any:
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)


class OpenAITranscriptionProvider:
    name = "openai"

    def __init__(self, settings: Settings, ffmpeg: FFmpegService) -> None:
        self.settings = settings
        self.ffmpeg = ffmpeg

    def transcribe(self, audio_path: Path, language: str | None) -> list[TranscriptSegment]:
        client = _client(self.settings)
        lang = language or self.settings.transcription_language_hint or None
        try:
            with open(audio_path, "rb") as fh:
                result = client.audio.transcriptions.create(
                    model=self.settings.openai_timestamp_model, file=fh, response_format="verbose_json",
                    timestamp_granularities=["segment"], language=lang, prompt=_TRANSCRIBE_PROMPT,
                )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"فشل التفريغ الصوتي عبر OpenAI: {exc}") from exc
        segments = [
            TranscriptSegment(float(_get(s, "start")), float(_get(s, "end")), str(_get(s, "text") or "").strip())
            for s in (_get(result, "segments") or [])
        ]
        segments = [s for s in segments if s.text and s.end > s.start]
        if not segments:
            text = str(_get(result, "text") or "").strip()
            if text:
                duration = float(_get(result, "duration") or self.ffmpeg.probe_duration(audio_path) or 0)
                segments = [TranscriptSegment(0.0, duration, text)]
        model = self.settings.openai_transcription_model
        if self.settings.openai_refine_segments and model and model != self.settings.openai_timestamp_model:
            segments = self._refine(client, audio_path, segments, lang)
        return segments

    def _refine(self, client: Any, audio_path: Path, segments: list[TranscriptSegment],
                lang: str | None) -> list[TranscriptSegment]:
        """Re-transcribe each timed segment with the higher-accuracy model."""
        refined: list[TranscriptSegment] = []
        with tempfile.TemporaryDirectory(prefix="balagh_refine_") as tmp:
            for i, seg in enumerate(segments):
                clip = Path(tmp) / f"seg_{i:04d}.mp3"
                try:
                    self.ffmpeg.cut_audio(audio_path, clip, seg.start, seg.end)
                    with open(clip, "rb") as fh:
                        result = client.audio.transcriptions.create(
                            model=self.settings.openai_transcription_model, file=fh, response_format="json",
                            language=lang, prompt=_TRANSCRIBE_PROMPT,
                        )
                    text = str(_get(result, "text") or "").strip()
                    refined.append(TranscriptSegment(seg.start, seg.end, text or seg.text))
                except Exception as exc:  # noqa: BLE001 - keep the timestamp-model text on failure
                    logger.warning("Refinement failed for segment %d: %s", i, exc)
                    refined.append(seg)
        return refined


class OpenAITranslationProvider:
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.openai_translation_model

    def translate(self, request: TranslationRequest) -> TranslationResult:
        client = _client(self.settings)
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": build_user_prompt(request)}],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"فشلت الترجمة عبر OpenAI: {exc}") from exc
        text, notes = parse_translation_json(raw)
        if not text:
            raise ProviderError("أعاد نموذج الترجمة نتيجة فارغة.")
        return TranslationResult(text=text, notes=notes, provider=self.name, model=self.model)


class OpenAITTSProvider:
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def synthesize(self, text: str, out_path: Path, *, language: str = "en") -> Path:
        client = _client(self.settings)
        kwargs: dict[str, Any] = {"model": self.settings.openai_tts_model, "voice": self.settings.openai_tts_voice,
                                  "input": text, "response_format": "mp3"}
        if self.settings.openai_tts_model.startswith("gpt-4o"):
            kwargs["instructions"] = "Calm, clear, respectful narration for an educational Islamic video."
        try:
            response = client.audio.speech.create(**kwargs)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(response.content)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"فشل توليد الصوت عبر OpenAI: {exc}") from exc
        return out_path
