from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column


class RetailerScan(Base):
    __tablename__ = "retailer_scans"

    id: Mapped[str] = pk_column()
    opportunity_id: Mapped[str] = fk_column()
    retailer_id: Mapped[str | None] = fk_column()
    source_url: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot_uri: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String)
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
