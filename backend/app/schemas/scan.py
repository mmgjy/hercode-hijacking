from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ScanItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    opportunity_id: str | None = None
    retailer_id: str | None = None
    title: str | None = None
    brand: str | None = None
    price_value: float | None = None
    currency: str | None = None
    availability: str | None = None
    features: list[Any] | None = None
    product_url: str | None = None
    image_url: str | None = None
    match_score: float | None = None
    matched_terms: list[Any] | None = None
    missing_terms: list[Any] | None = None
    match_explanation: str | None = None
    review_status: str | None = None
    review_notes: str | None = None
    origin: str | None = None


class ReviewStatus(str, Enum):
    approved = "approved"
    rejected = "rejected"


class ScanItemReview(BaseModel):
    review_status: ReviewStatus
    review_notes: str | None = None


class CoverageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: str
    configured_retailer_count: int | None = None
    retailers_with_matches: int | None = None
    approved_product_count: int | None = None
    unique_brand_count: int | None = None
    retailer_presence_score: float | None = None
    product_depth_score: float | None = None
    brand_diversity_score: float | None = None
    price_band_coverage_score: float | None = None
    feature_coverage_score: float | None = None
    availability_score: float | None = None
    coverage_score: float | None = None
    gap_score: float | None = None
    calculation_version: str | None = None
    provenance: str = "CALCULATED"
