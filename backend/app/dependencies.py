"""Shared FastAPI dependencies: DB session and optional API-key auth."""
from __future__ import annotations

from fastapi import Header

from app.config import get_settings
from app.database import get_db  # re-exported for routers
from app.errors import AppError, ErrorCode

__all__ = ["get_db", "require_api_key"]


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Enforce X-API-Key on mutating endpoints when API_KEY is configured.

    If API_KEY is unset (default for local/demo), auth is disabled.
    """
    settings = get_settings()
    if not settings.API_KEY:
        return
    if x_api_key != settings.API_KEY:
        raise AppError(
            ErrorCode.UNAUTHORIZED, "Missing or invalid API key.", status_code=401
        )
