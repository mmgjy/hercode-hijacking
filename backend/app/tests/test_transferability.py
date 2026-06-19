"""Transferability rules and unknown factors."""
from app.models import Opportunity, RawSignal
from app.services.transferability_service import assess_transferability
from app.tests.conftest import make_run


def _opp(db, **kw):
    run = make_run(db)
    base = dict(
        discovery_run_id=run.id,
        name="X",
        dominant_product_type="hiking trousers",
        dominant_features=[],
        dominant_materials=[],
    )
    base.update(kw)
    opp = Opportunity(**base)
    db.add(opp)
    db.flush()
    return opp


def test_alpine_sun_protection_high_climate(db):
    opp = _opp(
        db,
        dominant_product_type="hooded shirt",
        dominant_features=["UPF sun protection"],
        usage_occasion="alpine",
    )
    t = assess_transferability(db, opp=opp, raws=[])
    assert float(t.climate_score) == 85
    assert t.factor_details["climate"]["origin"] == "CALCULATED"


def test_regulatory_flag_lowers_score_and_requires_review(db):
    opp = _opp(db, dominant_features=["insect-protection"], usage_occasion="trail hiking")
    t = assess_transferability(db, opp=opp, raws=[])
    assert float(t.regulatory_score) == 45
    assert t.factor_details["regulatory"]["requires_review"] is True


def test_unknown_factor_marked_not_invented(db):
    # Product type with no matching profile rule -> price unknown (no prices).
    opp = _opp(db, dominant_product_type="quantum widget", dominant_features=[])
    t = assess_transferability(db, opp=opp, raws=[])
    assert t.factor_details["price_fit"]["unknown"] is True
    assert "Unknown" in t.factor_details["price_fit"]["limitations"]


def test_price_fit_uses_observed_prices(db):
    opp = _opp(db)
    raws = [RawSignal(price_value=120), RawSignal(price_value=999)]
    t = assess_transferability(db, opp=opp, raws=raws)
    assert t.factor_details["price_fit"]["unknown"] is False
    assert 0 < float(t.price_fit_score) < 100  # one of two in band
