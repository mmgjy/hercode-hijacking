"""Opportunity naming, strongest-market calculation and search terms."""
from datetime import datetime, timezone

from app.models import RawSignal
from app.services.opportunity_service import (
    _generate_name,
    _strongest_and_earliest_market,
    generate_search_terms,
)


def test_name_structure_feature_plus_type():
    name, terms = _generate_name("hiking trousers", ["insect-protection"], [], None, "trail hiking")
    assert "insect-protection" in name.lower()
    assert "hiking trousers" in name.lower()
    assert "insect-protection" in terms


def test_name_with_customer_segment():
    name, _ = _generate_name("hooded shirt", ["UPF sun protection"], [], "children", "alpine")
    assert "children" in name.lower()


def test_strongest_vs_earliest_market():
    raws = [
        RawSignal(market="US", observed_at=datetime(2026, 5, 1, tzinfo=timezone.utc)),
        RawSignal(market="US", observed_at=datetime(2026, 5, 10, tzinfo=timezone.utc)),
        RawSignal(market="EU", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
    ]
    strongest, earliest, earliest_at, latest_at = _strongest_and_earliest_market(raws)
    assert strongest == "US"   # most signals
    assert earliest == "EU"    # earliest observed in this dataset
    assert earliest_at < latest_at


def test_search_terms_include_localized_vocab():
    terms = generate_search_terms("hiking trousers", ["insect-protection"], [], None, "trail hiking")
    flat = [t["term"] for t in terms]
    assert "hiking trousers" in flat
    assert any("Zeckenschutz" in t for t in flat)  # German retail vocabulary
    assert all("reason" in t for t in terms)
