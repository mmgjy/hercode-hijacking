"""Deterministic decision logic and full recommendation recomputation.

Rules are applied in strict order: REJECT, then TEST, CONTACT, RESEARCH, and
finally MONITOR as the default. This single readable service also recomputes
coverage, transferability and all scores so the same code path serves both the
initial pipeline and the ``/recalculate`` endpoint after human review.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import load_scoring
from app.models import (
    CoverageSnapshot,
    DiscoveryRun,
    NormalizedSignal,
    Opportunity,
    OpportunitySignal,
    RawSignal,
    Recommendation,
    RetailerScan,
    ScanItem,
    TransferabilityAssessment,
)
from app.services import scoring_service
from app.services.coverage_service import calculate_coverage
from app.services.transferability_service import assess_transferability


def load_opportunity_raws(db: Session, opportunity_id: str) -> list[RawSignal]:
    rows = (
        db.query(RawSignal)
        .join(NormalizedSignal, NormalizedSignal.raw_signal_id == RawSignal.id)
        .join(
            OpportunitySignal,
            OpportunitySignal.normalized_signal_id == NormalizedSignal.id,
        )
        .filter(OpportunitySignal.opportunity_id == opportunity_id)
        .all()
    )
    return rows


def _pending_count(db: Session, opportunity_id: str) -> int:
    return (
        db.query(ScanItem)
        .filter(
            ScanItem.opportunity_id == opportunity_id,
            ScanItem.review_status == "pending",
        )
        .count()
    )


def _scan_coverage_sufficient(db: Session, opp: Opportunity, mode: str) -> bool:
    if mode == "demo":
        return True
    ok = (
        db.query(RetailerScan)
        .filter(RetailerScan.opportunity_id == opp.id, RetailerScan.status == "ok")
        .count()
    )
    return ok >= 1


def _default_experiment_plan() -> dict:
    cfg = load_scoring().get("experiment_plan", {})
    return cfg or {
        "unit_range": "40 to 60",
        "channel": "online",
        "duration": "6 to 8 weeks",
        "primary_metric": "sell-through",
        "suggested_success_threshold": "40%",
        "secondary_metrics": [
            "conversion",
            "onsite search activity",
            "returns",
            "customer feedback",
        ],
        "stop_conditions": [
            "very low conversion",
            "high return rate",
            "regulatory concern",
            "product quality concern",
        ],
        "assumption_notice": "Configurable test template, not a sales forecast.",
    }


def _decide(*, ctx: dict) -> dict:
    """Return {action, rule, rationale, risks, missing_evidence}. Order matters."""
    t = load_scoring().get("decision", {})
    opp_score = ctx["opportunity_score"]
    conf = ctx["confidence"]
    transfer = ctx["transferability"]
    gap = ctx["assortment_gap"]
    regulatory = ctx["regulatory_score"]
    pending = ctx["pending_count"]
    counter = ctx["has_critical_counter_signal"]
    scan_ok = ctx["scan_coverage_sufficient"]

    risks: list[str] = []
    missing: list[str] = []

    # --- REJECT (highest precedence) ---
    if transfer < t.get("reject_transferability_below", 40):
        return _r("REJECT", "transferability_below_40",
                  f"Swiss transferability {transfer:.0f} is below the minimum threshold.",
                  risks, missing)
    if regulatory < t.get("reject_regulatory_below", 30):
        return _r("REJECT", "regulatory_fit_below_30",
                  f"Regulatory fit {regulatory:.0f} is below the minimum threshold.",
                  risks, missing)
    if counter:
        return _r("REJECT", "critical_counter_signal",
                  "A critical counter-signal invalidates the opportunity.",
                  risks, missing)

    # --- TEST ---
    if (
        opp_score >= t.get("test_opportunity_min", 70)
        and conf >= t.get("test_confidence_min", 60)
        and transfer >= t.get("test_transferability_min", 65)
        and gap >= t.get("test_gap_min", 55)
        and scan_ok
        and pending == 0
    ):
        return _r("TEST", "all_test_conditions_met",
                  "Strong score, confidence, transferability and assortment gap with "
                  "reviews complete and sufficient scan coverage.",
                  risks, missing)

    # Capture why TEST failed for downstream branches
    if pending > 0:
        missing.append(f"{pending} uncertain Swiss matches awaiting review")
    if not scan_ok:
        missing.append("insufficient Swiss scan coverage")

    # --- CONTACT ---
    if (
        opp_score >= t.get("contact_opportunity_min", 65)
        and transfer >= t.get("contact_transferability_min", 60)
        and gap >= t.get("contact_gap_min", 50)
    ):
        risks.append("Supplier or brand access is the main unresolved issue.")
        return _r("CONTACT", "supplier_access_is_main_gap",
                  "Promising and under-served locally; supplier/brand access is the key "
                  "next step.",
                  risks, missing)

    # --- RESEARCH ---
    # Triggered by incompleteness (unreviewed matches, insufficient scan
    # coverage, or low confidence/source breadth) — NOT by low transferability,
    # which belongs to MONITOR/REJECT.
    research = (
        pending > 0
        or not scan_ok
        or conf < t.get("research_confidence_floor", 60)
    )
    if research and gap >= t.get("test_gap_min", 55):
        if conf < t.get("research_confidence_floor", 60):
            missing.append("confidence below TEST threshold; broaden source evidence")
        return _r("RESEARCH", "evidence_incomplete",
                  "Promising but important evidence is missing or review is incomplete.",
                  risks, missing)

    # --- MONITOR (default) ---
    if gap < t.get("test_gap_min", 55):
        rationale = "Swiss assortment is already substantial; no immediate test justified."
    else:
        rationale = "Credible signal but too early or not yet actionable; keep monitoring."
    return _r("MONITOR", "monitor_default", rationale, risks, missing)


def _r(action, rule, rationale, risks, missing):
    return {
        "action": action,
        "rule": rule,
        "rationale": rationale,
        "risks": risks,
        "missing_evidence": missing,
    }


def recompute(db: Session, opp: Opportunity) -> Recommendation:
    run = db.get(DiscoveryRun, opp.discovery_run_id)
    source_set_key = run.source_set if run else "outdoor_global_default"
    mode = run.mode if run else "demo"
    lookback = run.lookback_days if run else 90

    raws = load_opportunity_raws(db, opp.id)

    coverage = calculate_coverage(db, opp=opp, source_set_key=source_set_key)
    transfer = assess_transferability(db, opp=opp, raws=raws)

    momentum = scoring_service.compute_momentum(opp, raws, lookback)
    breadth = scoring_service.compute_evidence_breadth(opp, raws)
    confidence = scoring_service.compute_confidence(raws, source_set_key)
    feasibility = scoring_service.compute_commercial_feasibility(opp, raws)

    gap = float(coverage.gap_score or 0)
    opp_score = scoring_service.compute_opportunity_score(
        momentum=momentum["score"],
        evidence_breadth=breadth["score"],
        transferability=float(transfer.overall_score or 0),
        assortment_gap=gap,
        commercial_feasibility=feasibility["score"],
    )

    pending = _pending_count(db, opp.id)
    scan_ok = _scan_coverage_sufficient(db, opp, mode)

    # Critical counter-signal: a triggered regulatory flag requiring review with a
    # very low score.
    reg_detail = (transfer.factor_details or {}).get("regulatory", {})
    has_critical_counter = bool(reg_detail.get("requires_review")) and float(
        transfer.regulatory_score or 100
    ) < load_scoring().get("decision", {}).get("reject_regulatory_below", 30)

    decision = _decide(
        ctx={
            "opportunity_score": opp_score,
            "confidence": confidence["score"],
            "transferability": float(transfer.overall_score or 0),
            "assortment_gap": gap,
            "regulatory_score": float(transfer.regulatory_score or 0),
            "pending_count": pending,
            "has_critical_counter_signal": has_critical_counter,
            "scan_coverage_sufficient": scan_ok,
        }
    )

    # Evidence provenance links
    supporting = [s.id for s in raws[:25]]
    approved_items = (
        db.query(ScanItem)
        .filter(
            ScanItem.opportunity_id == opp.id,
            ScanItem.review_status.in_(("auto_approved", "approved")),
        )
        .all()
    )
    counter_ids = [i.id for i in approved_items] if decision["action"] in ("MONITOR", "REJECT") else []
    if reg_detail.get("requires_review"):
        counter_ids.append(f"regulatory:{reg_detail.get('rule_source')}")

    risks = list(decision["risks"])
    if feasibility["notes"]:
        risks.append("Commercial feasibility is a public-data proxy only.")
    missing = list(decision["missing_evidence"])

    experiment_plan = _default_experiment_plan() if decision["action"] == "TEST" else {}

    rec = Recommendation(
        opportunity_id=opp.id,
        opportunity_score=opp_score,
        confidence_score=confidence["score"],
        momentum_score=momentum["score"],
        evidence_breadth_score=breadth["score"],
        transferability_score=float(transfer.overall_score or 0),
        assortment_gap_score=gap,
        commercial_feasibility_score=feasibility["score"],
        action=decision["action"],
        triggered_rule=decision["rule"],
        rationale=decision["rationale"],
        supporting_evidence_ids=supporting,
        counter_signal_ids=counter_ids,
        risks=risks,
        missing_evidence=missing,
        experiment_plan=experiment_plan,
        scoring_version=scoring_service.SCORING_VERSION,
    )
    db.add(rec)
    db.flush()
    return rec


def latest_recommendation(db: Session, opportunity_id: str) -> Recommendation | None:
    return (
        db.query(Recommendation)
        .filter(Recommendation.opportunity_id == opportunity_id)
        .order_by(Recommendation.created_at.desc())
        .first()
    )


def latest_coverage(db: Session, opportunity_id: str) -> CoverageSnapshot | None:
    return (
        db.query(CoverageSnapshot)
        .filter(CoverageSnapshot.opportunity_id == opportunity_id)
        .order_by(CoverageSnapshot.created_at.desc())
        .first()
    )


def latest_transferability(db: Session, opportunity_id: str) -> TransferabilityAssessment | None:
    return (
        db.query(TransferabilityAssessment)
        .filter(TransferabilityAssessment.opportunity_id == opportunity_id)
        .order_by(TransferabilityAssessment.created_at.desc())
        .first()
    )
