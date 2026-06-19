"""Generic Swiss retailer adapter.

Tries extraction in the recommended order: JSON-LD products, then configured CSS
selectors. (Embedded structured state and Playwright are documented fallbacks;
Playwright is gated behind PLAYWRIGHT_ENABLED and out of scope for the offline
demo.) One robust generic adapter is preferred over several fragile per-retailer
scrapers.
"""
from __future__ import annotations

from typing import Any

from app.adapters.base import Adapter, FetchedDocument, register
from app.adapters.configurable_listing import ConfigurableListingAdapter
from app.adapters.generic_jsonld import GenericJsonLdAdapter


class SwissRetailerAdapter(Adapter):
    key = "swiss_retailer"

    def __init__(self) -> None:
        self._jsonld = GenericJsonLdAdapter()
        self._listing = ConfigurableListingAdapter()

    def extract(self, doc: FetchedDocument) -> list[dict[str, Any]]:
        signals = self._jsonld.extract(doc)
        if not signals:
            signals = self._listing.extract(doc)
        for s in signals:
            s["source_type"] = "swiss_retailer"
            s["market"] = "CH"
        return signals


register(SwissRetailerAdapter())
