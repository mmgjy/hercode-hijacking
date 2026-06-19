from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from app.errors import AppError, ErrorCode

ADAPTER_REGISTRY: dict[str, "Adapter"] = {}


def register(adapter: "Adapter") -> "Adapter":
    ADAPTER_REGISTRY[adapter.key] = adapter
    return adapter


def get_adapter(key: str) -> "Adapter":
    adapter = ADAPTER_REGISTRY.get(key)
    if adapter is None:
        raise AppError(
            ErrorCode.EXTRACTION_FAILED, f"Unknown adapter '{key}'.", status_code=500
        )
    return adapter


@dataclass
class FetchedDocument:
    """A collected document handed to an adapter for extraction."""

    url: str
    text: str
    source_key: str | None = None
    source_type: str | None = None
    market: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


class Adapter(abc.ABC):
    key: str = "base"

    @abc.abstractmethod
    def extract(self, doc: FetchedDocument) -> list[dict[str, Any]]:
        """Return a list of raw signal dicts. Never fabricate values; use None."""
        raise NotImplementedError

    @staticmethod
    def empty_signal() -> dict[str, Any]:
        return {
            "source_name": None,
            "source_url": None,
            "source_type": None,
            "market": None,
            "observed_at": None,
            "product_name": None,
            "product_type": None,
            "brand": None,
            "features": [],
            "materials": [],
            "target_customer": None,
            "usage_occasion": None,
            "price_value": None,
            "currency": None,
            "availability": None,
            "is_new_arrival": None,
            "category_rank": None,
            "raw_title": None,
            "raw_description": None,
            "image_url": None,
        }
