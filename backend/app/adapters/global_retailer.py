"""Primary global retailer adapter.

A reliable global retailer that exposes a listing page of new arrivals. Defaults
to JSON-LD products and falls back to configured CSS selectors. Marked as a
direct commercial source (higher credibility) by configuration.
"""
from __future__ import annotations

from typing import Any

from app.adapters.base import Adapter, FetchedDocument, register
from app.adapters.configurable_listing import ConfigurableListingAdapter
from app.adapters.generic_jsonld import GenericJsonLdAdapter


class GlobalRetailerAdapter(Adapter):
    key = "global_retailer"

    def __init__(self) -> None:
        self._jsonld = GenericJsonLdAdapter()
        self._listing = ConfigurableListingAdapter()

    def extract(self, doc: FetchedDocument) -> list[dict[str, Any]]:
        signals = self._jsonld.extract(doc)
        if not signals:
            signals = self._listing.extract(doc)
        for s in signals:
            s["source_type"] = doc.source_type or "retailer"
        return signals


register(GlobalRetailerAdapter())
