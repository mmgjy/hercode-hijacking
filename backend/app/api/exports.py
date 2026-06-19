from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.errors import AppError, ErrorCode
from app.models import Opportunity
from app.services.export_service import build_export_csv, build_export_dict

router = APIRouter(prefix="/api/opportunities", tags=["exports"])


def _get_opp(db: Session, opportunity_id: str) -> Opportunity:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        raise AppError(ErrorCode.NOT_FOUND, "Opportunity not found.", status_code=404)
    return opp


@router.get("/{opportunity_id}/export.json")
def export_json(opportunity_id: str, db: Session = Depends(get_db)) -> JSONResponse:
    opp = _get_opp(db, opportunity_id)
    return JSONResponse(content=build_export_dict(db, opp))


@router.get("/{opportunity_id}/export.csv")
def export_csv(opportunity_id: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    opp = _get_opp(db, opportunity_id)
    csv_text = build_export_csv(db, opp)
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="opportunity-{opp.id}.csv"'
        },
    )
