from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._common import created_at_column, fk_column, pk_column


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = pk_column()
    opportunity_id: Mapped[str] = fk_column()
    opportunity_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    confidence_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    momentum_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    evidence_breadth_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    transferability_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    assortment_gap_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    commercial_feasibility_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    action: Mapped[str | None] = mapped_column(String)
    triggered_rule: Mapped[str | None] = mapped_column(String)
    rationale: Mapped[str | None] = mapped_column(Text)
    supporting_evidence_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    counter_signal_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    risks: Mapped[list | None] = mapped_column(JSON, default=list)
    missing_evidence: Mapped[list | None] = mapped_column(JSON, default=list)
    experiment_plan: Mapped[dict | None] = mapped_column(JSON, default=dict)
    scoring_version: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = created_at_column()
