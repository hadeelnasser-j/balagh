"""FastAPI dependencies."""
from __future__ import annotations

from starlette.requests import Request

from app.dependencies.container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container
