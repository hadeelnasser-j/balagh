"""BALAGH FastAPI application.

Run:  uvicorn app.main:app --reload --port 8000   (from the backend/ folder)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.dependencies.container import Container
from app.routers import ALL_ROUTERS
from app.services.errors import AppError
from app.startup import run_startup_tasks

logger = logging.getLogger("balagh")


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        c = container or Container(settings)
        app.state.container = c
        # Never block or crash startup on the network: stale-job recovery and the sources
        # index warm-up run in the background.
        run_startup_tasks(c)
        yield
        c.shutdown()

    app = FastAPI(title="BALAGH API", version="1.0.0", lifespan=lifespan,
                  description="Quran & Hadith-aware transcription, verification, translation and dubbing.")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "Content-Length"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "حدث خطأ داخلي في الخادم.", "code": "internal_error"})

    for router in ALL_ROUTERS:
        app.include_router(router)
    return app


app = create_app()
