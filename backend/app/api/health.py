from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "app_env": settings.APP_ENV,
        "playwright_enabled": settings.PLAYWRIGHT_ENABLED,
    }
