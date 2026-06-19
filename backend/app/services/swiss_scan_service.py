"""Scan configured Swiss retailers for an opportunity and match products.

Live/replay: collect each retailer's scan URL, extract candidate products via
the Swiss adapter, then match them to the opportunity. Demo: structured scan
items are loaded directly (see ``discovery_service``). A failed retailer yields
a SWISS_SCAN_PARTIAL warning but never aborts the scan; we never fabricate
products after an extraction failure.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.adapters.base import get_adapter
from app.config import load_retailers, load_source_sets
from app.errors import AppError
from app.logging_config import get_logger
from app.models import Opportunity, Retailer, RetailerScan, ScanItem
from app.models._common import utcnow
from app.services.collection_service import Collector
from app.services.product_matching_service import apply_match

logger = get_logger(__name__)


def ensure_retailers(db: Session, source_set_key: str) -> list[Retailer]:
    """Upsert configured Swiss retailers for the source set into the DB."""
    sset = load_source_sets().get(source_set_key, {})
    keys = sset.get("swiss_retailers", [])
    defs = load_retailers()
    retailers: list[Retailer] = []
    for key in keys:
        rdef = defs.get(key)
        if not rdef:
            logger.warning("unknown_retailer key=%s", key)
            continue
        existing = db.query(Retailer).filter_by(key=key).one_or_none()
        if existing is None:
            existing = Retailer(
                key=key,
                name=rdef.get("name", key),
                domain=rdef.get("domain"),
                market=rdef.get("market", "CH"),
                adapter_key=rdef.get("adapter", "swiss_retailer"),
                active=rdef.get("active", True),
            )
            db.add(existing)
            db.flush()
        retailers.append(existing)
    return retailers


def scan_opportunity(
    db: Session,
    *,
    opp: Opportunity,
    source_set_key: str,
    mode: str,
) -> tuple[list[ScanItem], list[str]]:
    """Run live/replay scans for one opportunity. Returns (items, warnings)."""
    retailers = ensure_retailers(db, source_set_key)
    defs = load_retailers()
    collector = Collector(mode)
    items: list[ScanItem] = []
    warnings: list[str] = []

    for retailer in retailers:
        rdef = defs.get(retailer.key, {})
        scan_urls = rdef.get("scan_urls") or ([rdef["search_template"]] if rdef.get("search_template") else [])
        scan = RetailerScan(
            opportunity_id=opp.id,
            retailer_id=retailer.id,
            mode=mode,
            status="running",
            started_at=utcnow(),
        )
        db.add(scan)
        db.flush()
        retailer_items: list[ScanItem] = []
        try:
            for url in scan_urls or [rdef.get("domain", "")]:
                result = collector.collect(
                    db,
                    discovery_run_id=opp.discovery_run_id,
                    source_key=retailer.key,
                    url=url if url.startswith("http") else f"https://{url}",
                    source_type="swiss_retailer",
                    market="CH",
                    config=rdef,
                    fixture_subdir="swiss",
                )
                if result.document is None:
                    raise AppError(
                        result.source_document.error_code,  # type: ignore[arg-type]
                        result.source_document.error_message or "scan failed",
                    )
                scan.source_url = url
                scan.snapshot_uri = result.source_document.snapshot_uri
                scan.content_hash = result.source_document.content_hash
                adapter = get_adapter(retailer.adapter_key or "swiss_retailer")
                for sig in adapter.extract(result.document):
                    item = ScanItem(
                        retailer_scan_id=scan.id,
                        opportunity_id=opp.id,
                        retailer_id=retailer.id,
                        title=sig.get("product_name") or sig.get("raw_title"),
                        brand=sig.get("brand"),
                        price_value=sig.get("price_value"),
                        currency=sig.get("currency"),
                        availability=sig.get("availability"),
                        features=sig.get("features") or [],
                        product_url=sig.get("source_url"),
                        image_url=sig.get("image_url"),
                        origin={"live": "LIVE", "replay": "REPLAY"}.get(mode, "LIVE"),
                    )
                    apply_match(opp, item)
                    db.add(item)
                    retailer_items.append(item)
            scan.status = "ok"
            scan.completed_at = utcnow()
            db.flush()
            items.extend(retailer_items)
        except AppError as exc:
            scan.status = "failed"
            scan.error_code = exc.code.value
            scan.error_message = exc.message
            scan.completed_at = utcnow()
            db.flush()
            warnings.append(f"{retailer.key}: {exc.code.value}")
            logger.warning("swiss_scan_failed retailer=%s code=%s", retailer.key, exc.code)
    return items, warnings
