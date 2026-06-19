"""Shared column helpers for models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid_str() -> str:
    return str(uuid.uuid4())


def pk_column():
    # UUID stored as a string for cross-database portability (SQLite + Postgres).
    return mapped_column(String(36), primary_key=True, default=uuid_str)


def fk_column(nullable: bool = True):
    return mapped_column(String(36), nullable=nullable, index=True)


def created_at_column():
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
