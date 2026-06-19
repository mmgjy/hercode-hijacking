"""Database engine, session factory and declarative base.

Works with both SQLite (zero-config demo/tests) and PostgreSQL/Supabase. We use
SQLAlchemy's generic ``JSON`` type and timezone-aware ``DateTime`` so models are
portable across both backends.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, future=True)


settings = get_settings()
engine = _make_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Create tables directly (used for SQLite demo/tests; production uses Alembic)."""
    import app.models  # noqa: F401  ensure models are registered

    Base.metadata.create_all(bind=engine)
