"""Provider factory: picks OpenAI / Gemini / Fake implementations from settings."""
from __future__ import annotations

from app.config import Settings
from app.services.ffmpeg import FFmpegService
from app.services.providers.base import (  # noqa: F401
    ProviderError, TranscriptionProvider, TranscriptSegment, TranslationProvider, TranslationRequest,
    TranslationResult, TTSProvider,
)


def build_transcription_provider(settings: Settings, ffmpeg: FFmpegService) -> TranscriptionProvider:
    name = settings.transcription_provider.lower()
    if name == "openai":
        from app.services.providers.openai_provider import OpenAITranscriptionProvider
        return OpenAITranscriptionProvider(settings, ffmpeg)
    if name == "gemini":
        from app.services.providers.gemini_provider import GeminiTranscriptionProvider
        return GeminiTranscriptionProvider(settings)
    if name == "fake":
        from app.services.providers.fake_provider import FakeTranscriptionProvider
        return FakeTranscriptionProvider()
    raise ValueError(f"Unknown TRANSCRIPTION_PROVIDER: {settings.transcription_provider}")


def build_translation_provider(settings: Settings) -> TranslationProvider:
    name = settings.translation_provider.lower()
    if name == "openai":
        from app.services.providers.openai_provider import OpenAITranslationProvider
        return OpenAITranslationProvider(settings)
    if name == "gemini":
        from app.services.providers.gemini_provider import GeminiTranslationProvider
        return GeminiTranslationProvider(settings)
    if name == "fake":
        from app.services.providers.fake_provider import FakeTranslationProvider
        return FakeTranslationProvider()
    raise ValueError(f"Unknown TRANSLATION_PROVIDER: {settings.translation_provider}")


def build_tts_provider(settings: Settings, ffmpeg: FFmpegService) -> TTSProvider:
    name = settings.tts_provider.lower()
    if name == "openai":
        from app.services.providers.openai_provider import OpenAITTSProvider
        return OpenAITTSProvider(settings)
    if name == "gemini":
        from app.services.providers.gemini_provider import GeminiTTSProvider
        return GeminiTTSProvider(settings)
    if name == "fake":
        from app.services.providers.fake_provider import FakeTTSProvider
        return FakeTTSProvider(ffmpeg)
    raise ValueError(f"Unknown TTS_PROVIDER: {settings.tts_provider}")
