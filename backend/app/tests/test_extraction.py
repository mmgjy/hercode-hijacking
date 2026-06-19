"""Raw signal extraction via adapters."""
from app.adapters.base import FetchedDocument, get_adapter


JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Anti-Tick Trousers",
 "category":"hiking trousers","brand":{"@type":"Brand","name":"Craghoppers"},
 "material":"ripstop nylon",
 "offers":{"@type":"Offer","price":"99.00","priceCurrency":"EUR","availability":"https://schema.org/InStock"}}
</script></head><body></body></html>
"""

LISTING_HTML = """
<ul><li class="product-card">
  <a class="product-card__link" href="https://example.com/p1">x</a>
  <span class="product-card__brand">Patagonia</span>
  <h3 class="product-card__title">Kids UPF Sun Hoodie</h3>
  <span class="product-card__price">$59.00</span>
  <span class="badge--new">New</span>
</li>
<li class="product-card"><span class="product-card__brand"></span></li></ul>
"""


def test_jsonld_extraction():
    doc = FetchedDocument(url="https://example.org/x", text=JSONLD_HTML, source_key="src", market="EU")
    signals = get_adapter("generic_jsonld").extract(doc)
    assert len(signals) == 1
    s = signals[0]
    assert s["product_name"] == "Anti-Tick Trousers"
    assert s["brand"] == "Craghoppers"
    assert s["price_value"] == 99.0
    assert s["currency"] == "EUR"
    assert s["availability"] == "InStock"
    assert "ripstop nylon" in s["materials"]


def test_listing_extraction_skips_empty_cards():
    selectors = {
        "selectors": {
            "item": "li.product-card",
            "product_name": ".product-card__title",
            "brand": ".product-card__brand",
            "price": ".product-card__price",
            "product_url": "a.product-card__link@href",
            "new_arrival_badge": ".badge--new",
        }
    }
    doc = FetchedDocument(url="https://example.com/x", text=LISTING_HTML, source_key="r", market="US", config=selectors)
    signals = get_adapter("configurable_listing").extract(doc)
    assert len(signals) == 1  # empty card skipped
    s = signals[0]
    assert s["brand"] == "Patagonia"
    assert s["price_value"] == 59.0
    assert s["is_new_arrival"] is True


def test_no_fabrication_when_empty():
    doc = FetchedDocument(url="https://example.com/x", text="<html></html>", source_key="r")
    assert get_adapter("generic_jsonld").extract(doc) == []
