from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_api_key
from app.jobs import run_now
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
    SourceDocument,
    TransferabilityAssessment,
)
from app.schemas import DiscoveryRunCreate

router = APIRouter(prefix="/api/demo", tags=["demo"])

_DELETE_ORDER = [
    Recommendation,
    TransferabilityAssessment,
    CoverageSnapshot,
    ScanItem,
    RetailerScan,
    OpportunitySignal,
    Opportunity,
    NormalizedSignal,
    RawSignal,
    SourceDocument,
    DiscoveryRun,
]


@router.post("/reset", dependencies=[Depends(require_api_key)])
def demo_reset(db: Session = Depends(get_db)) -> dict:
    """Wipe all data and run a fresh deterministic demo discovery run.

    Runs synchronously so the response returns a ready-to-inspect run id with
    completed opportunities and recommendations.
    """
    for model in _DELETE_ORDER:
        db.execute(delete(model))
    db.commit()

    payload = DiscoveryRunCreate(mode="demo")
    run = DiscoveryRun(
        category=payload.category,
        target_market=payload.target_market,
        source_set=payload.source_set,
        lookback_days=payload.lookback_days,
        maximum_opportunities=payload.maximum_opportunities,
        focus_keywords=payload.focus_keywords,
        mode="demo",
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    run_id = run.id
    run_now(run_id)

    db.expire_all()
    run = db.get(DiscoveryRun, run_id)
    opp_count = (
        db.query(Opportunity).filter(Opportunity.discovery_run_id == run_id).count()
    )
    return {
        "status": "ok",
        "discovery_run_id": run_id,
        "run_status": run.status,
        "opportunity_count": opp_count,
        "message": "Demo data reset and discovery run completed.",
    }
