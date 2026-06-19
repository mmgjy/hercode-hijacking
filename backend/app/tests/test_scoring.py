"""Confidence and momentum scoring."""
from datetime import datetime, timedelta, timezone

from app.models import Opportunity, RawSignal
from app.services import scoring_service


def _raw(**kw):
    base = dict(features=[], materials=[])
    base.update(kw)
    return RawSignal(**base)


def test_confidence_rewards_credible_fresh_complete_signals():
    now = datetime.now(timezone.utc)
    fresh = [
        _raw(source_name="global_retailer_primary", source_type="retailer",
             product_type="x", brand="A", price_value=10, market="US", observed_at=now)
        for _ in range(3)
    ]
    high = scoring_service.compute_confidence(fresh, "outdoor_global_default")

    stale_unknown = [
        _raw(source_type="unknown", observed_at=now - timedelta(days=800))
        for _ in range(3)
    ]
    low = scoring_service.compute_confidence(stale_unknown, "outdoor_global_default")
    assert high["score"] > low["score"]
    assert high["components"]["source_credibility"] >= 85


def test_confidence_freshness_buckets():
    now = datetime.now(timezone.utc)
    recent = scoring_service.compute_confidence(
        [_raw(observed_at=now, source_type="retailer", product_type="x", brand="A", price_value=1, market="US")],
        "outdoor_global_default",
    )
    assert recent["components"]["evidence_freshness"] == 100


def test_momentum_describes_pattern_not_growth():
    opp = Opportunity(independent_source_count=3, brand_count=3, market_count=2)
    now = datetime.now(timezone.utc)
    raws = [_raw(observed_at=now, market="US", product_name=f"p{i}", source_type="retailer") for i in range(3)]
    m = scoring_service.compute_momentum(opp, raws, lookback_days=90)
    # Honest language: no unsupported growth claim; describes a repeated pattern.
    assert "repeated recent pattern" in m["basis"]
    assert "no historical growth series" in m["basis"]


def test_commercial_feasibility_is_labelled_proxy():
    opp = Opportunity(dominant_product_type="hiking trousers", dominant_materials=[], brand_count=2)
    f = scoring_service.compute_commercial_feasibility(opp, [_raw(price_value=90)])
    assert f["label"] == "PROXY"
    assert "proxy" in f["disclaimer"].lower()
