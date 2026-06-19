from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.config import load_source_sets
from app.dependencies import get_db, require_api_key
from app.errors import AppError, ErrorCode
from app.jobs import BackgroundTaskRunner
from app.models import DiscoveryRun, NormalizedSignal, Opportunity, RawSignal
from app.schemas import (
    DiscoveryRunCreate,
    DiscoveryRunCreatedOut,
    DiscoveryRunOut,
    OpportunityOut,
    RawSignalOut,
)

router = APIRouter(prefix="/api/discovery-runs", tags=["discovery-runs"])


@router.post(
    "", response_model=DiscoveryRunCreatedOut, status_code=202,
    dependencies=[Depends(require_api_key)],
)
def create_discovery_run(
    payload: DiscoveryRunCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> DiscoveryRunCreatedOut:
    if payload.source_set not in load_source_sets():
        raise AppError(
            ErrorCode.INVALID_SOURCE_SET,
            f"Unknown source set '{payload.source_set}'.",
        )
    run = DiscoveryRun(
        category=payload.category,
        target_market=payload.target_market,
        source_set=payload.source_set,
        lookback_days=payload.lookback_days,
        maximum_opportunities=payload.maximum_opportunities,
        focus_keywords=payload.focus_keywords,
        mode=payload.mode.value,
        status="pending",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    BackgroundTaskRunner(background_tasks).enqueue_discovery(run.id)
    return DiscoveryRunCreatedOut(
        id=run.id,
        status=run.status,
        mode=run.mode,
        message="Discovery run accepted and started in the background.",
    )


@router.get("", response_model=list[DiscoveryRunOut])
def list_discovery_runs(db: Session = Depends(get_db), limit: int = 50) -> list[DiscoveryRun]:
    return (
        db.query(DiscoveryRun)
        .order_by(DiscoveryRun.created_at.desc())
        .limit(min(limit, 200))
        .all()
    )


def _get_run(db: Session, run_id: str) -> DiscoveryRun:
    run = db.get(DiscoveryRun, run_id)
    if run is None:
        raise AppError(ErrorCode.NOT_FOUND, "Discovery run not found.", status_code=404)
    return run


@router.get("/{run_id}", response_model=DiscoveryRunOut)
def get_discovery_run(run_id: str, db: Session = Depends(get_db)) -> DiscoveryRun:
    return _get_run(db, run_id)


@router.get("/{run_id}/signals", response_model=list[RawSignalOut])
def get_run_signals(
    run_id: str, db: Session = Depends(get_db), limit: int = 500
) -> list[RawSignal]:
    _get_run(db, run_id)
    return (
        db.query(RawSignal)
        .filter(RawSignal.discovery_run_id == run_id)
        .limit(min(limit, 2000))
        .all()
    )


@router.get("/{run_id}/opportunities", response_model=list[OpportunityOut])
def get_run_opportunities(run_id: str, db: Session = Depends(get_db)) -> list[Opportunity]:
    _get_run(db, run_id)
    return (
        db.query(Opportunity)
        .filter(Opportunity.discovery_run_id == run_id)
        .order_by(Opportunity.created_at.asc())
        .all()
    )
