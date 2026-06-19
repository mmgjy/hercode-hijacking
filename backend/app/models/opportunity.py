from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = pk_column()
    discovery_run_id: Mapped[str] = fk_column()
    name: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    strongest_observed_market: Mapped[str | None] = mapped_column(String)
    earliest_observed_market: Mapped[str | None] = mapped_column(String)
    earliest_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dominant_product_type: Mapped[str | None] = mapped_column(String)
    dominant_features: Mapped[list | None] = mapped_column(JSON, default=list)
    dominant_materials: Mapped[list | None] = mapped_column(JSON, default=list)
    customer_segment: Mapped[str | None] = mapped_column(String)
    usage_occasion: Mapped[str | None] = mapped_column(String)
    search_terms: Mapped[list | None] = mapped_column(JSON, default=list)
    signal_count: Mapped[int] = mapped_column(Integer, default=0)
    independent_source_count: Mapped[int] = mapped_column(Integer, default=0)
    brand_count: Mapped[int] = mapped_column(Integer, default=0)
    market_count: Mapped[int] = mapped_column(Integer, default=0)
    naming_terms: Mapped[list | None] = mapped_column(JSON, default=list)
    naming_method: Mapped[str | None] = mapped_column(String)
    naming_version: Mapped[str | None] = mapped_column(String)
    origin: Mapped[str] = mapped_column(String, default="AUTO_DISCOVERED")
    created_at: Mapped[datetime] = created_at_column()


class OpportunitySignal(Base):
    __tablename__ = "opportunity_signals"

    opportunity_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    normalized_signal_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    cluster_similarity: Mapped[float | None] = mapped_column(Numeric(6, 4))
    cluster_terms: Mapped[list | None] = mapped_column(JSON, default=list)
