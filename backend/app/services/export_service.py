"""JSON and CSV exports for an opportunity (evidence + scores + recommendation)."""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from app.models import Opportunity, ScanItem
from app.services import recommendation_service as rec_svc


def build_export_dict(db: Session, opp: Opportunity) -> dict[str, Any]:
    rec = rec_svc.latest_recommendation(db, opp.id)
    cov = rec_svc.latest_coverage(db, opp.id)
    transfer = rec_svc.latest_transferability(db, opp.id)
    raws = rec_svc.load_opportunity_raws(db, opp.id)
    items = db.query(ScanItem).filter(ScanItem.opportunity_id == opp.id).all()

    return {
        "opportunity": {
            "id": opp.id,
            "name": opp.name,
            "category": opp.category,
            "description": opp.description,
            "strongest_observed_market": opp.strongest_observed_market,
            "earliest_observed_market": opp.earliest_observed_market,
            "dominant_product_type": opp.dominant_product_type,
            "dominant_features": opp.dominant_features,
            "dominant_materials": opp.dominant_materials,
            "customer_segment": opp.customer_segment,
            "usage_occasion": opp.usage_occasion,
            "signal_count": opp.signal_count,
            "independent_source_count": opp.independent_source_count,
            "brand_count": opp.brand_count,
            "market_count": opp.market_count,
            "search_terms": opp.search_terms,
            "origin": opp.origin,
        },
        "recommendation": _model_dict(rec),
        "coverage": _model_dict(cov),
        "transferability": _model_dict(transfer),
        "evidence": [
            {
                "raw_signal_id": r.id,
                "source_name": r.source_name,
                "source_url": r.source_url,
                "source_type": r.source_type,
                "market": r.market,
                "observed_at": r.observed_at.isoformat() if r.observed_at else None,
                "product_name": r.product_name,
                "brand": r.brand,
                "independence_group": r.independence_group,
                "origin": r.origin,
            }
            for r in raws
        ],
        "swiss_scan_items": [
            {
                "id": i.id,
                "title": i.title,
                "brand": i.brand,
                "price_value": float(i.price_value) if i.price_value is not None else None,
                "currency": i.currency,
                "match_score": float(i.match_score) if i.match_score is not None else None,
                "review_status": i.review_status,
                "product_url": i.product_url,
            }
            for i in items
        ],
    }


def _model_dict(obj) -> dict | None:
    if obj is None:
        return None
    out = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        try:
            from decimal import Decimal

            if isinstance(val, Decimal):
                val = float(val)
        except Exception:  # noqa: BLE001
            pass
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        out[col.name] = val
    return out


def build_export_csv(db: Session, opp: Opportunity) -> str:
    rec = rec_svc.latest_recommendation(db, opp.id)
    cov = rec_svc.latest_coverage(db, opp.id)
    transfer = rec_svc.latest_transferability(db, opp.id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "opportunity_id",
            "opportunity_name",
            "strongest_observed_market",
            "earliest_observed_market",
            "action",
            "triggered_rule",
            "opportunity_score",
            "confidence_score",
            "momentum_score",
            "evidence_breadth_score",
            "transferability_score",
            "assortment_gap_score",
            "commercial_feasibility_score",
            "coverage_score",
            "signal_count",
            "independent_source_count",
            "brand_count",
            "market_count",
        ]
    )
    writer.writerow(
        [
            opp.id,
            opp.name,
            opp.strongest_observed_market,
            opp.earliest_observed_market,
            rec.action if rec else None,
            rec.triggered_rule if rec else None,
            rec.opportunity_score if rec else None,
            rec.confidence_score if rec else None,
            rec.momentum_score if rec else None,
            rec.evidence_breadth_score if rec else None,
            transfer.overall_score if transfer else None,
            cov.gap_score if cov else None,
            rec.commercial_feasibility_score if rec else None,
            cov.coverage_score if cov else None,
            opp.signal_count,
            opp.independent_source_count,
            opp.brand_count,
            opp.market_count,
        ]
    )
    return buf.getvalue()
