"""Coverage calculation: only approved items count."""
from app.models import Opportunity, Retailer, ScanItem
from app.services.coverage_service import calculate_coverage
from app.tests.conftest import make_run


def _setup(db, statuses):
    run = make_run(db)
    opp = Opportunity(discovery_run_id=run.id, name="X", dominant_features=[])
    db.add(opp)
    db.flush()
    retailer = Retailer(key="transa", name="Transa", domain="transa.ch")
    db.add(retailer)
    db.flush()
    for i, (status, brand) in enumerate(statuses):
        db.add(
            ScanItem(
                opportunity_id=opp.id,
                retailer_id=retailer.id,
                title=f"item {i}",
                brand=brand,
                price_value=80,
                availability="InStock",
                review_status=status,
            )
        )
    db.commit()
    return opp


def test_rejected_and_pending_excluded(db):
    opp = _setup(
        db,
        [("auto_approved", "A"), ("approved", "B"), ("pending", "C"), ("rejected", "D")],
    )
    cov = calculate_coverage(db, opp=opp, source_set_key="outdoor_global_default")
    assert cov.approved_product_count == 2
    assert cov.unique_brand_count == 2  # only A and B
    assert 0 < cov.coverage_score < 100
    assert round(cov.coverage_score + cov.gap_score, 2) == 100.0


def test_zero_coverage_when_nothing_approved(db):
    opp = _setup(db, [("pending", "A"), ("rejected", "B")])
    cov = calculate_coverage(db, opp=opp, source_set_key="outdoor_global_default")
    assert cov.approved_product_count == 0
    assert cov.coverage_score == 0
    assert cov.gap_score == 100
