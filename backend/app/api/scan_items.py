from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_api_key
from app.errors import AppError, ErrorCode
from app.models import ScanItem
from app.schemas import ScanItemOut, ScanItemReview

router = APIRouter(prefix="/api/scan-items", tags=["scan-items"])


@router.post(
    "/{scan_item_id}/review",
    response_model=ScanItemOut,
    dependencies=[Depends(require_api_key)],
)
def review_scan_item(
    scan_item_id: str, payload: ScanItemReview, db: Session = Depends(get_db)
) -> ScanItem:
    item = db.get(ScanItem, scan_item_id)
    if item is None:
        raise AppError(ErrorCode.NOT_FOUND, "Scan item not found.", status_code=404)
    item.review_status = payload.review_status.value  # only approved/rejected allowed
    item.review_notes = payload.review_notes
    item.origin = "MANUAL_REVIEW"
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
