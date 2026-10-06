from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import get_container
from app.dependencies.container import Container
from app.schemas import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict:
    return {"name": "BALAGH Backend", "status": "ok", "docs": "/docs", "health": "/api/health"}


@router.get("/api/health", response_model=HealthStatus)
def health(c: Container = Depends(get_container)) -> dict:
    s = c.settings
    supabase_ok = c.repo.ping()
    ffmpeg_ok = c.ffmpeg.ffmpeg_available()
    ffprobe_ok = c.ffmpeg.ffprobe_available()
    sources = c.sources.stats()
    ok = supabase_ok and ffmpeg_ok and ffprobe_ok
    return {
        "status": "healthy" if ok else "degraded",
        "supabase": "available" if supabase_ok else "unavailable",
        "ffmpeg": "available" if ffmpeg_ok else "unavailable",
        "ffprobe": "available" if ffprobe_ok else "unavailable",
        "transcription_provider": s.transcription_provider,
        "translation_provider": s.translation_provider,
        "tts_provider": s.tts_provider,
        "openai_configured": s.openai_configured,
        "gemini_configured": s.gemini_configured,
        "sources_database": "available" if sources["available"] else "unavailable",
        "data_backend": s.data_backend,
    }
