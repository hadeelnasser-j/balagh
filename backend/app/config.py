"""Application settings, loaded from environment variables and backend/.env.

Only the standard library and pydantic are used so the settings load in any
environment (no pydantic-settings dependency).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        values[key.strip()] = value
    return values


class Settings(BaseModel):
    # General
    app_name: str = "BALAGH Backend"
    environment: str = "development"
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ])

    # Data backend: "supabase" (production) or "memory" (tests / offline dev)
    data_backend: str = "supabase"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_timeout_seconds: float = 10.0
    supabase_storage_enabled: bool = False
    bucket_videos: str = "videos"
    bucket_audio: str = "audio"
    bucket_subtitles: str = "subtitles"
    bucket_outputs: str = "dubbed-outputs"

    # Local storage for media working files
    storage_dir: Path = BACKEND_DIR / "storage"

    # Local sources database
    sources_db_path: Path = BACKEND_DIR / "data" / "balagh_sources.sqlite3"
    quran_match_threshold: float = 0.92
    hadith_match_threshold: float = 0.85
    # Below the Quran threshold but at/above this, a non-mixed match makes the segment "uncertain"
    # (Quran-protected, no AI translation) WITHOUT attaching any Quran reference.
    quran_suspect_threshold: float = 0.85
    # A Quran/Hadith match embedded in longer speech only counts if the quoted source is at least this
    # long (normalized chars). Shorter ayahs (e.g. "ملك الناس") coincide with ordinary speech.
    min_embedded_quote_chars: int = 25
    candidate_threshold: float = 0.70
    recovery_threshold: float = 0.70
    min_match_chars: int = 12
    mixed_coverage_threshold: float = 0.85

    # FFmpeg
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    audio_sample_rate: int = 16000
    max_upload_mb: int = 500
    max_video_duration_seconds: int = 900
    allowed_video_extensions: list[str] = Field(default_factory=lambda: [".mp4", ".mov", ".webm", ".mkv", ".m4v", ".avi"])

    # Providers
    transcription_provider: str = "openai"
    translation_provider: str = "openai"
    tts_provider: str = "openai"

    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_transcription_model: str = "gpt-4o-transcribe"
    openai_timestamp_model: str = "whisper-1"
    openai_refine_segments: bool = True
    openai_translation_model: str = "gpt-5-mini"
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "alloy"

    gemini_api_key: str = ""
    gemini_transcription_model: str = "gemini-2.5-flash"
    gemini_translation_model: str = "gemini-2.5-flash"
    gemini_tts_model: str = "gemini-2.5-flash-preview-tts"
    gemini_tts_voice: str = "Kore"

    transcription_language_hint: str = "ar"
    provider_timeout_seconds: float = 120.0

    # Concurrency
    worker_threads: int = 4
    max_translation_concurrency: int = 3
    max_tts_concurrency: int = 2

    # Dubbing / audio
    dubbing_max_tempo: float = 1.35
    # Approved audio that is longer than its slot is sped up at render time up to this factor
    # (never blocked; any remaining overflow is reported as a warning).
    approved_overflow_max_tempo: float = 1.6
    original_audio_duck_volume: float = 0.0
    dubbed_audio_bitrate: str = "192k"
    srt_include_attribution: bool = True

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())


def _coerce(field_type: object, raw: str) -> object:
    text = raw.strip()
    if field_type is bool:
        return text.lower() in {"1", "true", "yes", "on"}
    if field_type is list or str(field_type).startswith("list"):
        return [item.strip() for item in text.split(",") if item.strip()]
    return text


def load_settings(env_file: Path | None = None, overrides: dict[str, object] | None = None) -> Settings:
    file_values = _load_dotenv(env_file or BACKEND_DIR / ".env")
    data: dict[str, object] = {}
    for name, field in Settings.model_fields.items():
        env_key = name.upper()
        raw = os.environ.get(env_key, file_values.get(env_key))
        if raw is None or raw == "":
            continue
        data[name] = _coerce(field.annotation, raw)
    if overrides:
        data.update(overrides)
    settings = Settings(**data)
    # Accept common copy/paste variants of the project URL.
    url = settings.supabase_url.strip().rstrip("/")
    for suffix in ("/rest/v1", "/auth/v1", "/storage/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    settings.supabase_url = url
    # Relative paths in .env are relative to the backend/ folder, not the current directory.
    for name in ("storage_dir", "sources_db_path"):
        value = getattr(settings, name)
        if not value.is_absolute():
            setattr(settings, name, (BACKEND_DIR / value).resolve())
    return settings


@lru_cache
def get_settings() -> Settings:
    return load_settings()
