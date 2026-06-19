from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column


class NormalizedSignal(Base):
    __tablename__ = "normalized_signals"

    id: Mapped[str] = pk_column()
    raw_signal_id: Mapped[str] = fk_column()
    discovery_run_id: Mapped[str | None] = fk_column()  # denormalized for queries
    normalized_product_type: Mapped[str | None] = mapped_column(String)
    normalized_features: Mapped[list | None] = mapped_column(JSON, default=list)
    normalized_materials: Mapped[list | None] = mapped_column(JSON, default=list)
    normalized_customer_segment: Mapped[str | None] = mapped_column(String)
    normalized_usage_occasion: Mapped[str | None] = mapped_column(String)
    normalized_brand: Mapped[str | None] = mapped_column(String)
    normalization_terms: Mapped[dict | None] = mapped_column(JSON, default=dict)
    normalization_version: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
