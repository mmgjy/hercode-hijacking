from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column


class CoverageSnapshot(Base):
    __tablename__ = "coverage_snapshots"

    id: Mapped[str] = pk_column()
    opportunity_id: Mapped[str] = fk_column()
    configured_retailer_count: Mapped[int | None] = mapped_column(Integer)
    retailers_with_matches: Mapped[int | None] = mapped_column(Integer)
    approved_product_count: Mapped[int | None] = mapped_column(Integer)
    unique_brand_count: Mapped[int | None] = mapped_column(Integer)
    retailer_presence_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    product_depth_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    brand_diversity_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    price_band_coverage_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    feature_coverage_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    availability_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    coverage_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    gap_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    calculation_version: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
