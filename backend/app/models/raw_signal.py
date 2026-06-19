from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column


class RawSignal(Base):
    __tablename__ = "raw_signals"

    id: Mapped[str] = pk_column()
    discovery_run_id: Mapped[str] = fk_column()
    source_document_id: Mapped[str | None] = fk_column()
    source_name: Mapped[str | None] = mapped_column(String)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String)
    market: Mapped[str | None] = mapped_column(String)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    product_name: Mapped[str | None] = mapped_column(String)
    product_type: Mapped[str | None] = mapped_column(String)
    brand: Mapped[str | None] = mapped_column(String)
    features: Mapped[list | None] = mapped_column(JSON, default=list)
    materials: Mapped[list | None] = mapped_column(JSON, default=list)
    target_customer: Mapped[str | None] = mapped_column(String)
    usage_occasion: Mapped[str | None] = mapped_column(String)
    price_value: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String)
    availability: Mapped[str | None] = mapped_column(String)
    is_new_arrival: Mapped[bool | None] = mapped_column(Boolean)
    category_rank: Mapped[int | None] = mapped_column(Numeric(10, 0))
    raw_title: Mapped[str | None] = mapped_column(Text)
    raw_description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String, index=True)
    independence_group: Mapped[str | None] = mapped_column(String, index=True)
    origin: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
