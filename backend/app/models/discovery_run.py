from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column, uuid_str


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id: Mapped[str] = pk_column()
    category: Mapped[str] = mapped_column(String, nullable=False)
    target_market: Mapped[str] = mapped_column(String, nullable=False)
    source_set: Mapped[str] = mapped_column(String, nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False)
    maximum_opportunities: Mapped[int] = mapped_column(Integer, nullable=False)
    focus_keywords: Mapped[list | None] = mapped_column(JSON, default=list)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    current_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    normalized_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    opportunity_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[list | None] = mapped_column(JSON, default=list)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at_column()


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = pk_column()
    discovery_run_id: Mapped[str] = fk_column()
    source_key: Mapped[str | None] = mapped_column(String)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String)
    market: Mapped[str | None] = mapped_column(String)
    http_status: Mapped[int | None] = mapped_column(Integer)
    collection_status: Mapped[str | None] = mapped_column(String)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot_uri: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String)
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str | None] = mapped_column(String)
