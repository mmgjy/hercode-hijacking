"""Swiss coverage / assortment-gap calculation.

Uses only APPROVED scan items (auto_approved or human-approved). Pending and
rejected items never contribute to coverage. Weights and saturation thresholds
live in ``scoring.yaml``.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import load_scoring, load_source_sets
from app.models import CoverageSnapshot, Opportunity, ScanItem

COVERAGE_VERSION = "coverage-1.0.0"
APPROVED = ("auto_approved", "approved")


def _approved_items(db: Session, opportunity_id: str) -> list[ScanItem]:
    return (
        db.query(ScanItem)
        .filter(
            ScanItem.opportunity_id == opportunity_id,
            ScanItem.review_status.in_(APPROVED),
        )
        .all()
    )


def calculate_coverage(
    db: Session, *, opp: Opportunity, source_set_key: str
) -> CoverageSnapshot:
    cfg = load_scoring().get("coverage", {})
    weights = cfg.get(
        "weights",
        {
            "retailer_presence": 0.20,
            "product_depth": 0.25,
            "brand_diversity": 0.20,
            "price_band_coverage": 0.15,
            "feature_coverage": 0.10,
            "availability": 0.10,
        },
    )
    depth_sat = float(cfg.get("product_depth_saturation", 20))
    brand_sat = float(cfg.get("brand_diversity_saturation", 8))
    price_bands = cfg.get("price_bands", [50, 100, 200])

    sset = load_source_sets().get(source_set_key, {})
    configured_retailer_count = max(1, len(sset.get("swiss_retailers", [])))

    items = _approved_items(db, opp.id)

    retailers_with = {i.retailer_id for i in items if i.retailer_id}
    brands = {(i.brand or "").lower() for i in items if i.brand}
    approved_count = len(items)

    retailer_presence = len(retailers_with) / configured_retailer_count * 100
    product_depth = min(approved_count / depth_sat, 1.0) * 100
    brand_diversity = min(len(brands) / brand_sat, 1.0) * 100

    # price-band coverage: fraction of configured bands with >=1 approved item
    bands = [0, *price_bands, float("inf")]
    covered_bands = set()
    for i in items:
        if i.price_value is None:
            continue
        for b in range(len(bands) - 1):
            if bands[b] <= float(i.price_value) < bands[b + 1]:
                covered_bands.add(b)
    price_band_coverage = (
        len(covered_bands) / (len(bands) - 1) * 100 if items else 0.0
    )

    # feature coverage: fraction of opportunity defining features present in any item
    defining = {f.lower() for f in (opp.dominant_features or [])}
    if defining:
        present = {
            f.lower()
            for i in items
            for f in (i.features or [])
        } | {
            tok
            for i in items
            for tok in (i.title or "").lower().split()
        }
        feature_coverage = (
            len([f for f in defining if any(f in p or p in f for p in present)])
            / len(defining)
            * 100
        )
    else:
        feature_coverage = 0.0

    in_stock = [i for i in items if (i.availability or "").lower() in ("instock", "in stock", "available", "")]
    availability = (len(in_stock) / approved_count * 100) if approved_count else 0.0

    coverage_score = (
        weights["retailer_presence"] * retailer_presence
        + weights["product_depth"] * product_depth
        + weights["brand_diversity"] * brand_diversity
        + weights["price_band_coverage"] * price_band_coverage
        + weights["feature_coverage"] * feature_coverage
        + weights["availability"] * availability
    )
    gap_score = 100 - coverage_score

    snap = CoverageSnapshot(
        opportunity_id=opp.id,
        configured_retailer_count=configured_retailer_count,
        retailers_with_matches=len(retailers_with),
        approved_product_count=approved_count,
        unique_brand_count=len(brands),
        retailer_presence_score=round(retailer_presence, 2),
        product_depth_score=round(product_depth, 2),
        brand_diversity_score=round(brand_diversity, 2),
        price_band_coverage_score=round(price_band_coverage, 2),
        feature_coverage_score=round(feature_coverage, 2),
        availability_score=round(availability, 2),
        coverage_score=round(coverage_score, 2),
        gap_score=round(gap_score, 2),
        calculation_version=COVERAGE_VERSION,
    )
    db.add(snap)
    db.flush()
    return snap
