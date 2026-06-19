"""Discovery-run orchestrator.

Runs the exact pipeline:
    source set -> collect -> extract -> normalize -> dedup -> cluster ->
    qualify -> opportunities -> search terms -> Swiss scan -> match ->
    coverage -> transferability -> score -> recommendation.

Each stage records status/timestamps/warnings/errors on the run. A partial
failure from one source never destroys the run. Demo mode loads structured
fixtures; live/replay collect documents and run the adapters.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import FIXTURES_DIR, load_source_sets
from app.database import SessionLocal
from app.errors import AppError, ErrorCode
from app.logging_config import get_logger
from app.models import (
    DiscoveryRun,
    Opportunity,
    RawSignal,
    RetailerScan,
    ScanItem,
)
from app.models._common import utcnow
from app.services import (
    deduplication_service,
    normalization_service,
    opportunity_service,
    recommendation_service,
    swiss_scan_service,
)
from app.services.clustering_service import cluster_signals
from app.services.collection_service import Collector
from app.services.extraction_service import extract_signals
from app.services.product_matching_service import apply_match
from app.services.swiss_scan_service import ensure_retailers

logger = get_logger(__name__)

NO_QUALIFYING_MESSAGE = (
    "No qualifying opportunities were found in the configured source set and period."
)


def _set_stage(db: Session, run: DiscoveryRun, stage: str) -> None:
    run.current_stage = stage
    db.add(run)
    db.commit()
    logger.info("run=%s stage=%s", run.id, stage)


def _warn(run: DiscoveryRun, message: str) -> None:
    warnings = list(run.warnings or [])
    warnings.append(message)
    run.warnings = warnings


def run_discovery(run_id: str) -> None:
    """Entry point for the background job. Manages its own DB session."""
    db = SessionLocal()
    try:
        run = db.get(DiscoveryRun, run_id)
        if run is None:
            logger.error("run_not_found id=%s", run_id)
            return
        run.status = "running"
        run.started_at = utcnow()
        run.warnings = []
        db.commit()
        try:
            _execute(db, run)
            run.status = "completed"
        except AppError as exc:
            run.status = "failed"
            run.error_message = f"{exc.code.value}: {exc.message}"
            logger.warning("run_failed id=%s code=%s", run_id, exc.code)
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.error_message = str(exc)[:500]
            logger.exception("run_error id=%s", run_id)
        finally:
            run.completed_at = utcnow()
            run.current_stage = None
            db.commit()
    finally:
        db.close()


def _execute(db: Session, run: DiscoveryRun) -> None:
    source_sets = load_source_sets()
    if run.source_set not in source_sets:
        raise AppError(
            ErrorCode.INVALID_SOURCE_SET,
            f"Unknown source set '{run.source_set}'.",
        )

    # --- collect + extract ---
    _set_stage(db, run, "collect")
    if run.mode == "demo":
        raw_signals = _load_demo_signals(db, run)
    else:
        raw_signals = _collect_and_extract(db, run, source_sets[run.source_set])
    run.raw_signal_count = len(raw_signals)
    db.commit()
    if not raw_signals:
        raise AppError(ErrorCode.NO_SIGNALS_FOUND, "No signals collected.")

    # --- normalize ---
    _set_stage(db, run, "normalize")
    normalized = normalization_service.normalize_run(db, raw_signals)
    run.normalized_signal_count = len(normalized)
    db.commit()

    # --- dedup ---
    _set_stage(db, run, "deduplicate")
    if run.mode != "demo":  # demo fixtures carry explicit independence groups
        deduplication_service.assign_independence_groups(db, raw_signals)
    db.commit()

    # --- cluster ---
    _set_stage(db, run, "cluster")
    clusters = cluster_signals(normalized)

    # --- qualify + build opportunities ---
    _set_stage(db, run, "qualify")
    raw_by_id = {r.id: r for r in raw_signals}
    opportunities: list[Opportunity] = []
    for cluster in clusters:
        if len(opportunities) >= run.maximum_opportunities:
            break
        qual = opportunity_service.qualify_cluster(cluster, raw_by_id, run.lookback_days)
        if not qual.qualified:
            continue
        opp = opportunity_service.build_opportunity(
            db,
            discovery_run_id=run.id,
            category=run.category,
            cluster=cluster,
            raw_by_id=raw_by_id,
            qualification=qual,
        )
        opportunities.append(opp)
    run.opportunity_count = len(opportunities)
    db.commit()

    if not opportunities:
        _warn(run, NO_QUALIFYING_MESSAGE)
        run.error_message = NO_QUALIFYING_MESSAGE
        db.commit()
        raise AppError(ErrorCode.NO_QUALIFYING_CLUSTERS, NO_QUALIFYING_MESSAGE)

    # --- Swiss scan + match per opportunity ---
    _set_stage(db, run, "swiss_scan")
    ensure_retailers(db, run.source_set)
    demo_catalog = _load_demo_swiss_catalog() if run.mode == "demo" else None
    for opp in opportunities:
        if run.mode == "demo":
            _apply_demo_swiss_items(db, opp, demo_catalog)
        else:
            _items, warnings = swiss_scan_service.scan_opportunity(
                db, opp=opp, source_set_key=run.source_set, mode=run.mode
            )
            for w in warnings:
                _warn(run, f"SWISS_SCAN_PARTIAL {opp.name}: {w}")
        db.commit()

    # --- coverage + transferability + score + recommendation ---
    _set_stage(db, run, "score")
    for opp in opportunities:
        recommendation_service.recompute(db, opp)
        db.commit()


def _collect_and_extract(
    db: Session, run: DiscoveryRun, sset: dict
) -> list[RawSignal]:
    collector = Collector(run.mode)
    observed = utcnow() - timedelta(days=1)
    all_signals: list[RawSignal] = []
    for src in sset.get("global_sources", []):
        for url in src.get("urls", []):
            result = collector.collect(
                db,
                discovery_run_id=run.id,
                source_key=src["key"],
                url=url,
                source_type=src.get("source_type", "web"),
                market=src.get("market"),
                config=src,
                fixture_subdir="global",
            )
            if result.document is None:
                _warn(run, f"{src['key']}: {result.source_document.error_code}")
                continue
            signals = extract_signals(
                db,
                discovery_run_id=run.id,
                document=result.document,
                source_document=result.source_document,
                adapter_key=src.get("adapter", "generic_jsonld"),
                credibility=src.get("credibility"),
                observed_at=observed,
                mode=run.mode,
            )
            all_signals.extend(signals)
    return all_signals


# --------------------------------------------------------------------------- #
# Demo fixtures
# --------------------------------------------------------------------------- #
def _load_demo_signals(db: Session, run: DiscoveryRun) -> list[RawSignal]:
    path = FIXTURES_DIR / "demo" / "global_signals.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    rows: list[RawSignal] = []
    for entry in data:
        observed = now - timedelta(days=int(entry.get("observed_days_ago", 30)))
        rs = RawSignal(
            discovery_run_id=run.id,
            source_name=entry.get("source_name"),
            source_url=entry.get("source_url"),
            source_type=entry.get("source_type"),
            market=entry.get("market"),
            observed_at=observed,
            product_name=entry.get("product_name"),
            product_type=entry.get("product_type"),
            brand=entry.get("brand"),
            features=entry.get("features", []),
            materials=entry.get("materials", []),
            target_customer=entry.get("target_customer"),
            usage_occasion=entry.get("usage_occasion"),
            price_value=entry.get("price_value"),
            currency=entry.get("currency"),
            availability=entry.get("availability"),
            is_new_arrival=entry.get("is_new_arrival"),
            raw_title=entry.get("raw_title") or entry.get("product_name"),
            raw_description=entry.get("raw_description"),
            independence_group=entry.get("independence_group"),
            origin="DEMO",
        )
        db.add(rs)
        rows.append(rs)
    db.flush()
    return rows


def _load_demo_swiss_catalog() -> list[dict]:
    path = FIXTURES_DIR / "demo" / "swiss_catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_demo_swiss_items(db: Session, opp: Opportunity, catalog: list[dict]) -> None:
    """Match every demo Swiss product against the opportunity; persist matches.

    Items that match above the rejection floor become ScanItems for this
    opportunity (auto_approved / pending depending on score). This reuses the
    real matching logic — only the catalog source differs from live mode.
    """
    retailer_map = {r.key: r for r in ensure_retailers(db, "outdoor_global_default")}
    scans: dict[str, RetailerScan] = {}
    for entry in catalog:
        retailer = retailer_map.get(entry.get("retailer"))
        if retailer is None:
            continue
        if retailer.key not in scans:
            scan = RetailerScan(
                opportunity_id=opp.id,
                retailer_id=retailer.id,
                mode="demo",
                status="ok",
                started_at=utcnow(),
                completed_at=utcnow(),
            )
            db.add(scan)
            db.flush()
            scans[retailer.key] = scan
        item = ScanItem(
            retailer_scan_id=scans[retailer.key].id,
            opportunity_id=opp.id,
            retailer_id=retailer.id,
            title=entry.get("title"),
            brand=entry.get("brand"),
            price_value=entry.get("price_value"),
            currency=entry.get("currency", "CHF"),
            availability=entry.get("availability", "InStock"),
            features=entry.get("features", []),
            product_url=entry.get("product_url"),
            origin="DEMO",
        )
        apply_match(opp, item)
        # Only attach items that are plausibly about this opportunity.
        if item.review_status == "rejected" and not entry.get("force_attach"):
            continue
        if entry.get("force_pending"):
            item.review_status = "pending"
        db.add(item)
    db.flush()
