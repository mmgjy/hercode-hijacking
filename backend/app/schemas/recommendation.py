from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class TransferabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: str
    climate_score: float | None = None
    geography_score: float | None = None
    customer_fit_score: float | None = None
    regulatory_score: float | None = None
    price_fit_score: float | None = None
    seasonality_score: float | None = None
    overall_score: float | None = None
    factor_details: dict[str, Any] | None = None
    market_profile_version: str | None = None
    provenance: str = "CALCULATED"


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    opportunity_id: str
    opportunity_score: float | None = None
    confidence_score: float | None = None
    momentum_score: float | None = None
    evidence_breadth_score: float | None = None
    transferability_score: float | None = None
    assortment_gap_score: float | None = None
    commercial_feasibility_score: float | None = None
    action: str | None = None
    triggered_rule: str | None = None
    rationale: str | None = None
    supporting_evidence_ids: list[Any] | None = None
    counter_signal_ids: list[Any] | None = None
    risks: list[Any] | None = None
    missing_evidence: list[Any] | None = None
    experiment_plan: dict[str, Any] | None = None
    scoring_version: str | None = None
    provenance: str = "CALCULATED"
