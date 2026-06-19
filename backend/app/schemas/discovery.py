from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunMode(str, Enum):
    live = "live"
    replay = "replay"
    demo = "demo"


class DiscoveryRunCreate(BaseModel):
    category: str = "outdoor retail"
    target_market: str = "Switzerland"
    source_set: str = "outdoor_global_default"
    lookback_days: int = Field(default=90, ge=1, le=1825)
    maximum_opportunities: int = Field(default=5, ge=1, le=50)
    focus_keywords: list[str] = Field(default_factory=list)
    mode: RunMode = RunMode.demo

    @field_validator("focus_keywords")
    @classmethod
    def strip_keywords(cls, v: list[str]) -> list[str]:
        return [k.strip() for k in v if k and k.strip()]


class SourceSetOut(BaseModel):
    key: str
    category: str | None = None
    global_source_count: int
    swiss_retailer_count: int
    global_sources: list[dict[str, Any]]
    swiss_retailers: list[str]


class DiscoveryRunCreatedOut(BaseModel):
    id: str
    status: str
    mode: str
    message: str


class DiscoveryRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    target_market: str
    source_set: str
    lookback_days: int
    maximum_opportunities: int
    focus_keywords: list[str] | None = None
    mode: str
    status: str
    current_stage: str | None = None
    raw_signal_count: int
    normalized_signal_count: int
    opportunity_count: int
    warnings: list[Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class RawSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_name: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    market: str | None = None
    observed_at: datetime | None = None
    product_name: str | None = None
    product_type: str | None = None
    brand: str | None = None
    features: list[Any] | None = None
    materials: list[Any] | None = None
    target_customer: str | None = None
    usage_occasion: str | None = None
    price_value: float | None = None
    currency: str | None = None
    availability: str | None = None
    is_new_arrival: bool | None = None
    raw_title: str | None = None
    image_url: str | None = None
    content_hash: str | None = None
    independence_group: str | None = None
    origin: str | None = None
