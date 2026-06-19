"""Product matching: auto-approve, pending, reject."""
from app.models import Opportunity, ScanItem
from app.services.product_matching_service import match_item


def _opp(**kw):
    base = dict(
        dominant_product_type="hiking trousers",
        dominant_features=["insect-protection"],
        dominant_materials=[],
        customer_segment=None,
        usage_occasion="trail hiking",
        search_terms=[{"term": "insect-protection hiking trousers"}],
    )
    base.update(kw)
    return Opportunity(**base)


def _item(title, features=None):
    return ScanItem(title=title, features=features or [])


def test_strong_match_auto_approved():
    opp = _opp()
    item = _item("Insect-protection hiking trousers", ["insect-protection"])
    res = match_item(opp, item)
    assert res.score >= 85
    assert res.review_status == "auto_approved"


def test_missing_defining_feature_held_for_review():
    opp = _opp()
    # Same product type, but the defining feature is absent -> not auto-approved.
    item = _item("Plain hiking trousers", [])
    res = match_item(opp, item)
    assert res.review_status in ("pending", "rejected")
    assert "insect" in " ".join(res.missing_terms)


def test_partial_match_pending():
    opp = _opp()
    item = _item("Insect mesh hiking trousers", ["insect mesh"])
    res = match_item(opp, item)
    assert res.review_status == "pending"
    assert 55 <= res.score < 85


def test_unrelated_item_rejected():
    opp = _opp()
    item = _item("City camping folding chair", [])
    res = match_item(opp, item)
    assert res.review_status == "rejected"
    assert res.score < 55
