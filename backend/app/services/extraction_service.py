"""Extract raw product/market signals from collected documents using adapters."""
from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.adapters.base import FetchedDocument, get_adapter
from app.logging_config import get_logger
from app.models import RawSignal, SourceDocument

logger = get_logger(__name__)


def _signal_hash(sig: dict) -> str:
    key = "|".join(
        str(sig.get(k) or "")
        for k in ("product_name", "brand", "source_url", "price_value")
    ).lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def extract_signals(
    db: Session,
    *,
    discovery_run_id: str,
    document: FetchedDocument,
    source_document: SourceDocument,
    adapter_key: str,
    credibility: int | None = None,
    observed_at=None,
    mode: str = "live",
) -> list[RawSignal]:
    """Run the adapter on one document and persist RawSignal rows.

    Origin reflects the collection mode (LIVE/REPLAY/DEMO). Missing fields stay
    None — never fabricated.
    """
    adapter = get_adapter(adapter_key)
    extracted = adapter.extract(document)
    rows: list[RawSignal] = []
    origin = {"live": "LIVE", "replay": "REPLAY", "demo": "DEMO"}.get(mode, "LIVE")
    for sig in extracted:
        rs = RawSignal(
            discovery_run_id=discovery_run_id,
            source_document_id=source_document.id,
            source_name=sig.get("source_name") or document.source_key,
            source_url=sig.get("source_url") or document.url,
            source_type=sig.get("source_type") or document.source_type,
            market=sig.get("market") or document.market,
            observed_at=observed_at,
            product_name=sig.get("product_name"),
            product_type=sig.get("product_type"),
            brand=sig.get("brand"),
            features=sig.get("features") or [],
            materials=sig.get("materials") or [],
            target_customer=sig.get("target_customer"),
            usage_occasion=sig.get("usage_occasion"),
            price_value=sig.get("price_value"),
            currency=sig.get("currency"),
            availability=sig.get("availability"),
            is_new_arrival=sig.get("is_new_arrival"),
            category_rank=sig.get("category_rank"),
            raw_title=sig.get("raw_title"),
            raw_description=sig.get("raw_description"),
            image_url=sig.get("image_url"),
            content_hash=_signal_hash(sig),
            origin=origin,
        )
        db.add(rs)
        rows.append(rs)
    db.flush()
    logger.info(
        "extracted source=%s count=%d", document.source_key, len(rows)
    )
    return rows
