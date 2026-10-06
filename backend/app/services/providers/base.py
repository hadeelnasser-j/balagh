"""Provider interfaces. Concrete providers: OpenAI, Gemini (and Fake for tests)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class ProviderError(RuntimeError):
    """Raised when an AI provider call fails or is misconfigured."""


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranslationRequest:
    text: str
    source_language: str
    target_language: str
    mode: str                                   # "general" | "constrained" | "unverified"
    dubbing_mode: str = "timed"
    duration_seconds: float | None = None
    context_before: str | None = None
    context_after: str | None = None
    reference_text: str | None = None           # Arabic source text (e.g. the matched hadith)
    reference_translation: str | None = None    # published translation of the reference
    glossary: dict[str, str] = field(default_factory=dict)


@dataclass
class TranslationResult:
    text: str
    notes: str | None = None
    provider: str = ""
    model: str = ""


class TranscriptionProvider(Protocol):
    name: str

    def transcribe(self, audio_path: Path, language: str | None) -> list[TranscriptSegment]: ...


class TranslationProvider(Protocol):
    name: str
    model: str

    def translate(self, request: TranslationRequest) -> TranslationResult: ...


class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str, out_path: Path, *, language: str = "en") -> Path: ...
