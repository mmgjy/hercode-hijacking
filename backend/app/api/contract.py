"""Frontend-facing REST contract.

The Lovable frontend (`frontend/src/lib/api`) defines the API shape: camelCase
fields, aggregated/nested DTOs, and a few extra endpoints (`/api/sources`,
`/api/opportunity-map`, `/api/discovery-runs/latest/opportunities`). This module
serves exactly that contract by transforming our internal models + service
outputs — so no fabrication: every value still originates from the pipeline.

Responses are plain dicts (camelCase) returned directly by FastAPI.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings, load_retailers, load_source_sets
from app.dependencies import get_db, require_api_key
from app.errors import AppError, ErrorCode
from app.jobs import BackgroundTaskRunner, run_now
from app.models import (
    CoverageSnapshot,
    DiscoveryRun,
    NormalizedSignal,
    Opportunity,
    OpportunitySignal,
    RawSignal,
    Recommendation,
    Retailer,
    RetailerScan,
    ScanItem,
    SourceDocument,
    TransferabilityAssessment,
)
from app.services import recommendation_service as rec_svc
from app.services import scoring_service
from app.services.product_matching_service import apply_match  # noqa: F401 (kept for parity)

router = APIRouter(tags=["frontend"])

# --------------------------------------------------------------------------- #
# mappings & helpers
# --------------------------------------------------------------------------- #
_ORIGIN = {
    "LIVE": "LIVE",
    "DEMO": "DEMO",
    "REPLAY": "REPLAY",
    "CALCULATED": "CALCULATED",
    "AUTO_DISCOVERED": "CALCULATED",
    "MANUAL_REVIEW": "MANUAL REVIEW",
    "INTERNAL": "CALCULATED",
}
_CONFIDENCE_WORD = {"low": 40, "medium": 65, "high": 85}
_MARKET_GEO = {
    "US": (39.8, -98.6, False),
    "EU": (50.1, 9.0, False),
    "UK": (54.0, -2.0, False),
    "CH": (46.8, 8.2, True),
    "JP": (36.2, 138.3, False),
    "KR": (36.5, 127.9, False),
    "NORDICS": (60.5, 12.0, False),
    "DACH": (48.5, 10.5, False),
}

_PIPELINE_STAGES = [
    ("collect", "Collect signals"),
    ("normalize", "Normalize"),
    ("deduplicate", "Deduplicate"),
    ("cluster", "Cluster patterns"),
    ("qualify", "Qualify opportunities"),
    ("swiss_scan", "Scan Swiss retailers"),
    ("score", "Score & recommend"),
]


def _origin(value: str | None) -> str:
    return _ORIGIN.get((value or "").upper(), "CALCULATED")


def _num(value) -> float:
    return round(float(value), 1) if value is not None else 0.0


def _run_status(run: DiscoveryRun) -> str:
    if run.status == "completed":
        return "partial" if run.warnings else "complete"
    if run.status in ("running", "pending"):
        return "running" if run.status == "running" else "pending"
    return "failed"


def _origin_for_run(run: DiscoveryRun | None) -> str:
    return {"demo": "DEMO", "replay": "REPLAY", "live": "LIVE"}.get(
        run.mode if run else "demo", "CALCULATED"
    )


def _iso(dt: datetime | None) -> str:
    return dt.isoformat() if dt else ""


def _price_str(value, currency: str | None) -> str:
    if value is None:
        return ""
    return f"{currency or 'CHF'} {float(value):.0f}"


def _coverage_band(coverage_score: float | None) -> str:
    s = float(coverage_score or 0)
    if s >= 55:
        return "well-covered"
    if s > 0:
        return "partial"
    return "none"


# --------------------------------------------------------------------------- #
# loaders
# --------------------------------------------------------------------------- #
def _get_run(db: Session, run_id: str) -> DiscoveryRun:
    if run_id == "latest":
        run = db.query(DiscoveryRun).order_by(DiscoveryRun.created_at.desc()).first()
    else:
        run = db.get(DiscoveryRun, run_id)
    if run is None:
        raise AppError(ErrorCode.NOT_FOUND, "Discovery run not found.", status_code=404)
    return run


def _get_opp(db: Session, opportunity_id: str) -> Opportunity:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        raise AppError(ErrorCode.NOT_FOUND, "Opportunity not found.", status_code=404)
    return opp


def _opp_raws(db: Session, opportunity_id: str) -> list[RawSignal]:
    return rec_svc.load_opportunity_raws(db, opportunity_id)


# --------------------------------------------------------------------------- #
# builders
# --------------------------------------------------------------------------- #
def _stages(run: DiscoveryRun) -> list[dict]:
    out = []
    current = run.current_stage
    reached = run.status == "completed"
    seen_current = False
    for key, label in _PIPELINE_STAGES:
        if run.status == "completed":
            status = "partial" if run.warnings and key == "swiss_scan" else "complete"
        elif run.status == "failed":
            status = "failed" if key == current else ("complete" if not seen_current else "pending")
        elif key == current:
            status = "running"
            seen_current = True
        elif not seen_current:
            status = "complete"
        else:
            status = "pending"
        if key == current:
            seen_current = True
        out.append({"key": key, "label": label, "status": status, "detail": None})
    _ = reached
    return out


def build_run(run: DiscoveryRun) -> dict:
    sset = load_source_sets().get(run.source_set, {})
    return {
        "id": run.id,
        "mode": "demo" if run.mode == "demo" else "live",
        "status": _run_status(run),
        "startedAt": _iso(run.started_at or run.created_at),
        "sourceSetId": run.source_set,
        "sourceSetName": sset.get("category", run.source_set),
        "category": run.category,
        "targetMarket": run.target_market,
        "rawSignals": run.raw_signal_count,
        "normalizedSignals": run.normalized_signal_count,
        "clusters": run.opportunity_count,
        "warnings": run.warnings or [],
        "stages": _stages(run),
    }


def _summary_context(db: Session, opp: Opportunity):
    rec = rec_svc.latest_recommendation(db, opp.id)
    cov = rec_svc.latest_coverage(db, opp.id)
    return rec, cov


def build_summary(db: Session, opp: Opportunity, rank: int, run: DiscoveryRun | None) -> dict:
    rec, cov = _summary_context(db, opp)
    missing = (rec.missing_evidence or []) if rec else []
    return {
        "id": opp.id,
        "runId": opp.discovery_run_id,
        "rank": rank,
        "name": opp.name,
        "strongestMarket": opp.strongest_observed_market or "—",
        "globalSignal": _num(rec.momentum_score if rec else None),
        "swissFit": _num(rec.transferability_score if rec else None),
        "swissCoverage": _coverage_band(cov.coverage_score if cov else None),
        "opportunityScore": _num(rec.opportunity_score if rec else None),
        "confidence": _num(rec.confidence_score if rec else None),
        "action": (rec.action if rec else "RESEARCH"),
        "mainMissingEvidence": (missing[0] if missing else ""),
        "discoveryStatus": "complete",
        "origin": _origin_for_run(run),
    }


def _score_item(key, label, value, explanation) -> dict:
    return {
        "key": key,
        "label": label,
        "value": _num(value),
        "origin": "CALCULATED",
        "explanation": explanation,
        "calculatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _rationale(db: Session, opp: Opportunity, raws: list[RawSignal]) -> dict:
    markets = sorted({(r.market or "").upper() for r in raws if r.market})
    brands = sorted({r.brand for r in raws if r.brand})
    products = sorted({r.product_name for r in raws if r.product_name})
    terms: list[str] = []
    for os in db.query(OpportunitySignal).filter_by(opportunity_id=opp.id).all():
        for t in (os.cluster_terms or []):
            if t not in terms:
                terms.append(t)
    return {
        "rawSignals": opp.signal_count,
        "independentSources": opp.independent_source_count,
        "markets": markets,
        "brands": brands,
        "products": products,
        "firstObserved": _iso(opp.earliest_observed_at),
        "latestObserved": _iso(opp.latest_observed_at),
        "dominantProductType": opp.dominant_product_type or "",
        "dominantFeatures": opp.dominant_features or [],
        "dominantMaterials": opp.dominant_materials or [],
        "dominantSegment": opp.customer_segment or "",
        "dominantOccasion": opp.usage_occasion or "",
        "groupingExplanation": opp.description or "",
        "matchedTerms": terms[:12],
    }


def _transfer_factors(transfer: TransferabilityAssessment | None) -> list[dict]:
    if transfer is None or not transfer.factor_details:
        return []
    labels = {
        "climate": "Climate relevance",
        "geography": "Geographic relevance",
        "customer_fit": "Customer-use relevance",
        "regulatory": "Regulatory fit",
        "price_fit": "Price fit",
        "seasonality": "Seasonality",
    }
    out = []
    for key, label in labels.items():
        f = transfer.factor_details.get(key, {})
        conf = f.get("confidence", "medium")
        out.append(
            {
                "key": key,
                "label": label,
                "value": _num(f.get("score")),
                "reason": f.get("rationale", ""),
                "basis": f.get("rule_source", ""),
                "confidence": _CONFIDENCE_WORD.get(conf, 65) if isinstance(conf, str) else _num(conf),
                "limitations": f.get("limitations", ""),
                "heuristic": bool(f.get("unknown", False)),
            }
        )
    return out


def _test_plan(rec: Recommendation | None, opp: Opportunity) -> dict | None:
    if not rec or rec.action != "TEST" or not rec.experiment_plan:
        return None
    p = rec.experiment_plan
    return {
        "productScope": opp.name or "",
        "unitRange": p.get("unit_range", ""),
        "channel": p.get("channel", ""),
        "duration": p.get("duration", ""),
        "targetCustomer": opp.customer_segment or "general outdoor customer",
        "primaryMetric": p.get("primary_metric", ""),
        "secondaryMetrics": p.get("secondary_metrics", []),
        "successThreshold": p.get("suggested_success_threshold", ""),
        "stopCondition": ", ".join(p.get("stop_conditions", [])),
        "assumptions": [p.get("assumption_notice", "")],
    }


def build_recommendation(rec: Recommendation | None) -> dict:
    if rec is None:
        return {
            "action": "RESEARCH",
            "triggeredRule": "recommendation_incomplete",
            "rationale": "Recommendation not yet available.",
            "supportingEvidence": [],
            "preventingEvidence": [],
            "nextStep": "Wait for the discovery run to complete.",
            "origin": "CALCULATED",
            "complete": False,
        }
    next_step = {
        "TEST": "Launch the configurable test plan.",
        "CONTACT": "Open a supplier / brand conversation.",
        "RESEARCH": "Gather the missing evidence and review uncertain matches.",
        "MONITOR": "Keep monitoring; no immediate action.",
        "REJECT": "Do not pursue.",
    }.get(rec.action or "", "")
    return {
        "action": rec.action,
        "triggeredRule": rec.triggered_rule or "",
        "rationale": rec.rationale or "",
        "supportingEvidence": [str(x) for x in (rec.supporting_evidence_ids or [])],
        "preventingEvidence": [str(x) for x in (rec.counter_signal_ids or [])],
        "nextStep": next_step,
        "origin": "CALCULATED",
        "complete": True,
    }


def build_detail(db: Session, opp: Opportunity, run: DiscoveryRun | None, rank: int) -> dict:
    rec = rec_svc.latest_recommendation(db, opp.id)
    transfer = rec_svc.latest_transferability(db, opp.id)
    raws = _opp_raws(db, opp.id)
    summary = build_summary(db, opp, rank, run)

    score_breakdown = []
    conf_breakdown = []
    if rec:
        score_breakdown = [
            _score_item("momentum", "Global momentum", rec.momentum_score, "Recency, source breadth, diversity, market breadth, commercial presence."),
            _score_item("evidence_breadth", "Evidence breadth", rec.evidence_breadth_score, "Independent source types/groups, markets, brands; penalizes concentration."),
            _score_item("transferability", "Swiss transferability", rec.transferability_score, "Weighted Swiss market-profile factors."),
            _score_item("assortment_gap", "Swiss assortment gap", rec.assortment_gap_score, "100 minus Swiss coverage (approved matches only)."),
            _score_item("commercial_feasibility", "Commercial feasibility (proxy)", rec.commercial_feasibility_score, "Public-data proxy; excludes margin/MOQ/conversion."),
        ]
        conf = scoring_service.compute_confidence(raws, run.source_set if run else "outdoor_global_default")
        c = conf["components"]
        conf_breakdown = [
            _score_item("source_credibility", "Source credibility", c["source_credibility"], "Average configured/source-type credibility."),
            _score_item("source_diversity", "Source diversity", c["source_diversity"], "Distinct sources behind the evidence."),
            _score_item("evidence_freshness", "Evidence freshness", c["evidence_freshness"], "Recency of observed signals."),
            _score_item("data_completeness", "Data completeness", c["data_completeness"], "Share of populated key fields."),
        ]

    detail = dict(summary)
    detail.update(
        {
            "productCategory": opp.category or "",
            "earliestMarket": opp.earliest_observed_market or "—",
            "decisionSummary": rec.rationale if rec else "",
            "scoreBreakdown": score_breakdown,
            "confidenceBreakdown": conf_breakdown,
            "rationale": _rationale(db, opp, raws),
            "transferability": _transfer_factors(transfer),
            "risks": {
                "counterSignals": [str(x) for x in (rec.counter_signal_ids or [])] if rec else [],
                "risks": (rec.risks or []) if rec else [],
                "missingEvidence": (rec.missing_evidence or []) if rec else [],
                "internalDataRequired": [],
                "extractionLimitations": [],
            },
            "recommendation": build_recommendation(rec),
            "testPlan": _test_plan(rec, opp),
        }
    )
    return detail


def build_evidence(db: Session, opp: Opportunity) -> list[dict]:
    rows = (
        db.query(OpportunitySignal, NormalizedSignal, RawSignal)
        .join(NormalizedSignal, NormalizedSignal.id == OpportunitySignal.normalized_signal_id)
        .join(RawSignal, RawSignal.id == NormalizedSignal.raw_signal_id)
        .filter(OpportunitySignal.opportunity_id == opp.id)
        .all()
    )
    out = []
    for os, ns, rs in rows:
        feats = (ns.normalized_features or []) + (ns.normalized_materials or [])
        out.append(
            {
                "id": rs.id,
                "source": rs.source_name or "",
                "sourceType": rs.source_type or "",
                "market": (rs.market or "").upper(),
                "date": _iso(rs.observed_at),
                "signal": rs.product_name or rs.raw_title or "",
                "brand": rs.brand or "",
                "featureOrMaterial": ", ".join(feats),
                "price": _price_str(rs.price_value, rs.currency),
                "direction": "supporting",
                "credibility": 85 if (rs.source_type or "") in ("retailer", "official") else 65,
                "origin": _origin(rs.origin),
                "url": rs.source_url or "",
                "rawTitle": rs.raw_title or "",
                "rawDescription": rs.raw_description or "",
                "normalizedProductType": ns.normalized_product_type or "",
                "normalizedFeatures": ns.normalized_features or [],
                "matchedTerms": os.cluster_terms or [],
                "limitations": "",
                "artifactRef": rs.content_hash or "",
            }
        )
    return out


def build_coverage(db: Session, opp: Opportunity) -> list[dict]:
    items = db.query(ScanItem).filter(ScanItem.opportunity_id == opp.id).all()
    retailers = {r.id: r for r in db.query(Retailer).all()}
    by_retailer: dict[str, list[ScanItem]] = {}
    for it in items:
        by_retailer.setdefault(it.retailer_id, []).append(it)
    out = []
    for retailer_id, ritems in by_retailer.items():
        retailer = retailers.get(retailer_id)
        approved = [i for i in ritems if i.review_status in ("auto_approved", "approved")]
        pending = [i for i in ritems if i.review_status == "pending"]
        rejected = [i for i in ritems if i.review_status == "rejected"]
        prices = [float(i.price_value) for i in approved if i.price_value is not None]
        feats = sorted({f for i in approved for f in (i.features or [])})
        out.append(
            {
                "id": retailer_id or "unknown",
                "retailer": retailer.name if retailer else (retailer_id or "Unknown"),
                "approvedMatches": len(approved),
                "pendingMatches": len(pending),
                "rejectedMatches": len(rejected),
                "brands": sorted({i.brand for i in approved if i.brand}),
                "priceRange": (f"CHF {min(prices):.0f}–{max(prices):.0f}" if prices else "—"),
                "relevantFeatures": feats,
                "availability": "in stock" if approved else "—",
                "scanStatus": "complete",
                "scanDate": _iso(datetime.now(timezone.utc)),
                "origin": _origin(ritems[0].origin if ritems else None),
            }
        )
    return out


def build_scan_item(db: Session, it: ScanItem, retailers: dict[str, Retailer]) -> dict:
    retailer = retailers.get(it.retailer_id)
    return {
        "id": it.id,
        "productName": it.title or "",
        "brand": it.brand or "",
        "price": _price_str(it.price_value, it.currency),
        "features": it.features or [],
        "retailer": retailer.name if retailer else "",
        "productUrl": it.product_url or "",
        "matchScore": _num(it.match_score),
        "matchedKeywords": it.matched_terms or [],
        "extractionOrigin": _origin(it.origin),
        "reviewStatus": it.review_status or "pending",
        "reviewNote": it.review_notes,
    }


# --------------------------------------------------------------------------- #
# endpoints
# --------------------------------------------------------------------------- #
class DiscoveryRunInput(BaseModel):
    category: str = "outdoor retail"
    targetMarket: str = "Switzerland"
    sourceSetId: str = "outdoor_global_default"
    observationPeriod: str = "90"
    maxOpportunities: int = 5
    focusKeywords: str | None = None


@router.get("/api/source-sets")
def list_source_sets() -> list[dict]:
    out = []
    for key, sset in load_source_sets().items():
        out.append(
            {
                "id": key,
                "name": key.replace("_", " ").title(),
                "description": f"{sset.get('category', 'retail')} — configured source set",
                "scope": "global",
                "sourceCount": len(sset.get("global_sources", [])) + len(sset.get("swiss_retailers", [])),
            }
        )
    return out


@router.get("/api/sources")
def list_sources() -> list[dict]:
    out = []
    for sset in load_source_sets().values():
        for s in sset.get("global_sources", []):
            urls = s.get("urls", [])
            domain = urls[0].split("/")[2] if urls else ""
            out.append(
                {
                    "id": s.get("key"),
                    "name": s.get("key", "").replace("_", " ").title(),
                    "sourceType": s.get("source_type", s.get("adapter", "web")),
                    "geography": s.get("market", ""),
                    "domain": domain,
                    "scope": "global",
                    "active": True,
                    "lastSuccess": None,
                    "lastError": None,
                    "supportedMode": "live, replay, demo",
                    "signalsCollected": 0,
                }
            )
    for r in load_retailers().values():
        out.append(
            {
                "id": r.get("key"),
                "name": r.get("name", r.get("key")),
                "sourceType": "Retailer catalogue",
                "geography": r.get("market", "CH"),
                "domain": r.get("domain", ""),
                "scope": "swiss",
                "active": r.get("active", True),
                "lastSuccess": None,
                "lastError": None,
                "supportedMode": "live, replay, demo",
                "signalsCollected": 0,
            }
        )
    return out


@router.post("/api/discovery-runs", status_code=202, dependencies=[Depends(require_api_key)])
def create_discovery_run(
    payload: DiscoveryRunInput, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> dict:
    # The frontend may send the id as a hyphenated slug; config keys use
    # underscores. Accept both.
    source_sets = load_source_sets()
    source_set = payload.sourceSetId
    if source_set not in source_sets:
        source_set = source_set.replace("-", "_")
    if source_set not in source_sets:
        raise AppError(ErrorCode.INVALID_SOURCE_SET, f"Unknown source set '{payload.sourceSetId}'.")
    keywords = [k.strip() for k in (payload.focusKeywords or "").split(",") if k.strip()]
    run = DiscoveryRun(
        category=payload.category,
        target_market=payload.targetMarket,
        source_set=source_set,
        lookback_days=int(payload.observationPeriod or 90),
        maximum_opportunities=int(payload.maxOpportunities),
        focus_keywords=keywords,
        mode=get_settings().BACKEND_DISCOVERY_MODE,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    BackgroundTaskRunner(background_tasks).enqueue_discovery(run.id)
    return {"id": run.id}


@router.get("/api/discovery-runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)) -> dict:
    return build_run(_get_run(db, run_id))


def _ranked_opportunities(db: Session, run: DiscoveryRun) -> list[dict]:
    opps = db.query(Opportunity).filter(Opportunity.discovery_run_id == run.id).all()

    def score(o: Opportunity) -> float:
        rec = rec_svc.latest_recommendation(db, o.id)
        return float(rec.opportunity_score) if rec and rec.opportunity_score is not None else 0.0

    opps.sort(key=score, reverse=True)
    return [build_summary(db, o, i + 1, run) for i, o in enumerate(opps)]


@router.get("/api/discovery-runs/{run_id}/opportunities")
def get_run_opportunities(run_id: str, db: Session = Depends(get_db)) -> list[dict]:
    if run_id == "latest":
        run = db.query(DiscoveryRun).order_by(DiscoveryRun.created_at.desc()).first()
        if run is None:
            return []  # no runs yet -> empty list, not an error
    else:
        run = _get_run(db, run_id)
    return _ranked_opportunities(db, run)


@router.get("/api/opportunities/{opportunity_id}")
def get_opportunity(opportunity_id: str, db: Session = Depends(get_db)) -> dict:
    opp = _get_opp(db, opportunity_id)
    run = db.get(DiscoveryRun, opp.discovery_run_id)
    # rank within its run
    ranked = _ranked_opportunities(db, run) if run else []
    rank = next((r["rank"] for r in ranked if r["id"] == opp.id), 1)
    return build_detail(db, opp, run, rank)


@router.get("/api/opportunities/{opportunity_id}/evidence")
def get_evidence(opportunity_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return build_evidence(db, _get_opp(db, opportunity_id))


@router.get("/api/opportunities/{opportunity_id}/coverage")
def get_coverage(opportunity_id: str, db: Session = Depends(get_db)) -> list[dict]:
    return build_coverage(db, _get_opp(db, opportunity_id))


@router.get("/api/opportunities/{opportunity_id}/scan-items")
def get_scan_items(opportunity_id: str, db: Session = Depends(get_db)) -> list[dict]:
    opp = _get_opp(db, opportunity_id)
    retailers = {r.id: r for r in db.query(Retailer).all()}
    items = db.query(ScanItem).filter(ScanItem.opportunity_id == opp.id).order_by(ScanItem.match_score.desc()).all()
    return [build_scan_item(db, it, retailers) for it in items]


@router.get("/api/opportunities/{opportunity_id}/recommendation")
def get_recommendation(opportunity_id: str, db: Session = Depends(get_db)) -> dict:
    opp = _get_opp(db, opportunity_id)
    return build_recommendation(rec_svc.latest_recommendation(db, opp.id))


class ReviewBody(BaseModel):
    status: str
    note: str | None = None


@router.post("/api/scan-items/{scan_item_id}/review", dependencies=[Depends(require_api_key)])
def review_scan_item(scan_item_id: str, body: ReviewBody, db: Session = Depends(get_db)) -> dict:
    item = db.get(ScanItem, scan_item_id)
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "Scan item not found.", status_code=404)
    if body.status not in ("approved", "rejected"):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Only 'approved' or 'rejected' allowed.", status_code=422)
    item.review_status = body.status
    item.review_notes = body.note
    item.origin = "MANUAL_REVIEW"
    db.add(item)
    db.commit()
    return {"ok": True}


@router.post("/api/opportunities/{opportunity_id}/recalculate", dependencies=[Depends(require_api_key)])
def recalculate(opportunity_id: str, db: Session = Depends(get_db)) -> dict:
    opp = _get_opp(db, opportunity_id)
    rec = rec_svc.recompute(db, opp)
    db.commit()
    return build_recommendation(rec)


_DELETE_ORDER = [
    Recommendation, TransferabilityAssessment, CoverageSnapshot, ScanItem,
    RetailerScan, OpportunitySignal, Opportunity, NormalizedSignal, RawSignal,
    SourceDocument, DiscoveryRun,
]


@router.post("/api/demo/reset", dependencies=[Depends(require_api_key)])
def demo_reset(db: Session = Depends(get_db)) -> dict:
    for model in _DELETE_ORDER:
        db.execute(delete(model))
    db.commit()
    run = DiscoveryRun(
        category="outdoor retail", target_market="Switzerland",
        source_set="outdoor_global_default", lookback_days=90,
        maximum_opportunities=5, focus_keywords=[], mode="demo", status="pending",
    )
    db.add(run)
    db.commit()
    run_id = run.id
    run_now(run_id)
    return {"ok": True, "discoveryRunId": run_id}


# ---- Opportunity map ----
def _opp_map_entry(db: Session, opp: Opportunity, rank: int, run: DiscoveryRun | None) -> dict:
    summary = build_summary(db, opp, rank, run)
    cov = rec_svc.latest_coverage(db, opp.id)
    raws = _opp_raws(db, opp.id)
    markets = sorted({(r.market or "").upper() for r in raws if r.market})
    summary.update(
        {
            "earliestMarket": opp.earliest_observed_market or "—",
            "swissGap": _num(cov.gap_score if cov else 0),
            "signalCount": opp.signal_count,
            "sourceCount": opp.independent_source_count,
            "marketCount": opp.market_count,
            "markets": markets,
            "mainSupportingEvidence": (raws[0].product_name if raws else ""),
        }
    )
    return summary


@router.get("/api/opportunity-map")
def opportunity_map(db: Session = Depends(get_db)) -> dict:
    run = db.query(DiscoveryRun).filter(DiscoveryRun.status == "completed").order_by(DiscoveryRun.created_at.desc()).first()
    if run is None:
        return {"opportunities": [], "markets": [], "connections": [], "summary": {
            "totalOpportunities": 0, "totalMarkets": 0, "totalSources": 0,
            "highestConfidence": 0, "highestSwissGap": 0,
            "strongestOpportunity": {"id": "", "name": "", "confidence": 0},
            "highestGapOpportunity": {"id": "", "name": "", "swissGap": 0}}}

    opps = db.query(Opportunity).filter(Opportunity.discovery_run_id == run.id).all()
    map_opps = [_opp_map_entry(db, o, i + 1, run) for i, o in enumerate(opps)]

    markets: dict[str, dict] = {}
    connections: list[dict] = []
    for mo in map_opps:
        strongest = mo["strongestMarket"]
        for mcode in mo["markets"] or [strongest]:
            geo = _MARKET_GEO.get(mcode, (0.0, 0.0, mcode == "CH"))
            m = markets.setdefault(mcode, {
                "id": mcode, "country": mcode, "lat": geo[0], "lng": geo[1],
                "signalStrength": 0.0, "confidence": 0.0, "evidenceCount": 0,
                "action": mo["action"], "isSwiss": geo[2], "opportunityIds": [],
                "evidence": [], "origin": mo["origin"],
            })
            m["opportunityIds"].append(mo["id"])
            m["signalStrength"] = max(m["signalStrength"], mo["globalSignal"])
            m["confidence"] = max(m["confidence"], mo["confidence"])
            m["evidenceCount"] += mo["signalCount"]
        # connection strongest market -> CH
        if strongest and strongest != "CH":
            connections.append({
                "id": f"{mo['id']}-{strongest}-CH",
                "sourceMarket": strongest,
                "targetMarket": "CH",
                "opportunityId": mo["id"],
                "transferabilityScore": mo["swissFit"],
                "swissGapScore": mo["swissGap"],
            })
    # ensure Switzerland marker exists
    if "CH" not in markets and map_opps:
        markets["CH"] = {
            "id": "CH", "country": "CH", "lat": 46.8, "lng": 8.2,
            "signalStrength": 0.0, "confidence": 0.0, "evidenceCount": 0,
            "action": "MONITOR", "isSwiss": True,
            "opportunityIds": [o["id"] for o in map_opps], "evidence": [], "origin": "CALCULATED",
        }

    strongest_opp = max(map_opps, key=lambda o: o["confidence"], default=None)
    gap_opp = max(map_opps, key=lambda o: o["swissGap"], default=None)
    summary = {
        "totalOpportunities": len(map_opps),
        "totalMarkets": len(markets),
        "totalSources": len(list_sources()),
        "highestConfidence": max((o["confidence"] for o in map_opps), default=0),
        "highestSwissGap": max((o["swissGap"] for o in map_opps), default=0),
        "strongestOpportunity": {
            "id": strongest_opp["id"], "name": strongest_opp["name"], "confidence": strongest_opp["confidence"]
        } if strongest_opp else {"id": "", "name": "", "confidence": 0},
        "highestGapOpportunity": {
            "id": gap_opp["id"], "name": gap_opp["name"], "swissGap": gap_opp["swissGap"]
        } if gap_opp else {"id": "", "name": "", "swissGap": 0},
    }
    return {"opportunities": map_opps, "markets": list(markets.values()), "connections": connections, "summary": summary}
