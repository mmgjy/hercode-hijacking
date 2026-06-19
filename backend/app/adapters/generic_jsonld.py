"""Generic JSON-LD product extractor.

Reads schema.org ``Product`` and ``ItemList`` blocks embedded in
``<script type="application/ld+json">`` tags. This is the most reliable and
respectful extraction path because it consumes data the site publishes for
machines.
"""
from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup

from app.adapters.base import Adapter, FetchedDocument, register


def _iter_jsonld(soup: BeautifulSoup):
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                yield from data["@graph"]
            else:
                yield data


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _type_matches(node: dict, wanted: str) -> bool:
    t = node.get("@type")
    if isinstance(t, list):
        return wanted in t
    return t == wanted


def _price_from_offers(offers: Any) -> tuple[float | None, str | None, str | None]:
    for off in _as_list(offers):
        if not isinstance(off, dict):
            continue
        price = off.get("price") or off.get("lowPrice")
        currency = off.get("priceCurrency")
        availability = off.get("availability")
        if availability and isinstance(availability, str):
            availability = availability.rsplit("/", 1)[-1]
        try:
            price_val = float(price) if price is not None else None
        except (TypeError, ValueError):
            price_val = None
        return price_val, currency, availability
    return None, None, None


class GenericJsonLdAdapter(Adapter):
    key = "generic_jsonld"

    def extract(self, doc: FetchedDocument) -> list[dict[str, Any]]:
        soup = BeautifulSoup(doc.text, "html.parser")
        signals: list[dict[str, Any]] = []
        for node in _iter_jsonld(soup):
            if not isinstance(node, dict):
                continue
            products: list[dict] = []
            if _type_matches(node, "Product"):
                products = [node]
            elif _type_matches(node, "ItemList"):
                for el in _as_list(node.get("itemListElement")):
                    item = el.get("item") if isinstance(el, dict) else None
                    if isinstance(item, dict) and _type_matches(item, "Product"):
                        products.append(item)
            for prod in products:
                signals.append(self._product_to_signal(prod, doc))
        return signals

    def _product_to_signal(self, prod: dict, doc: FetchedDocument) -> dict[str, Any]:
        sig = self.empty_signal()
        sig.update(
            {
                "source_name": doc.source_key,
                "source_url": prod.get("url") or doc.url,
                "source_type": doc.source_type or "web",
                "market": doc.market,
                "product_name": prod.get("name"),
                "raw_title": prod.get("name"),
                "raw_description": prod.get("description"),
                "image_url": (_as_list(prod.get("image")) or [None])[0],
            }
        )
        brand = prod.get("brand")
        if isinstance(brand, dict):
            sig["brand"] = brand.get("name")
        elif isinstance(brand, str):
            sig["brand"] = brand
        sig["product_type"] = prod.get("category")
        price, currency, availability = _price_from_offers(prod.get("offers"))
        sig["price_value"] = price
        sig["currency"] = currency
        sig["availability"] = availability
        # material may be a string or list
        mats = _as_list(prod.get("material"))
        sig["materials"] = [m for m in mats if isinstance(m, str)]
        return sig


register(GenericJsonLdAdapter())
