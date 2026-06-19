"""Clustering and qualification thresholds."""
import uuid
from datetime import datetime, timezone

from app.models import NormalizedSignal, RawSignal
from app.services.clustering_service import cluster_signals
from app.services.opportunity_service import qualify_cluster


def _ns(pt, features=None, materials=None, customer=None, usage=None):
    return NormalizedSignal(
        id=str(uuid.uuid4()),
        raw_signal_id=str(uuid.uuid4()),
        normalized_product_type=pt,
        normalized_features=features or [],
        normalized_materials=materials or [],
        normalized_customer_segment=customer,
        normalized_usage_occasion=usage,
    )


def test_related_signals_cluster_together():
    sigs = [
        _ns("hiking trousers", ["insect-protection"], usage="trail hiking"),
        _ns("hiking trousers", ["insect-protection"], usage="hiking"),
        _ns("hiking trousers", ["insect-protection"], materials=["ripstop nylon"]),
    ]
    clusters = cluster_signals(sigs)
    assert len(clusters) == 1
    assert len(clusters[0].members) == 3


def test_unrelated_categories_do_not_merge():
    sigs = [
        _ns("hiking trousers", ["insect-protection"], usage="trail hiking"),
        _ns("hiking trousers", ["insect-protection"], usage="hiking"),
        _ns("hooded shirt", ["UPF sun protection"], customer="children", usage="alpine hiking"),
        _ns("hooded shirt", ["UPF sun protection"], customer="children", usage="alpine"),
    ]
    clusters = cluster_signals(sigs)
    # "protection" token is shared but must not collapse the two categories.
    assert len(clusters) == 2


def _raw(ns, brand, market, group, days_ago=10):
    return RawSignal(
        id=ns.raw_signal_id,
        brand=brand,
        market=market,
        product_name=f"{brand} {market}",
        independence_group=group,
        observed_at=datetime.now(timezone.utc).replace(microsecond=0),
    )


def test_qualification_requires_minimums():
    sigs = [
        _ns("hiking trousers", ["insect-protection"]),
        _ns("hiking trousers", ["insect-protection"]),
        _ns("hiking trousers", ["insect-protection"]),
    ]
    clusters = cluster_signals(sigs)
    cluster = clusters[0]
    # Three independent groups (no group >60%), two brands -> qualifies
    raw_by_id = {
        sigs[0].raw_signal_id: _raw(sigs[0], "BrandA", "US", "g1"),
        sigs[1].raw_signal_id: _raw(sigs[1], "BrandB", "EU", "g2"),
        sigs[2].raw_signal_id: _raw(sigs[2], "BrandA", "US", "g3"),
    }
    res = qualify_cluster(cluster, raw_by_id, lookback_days=90)
    assert res.qualified
    assert res.independent_source_count == 3
    assert res.brand_count == 2


def test_qualification_fails_on_single_source_concentration():
    sigs = [_ns("hiking trousers", ["insect-protection"]) for _ in range(4)]
    clusters = cluster_signals(sigs)
    raw_by_id = {
        s.raw_signal_id: _raw(s, "BrandA", "US", "g1") for s in sigs
    }  # all same group -> >60% concentration & single source
    res = qualify_cluster(clusters[0], raw_by_id, lookback_days=90)
    assert not res.qualified
    assert any("independence group" in r for r in res.reasons)


def test_qualification_fails_when_no_recent_signal():
    sigs = [_ns("hiking trousers", ["insect-protection"]) for _ in range(3)]
    clusters = cluster_signals(sigs)
    raw_by_id = {}
    for i, s in enumerate(sigs):
        r = _raw(s, f"Brand{i}", "US", f"g{i}")
        r.observed_at = datetime(2000, 1, 1, tzinfo=timezone.utc)  # very old
        raw_by_id[s.raw_signal_id] = r
    res = qualify_cluster(clusters[0], raw_by_id, lookback_days=90)
    assert not res.qualified
    assert any("observation period" in r for r in res.reasons)
