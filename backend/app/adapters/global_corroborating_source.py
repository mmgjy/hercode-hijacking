"""Independent corroborating global source adapter.

A second, independent source (e.g. a specialist outdoor publication's product
roundup) used to corroborate retailer signals. Independence matters for
deduplication and evidence breadth, so it is configured with a distinct
``source_type`` and credibility.
"""
from __future__ import annotations

from typing import Any

from app.adapters.base import Adapter, FetchedDocument, register
from app.adapters.configurable_listing import ConfigurableListingAdapter
from app.adapters.generic_jsonld import GenericJsonLdAdapter


class GlobalCorroboratingSourceAdapter(Adapter):
    key = "global_corroborating_source"

    def __init__(self) -> None:
        self._jsonld = GenericJsonLdAdapter()
        self._listing = ConfigurableListingAdapter()

    def extract(self, doc: FetchedDocument) -> list[dict[str, Any]]:
        signals = self._jsonld.extract(doc)
        if not signals:
            signals = self._listing.extract(doc)
        for s in signals:
            s["source_type"] = doc.source_type or "publication"
        return signals


register(GlobalCorroboratingSourceAdapter())
