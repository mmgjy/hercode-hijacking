"""Configurable CSS-selector listing extractor.

Used when a source has no usable JSON-LD. Selectors live in the source-set
configuration so a new listing page can be supported by config alone.

Example config block::

    selectors:
      item: "li.product-card"
      product_name: ".product-card__title"
      brand: ".product-card__brand"
      price: ".product-card__price"
      product_url: "a.product-card__link@href"
      image_url: "img@src"
      new_arrival_badge: ".badge--new"

A ``field@attr`` selector reads an attribute instead of text.
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from app.adapters.base import Adapter, FetchedDocument, register

_PRICE_RE = re.compile(r"(\d[\d'.,]*)")
_CURRENCY_RE = re.compile(r"(CHF|EUR|USD|GBP|\$|€|£)")


def _select_value(node, selector: str | None) -> str | None:
    if not selector:
        return None
    attr = None
    if "@" in selector:
        selector, attr = selector.rsplit("@", 1)
    el = node.select_one(selector) if selector else node
    if el is None:
        return None
    if attr:
        val = el.get(attr)
        return val.strip() if isinstance(val, str) else None
    text = el.get_text(strip=True)
    return text or None


def _parse_price(text: str | None) -> tuple[float | None, str | None]:
    if not text:
        return None, None
    currency = None
    cm = _CURRENCY_RE.search(text)
    if cm:
        sym = cm.group(1)
        currency = {"$": "USD", "€": "EUR", "£": "GBP"}.get(sym, sym)
    pm = _PRICE_RE.search(text)
    if not pm:
        return None, currency
    num = pm.group(1).replace("'", "").replace(" ", "")
    # Heuristic: if both , and . present, assume , is thousands sep
    if "," in num and "." in num:
        num = num.replace(",", "")
    elif "," in num:
        num = num.replace(",", ".")
    try:
        return float(num), currency
    except ValueError:
        return None, currency


class ConfigurableListingAdapter(Adapter):
    key = "configurable_listing"

    def extract(self, doc: FetchedDocument) -> list[dict[str, Any]]:
        selectors = (doc.config or {}).get("selectors", {})
        item_sel = selectors.get("item")
        if not item_sel:
            return []
        soup = BeautifulSoup(doc.text, "html.parser")
        signals: list[dict[str, Any]] = []
        for node in soup.select(item_sel):
            sig = self.empty_signal()
            sig.update(
                {
                    "source_name": doc.source_key,
                    "source_url": _select_value(node, selectors.get("product_url"))
                    or doc.url,
                    "source_type": doc.source_type or "web",
                    "market": doc.market,
                    "product_name": _select_value(node, selectors.get("product_name")),
                    "raw_title": _select_value(node, selectors.get("product_name")),
                    "brand": _select_value(node, selectors.get("brand")),
                    "product_type": _select_value(node, selectors.get("product_type")),
                    "image_url": _select_value(node, selectors.get("image_url")),
                    "raw_description": _select_value(
                        node, selectors.get("description")
                    ),
                }
            )
            price_val, currency = _parse_price(
                _select_value(node, selectors.get("price"))
            )
            sig["price_value"] = price_val
            sig["currency"] = currency or doc.config.get("default_currency")
            if selectors.get("new_arrival_badge"):
                sig["is_new_arrival"] = (
                    node.select_one(selectors["new_arrival_badge"]) is not None
                )
            if not (sig["product_name"] or sig["brand"]):
                continue  # skip empty cards
            signals.append(sig)
        return signals


register(ConfigurableListingAdapter())
