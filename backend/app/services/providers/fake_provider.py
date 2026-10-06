"""Deterministic offline providers used by the test-suite (PROVIDER=fake).

Never use in production: the health endpoint reports them as "fake".
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.ffmpeg import FFmpegService
from app.services.providers.base import TranscriptSegment, TranslationRequest, TranslationResult


class FakeTranscriptionProvider:
    """Reads segments from `<audio>.transcript.json` or FAKE_TRANSCRIPT set on the instance."""

    name = "fake"

    def __init__(self, segments: list[TranscriptSegment] | None = None) -> None:
        self.segments = segments

    def transcribe(self, audio_path: Path, language: str | None) -> list[TranscriptSegment]:
        if self.segments is not None:
            return list(self.segments)
        sidecar = audio_path.with_suffix(".transcript.json")
        if sidecar.is_file():
            rows = json.loads(sidecar.read_text(encoding="utf-8"))
            return [TranscriptSegment(r["start"], r["end"], r["text"]) for r in rows]
        return [TranscriptSegment(0.0, 2.0, "هذا مثال للتجربة")]


class FakeTranslationProvider:
    name = "fake"
    model = "fake-translator"

    def __init__(self) -> None:
        self.calls: list[TranslationRequest] = []

    def translate(self, request: TranslationRequest) -> TranslationResult:
        self.calls.append(request)
        words = max(1, len(request.text.split()))
        return TranslationResult(text=" ".join(["word"] * words) + ".", notes=None, provider=self.name,
                                 model=self.model)


class FakeTTSProvider:
    name = "fake"

    def __init__(self, ffmpeg: FFmpegService, seconds_per_word: float = 0.3) -> None:
        self.ffmpeg = ffmpeg
        self.seconds_per_word = seconds_per_word
        self.calls: list[str] = []

    def synthesize(self, text: str, out_path: Path, *, language: str = "en") -> Path:
        self.calls.append(text)
        duration = max(0.4, self.seconds_per_word * len(text.split()))
        out_path = out_path.with_suffix(".wav")
        self.ffmpeg.generate_tone(out_path, duration)
        return out_path
