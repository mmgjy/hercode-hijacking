from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column, utcnow


class ScanItem(Base):
    __tablename__ = "scan_items"

    id: Mapped[str] = pk_column()
    retailer_scan_id: Mapped[str] = fk_column()
    opportunity_id: Mapped[str | None] = fk_column()  # denormalized for queries
    retailer_id: Mapped[str | None] = fk_column()
    title: Mapped[str | None] = mapped_column(String)
    brand: Mapped[str | None] = mapped_column(String)
    price_value: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String)
    availability: Mapped[str | None] = mapped_column(String)
    features: Mapped[list | None] = mapped_column(JSON, default=list)
    product_url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    match_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    matched_terms: Mapped[list | None] = mapped_column(JSON, default=list)
    missing_terms: Mapped[list | None] = mapped_column(JSON, default=list)
    match_explanation: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str | None] = mapped_column(String, default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
