from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column


class TransferabilityAssessment(Base):
    __tablename__ = "transferability_assessments"

    id: Mapped[str] = pk_column()
    opportunity_id: Mapped[str] = fk_column()
    climate_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    geography_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    customer_fit_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    regulatory_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    price_fit_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    seasonality_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    overall_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    factor_details: Mapped[dict | None] = mapped_column(JSON, default=dict)
    market_profile_version: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
