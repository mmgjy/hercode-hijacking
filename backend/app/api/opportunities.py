from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_api_key
from app.errors import AppError, ErrorCode
from app.models import (
    NormalizedSignal,
    Opportunity,
    OpportunitySignal,
    RawSignal,
    ScanItem,
)
from app.schemas import (
    CoverageOut,
    OpportunityDetailOut,
    RecommendationOut,
    ScanItemOut,
    TransferabilityOut,
)
from app.schemas.opportunity import EvidenceItem, EvidenceOut
from app.services import recommendation_service as rec_svc

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


def _get_opp(db: Session, opportunity_id: str) -> Opportunity:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        raise AppError(ErrorCode.NOT_FOUND, "Opportunity not found.", status_code=404)
    return opp


@router.get("/{opportunity_id}", response_model=OpportunityDetailOut)
def get_opportunity(opportunity_id: str, db: Session = Depends(get_db)) -> OpportunityDetailOut:
    opp = _get_opp(db, opportunity_id)
    pending = (
        db.query(ScanItem)
        .filter(ScanItem.opportunity_id == opp.id, ScanItem.review_status == "pending")
        .count()
    )
    detail = OpportunityDetailOut.model_validate(opp, from_attributes=True)
    detail.has_recommendation = rec_svc.latest_recommendation(db, opp.id) is not None
    detail.has_coverage = rec_svc.latest_coverage(db, opp.id) is not None
    detail.pending_review_count = pending
    return detail


@router.get("/{opportunity_id}/evidence", response_model=EvidenceOut)
def get_evidence(opportunity_id: str, db: Session = Depends(get_db)) -> EvidenceOut:
    opp = _get_opp(db, opportunity_id)
    rows = (
        db.query(OpportunitySignal, NormalizedSignal, RawSignal)
        .join(NormalizedSignal, NormalizedSignal.id == OpportunitySignal.normalized_signal_id)
        .join(RawSignal, RawSignal.id == NormalizedSignal.raw_signal_id)
        .filter(OpportunitySignal.opportunity_id == opp.id)
        .all()
    )
    evidence = [
        EvidenceItem(
            normalized_signal_id=ns.id,
            raw_signal_id=rs.id,
            cluster_similarity=float(os.cluster_similarity) if os.cluster_similarity is not None else None,
            cluster_terms=os.cluster_terms,
            source_name=rs.source_name,
            source_url=rs.source_url,
            source_type=rs.source_type,
            market=rs.market,
            observed_at=rs.observed_at,
            product_name=rs.product_name,
            brand=rs.brand,
            independence_group=rs.independence_group,
            origin=rs.origin,
        )
        for (os, ns, rs) in rows
    ]
    return EvidenceOut(opportunity_id=opp.id, evidence=evidence)


@router.get("/{opportunity_id}/coverage", response_model=CoverageOut)
def get_coverage(opportunity_id: str, db: Session = Depends(get_db)) -> CoverageOut:
    opp = _get_opp(db, opportunity_id)
    cov = rec_svc.latest_coverage(db, opp.id)
    if cov is None:
        raise AppError(ErrorCode.NOT_FOUND, "No coverage snapshot yet.", status_code=404)
    return CoverageOut.model_validate(cov, from_attributes=True)


@router.get("/{opportunity_id}/recommendation", response_model=RecommendationOut)
def get_recommendation(opportunity_id: str, db: Session = Depends(get_db)) -> RecommendationOut:
    opp = _get_opp(db, opportunity_id)
    rec = rec_svc.latest_recommendation(db, opp.id)
    if rec is None:
        raise AppError(
            ErrorCode.RECOMMENDATION_INCOMPLETE,
            "No recommendation available yet.",
            status_code=404,
        )
    return RecommendationOut.model_validate(rec, from_attributes=True)


@router.get("/{opportunity_id}/transferability", response_model=TransferabilityOut)
def get_transferability(opportunity_id: str, db: Session = Depends(get_db)) -> TransferabilityOut:
    opp = _get_opp(db, opportunity_id)
    t = rec_svc.latest_transferability(db, opp.id)
    if t is None:
        raise AppError(ErrorCode.NOT_FOUND, "No transferability assessment yet.", status_code=404)
    return TransferabilityOut.model_validate(t, from_attributes=True)


@router.get("/{opportunity_id}/scan-items", response_model=list[ScanItemOut])
def get_scan_items(
    opportunity_id: str, db: Session = Depends(get_db), review_status: str | None = None
) -> list[ScanItem]:
    opp = _get_opp(db, opportunity_id)
    q = db.query(ScanItem).filter(ScanItem.opportunity_id == opp.id)
    if review_status:
        q = q.filter(ScanItem.review_status == review_status)
    return q.order_by(ScanItem.match_score.desc()).all()


@router.post(
    "/{opportunity_id}/recalculate",
    response_model=RecommendationOut,
    dependencies=[Depends(require_api_key)],
)
def recalculate(opportunity_id: str, db: Session = Depends(get_db)) -> RecommendationOut:
    opp = _get_opp(db, opportunity_id)
    rec = rec_svc.recompute(db, opp)
    db.commit()
    return RecommendationOut.model_validate(rec, from_attributes=True)
