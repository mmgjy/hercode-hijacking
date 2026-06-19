"""Deterministic decision rules and precedence."""
from app.services.recommendation_service import _decide


def _ctx(**kw):
    base = dict(
        opportunity_score=80,
        confidence=70,
        transferability=75,
        assortment_gap=80,
        regulatory_score=85,
        pending_count=0,
        has_critical_counter_signal=False,
        scan_coverage_sufficient=True,
    )
    base.update(kw)
    return base


def test_reject_takes_precedence_over_strong_scores():
    # Strong scores but transferability below 40 -> REJECT wins.
    d = _decide(ctx=_ctx(transferability=30))
    assert d["action"] == "REJECT"
    assert d["rule"] == "transferability_below_40"


def test_reject_on_regulatory():
    d = _decide(ctx=_ctx(regulatory_score=20))
    assert d["action"] == "REJECT"


def test_reject_on_critical_counter_signal():
    d = _decide(ctx=_ctx(has_critical_counter_signal=True))
    assert d["action"] == "REJECT"


def test_test_when_all_conditions_met():
    d = _decide(ctx=_ctx())
    assert d["action"] == "TEST"


def test_no_test_when_reviews_pending():
    d = _decide(ctx=_ctx(pending_count=2))
    assert d["action"] != "TEST"


def test_contact_when_supplier_access_is_gap():
    # Below TEST score but above CONTACT thresholds.
    d = _decide(ctx=_ctx(opportunity_score=66, confidence=55))
    assert d["action"] == "CONTACT"


def test_research_when_incomplete():
    # Pending reviews, gap high -> RESEARCH.
    d = _decide(ctx=_ctx(opportunity_score=60, pending_count=3, assortment_gap=80))
    assert d["action"] == "RESEARCH"


def test_monitor_when_swiss_coverage_high():
    # Low assortment gap (Swiss already well covered) -> MONITOR.
    d = _decide(ctx=_ctx(opportunity_score=60, assortment_gap=30, transferability=58))
    assert d["action"] == "MONITOR"
