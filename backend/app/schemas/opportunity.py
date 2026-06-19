from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    discovery_run_id: str
    name: str | None = None
    category: str | None = None
    description: str | None = None
    strongest_observed_market: str | None = None
    earliest_observed_market: str | None = None
    earliest_observed_at: datetime | None = None
    latest_observed_at: datetime | None = None
    dominant_product_type: str | None = None
    dominant_features: list[Any] | None = None
    dominant_materials: list[Any] | None = None
    customer_segment: str | None = None
    usage_occasion: str | None = None
    search_terms: list[Any] | None = None
    signal_count: int
    independent_source_count: int
    brand_count: int
    market_count: int
    naming_terms: list[Any] | None = None
    naming_method: str | None = None
    origin: str


class EvidenceItem(BaseModel):
    normalized_signal_id: str
    raw_signal_id: str | None = None
    cluster_similarity: float | None = None
    cluster_terms: list[Any] | None = None
    source_name: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    market: str | None = None
    observed_at: datetime | None = None
    product_name: str | None = None
    brand: str | None = None
    independence_group: str | None = None
    origin: str | None = None


class EvidenceOut(BaseModel):
    opportunity_id: str
    provenance: str = "AUTO_DISCOVERED"
    evidence: list[EvidenceItem]


class OpportunityDetailOut(OpportunityOut):
    has_recommendation: bool = False
    has_coverage: bool = False
    pending_review_count: int = 0
