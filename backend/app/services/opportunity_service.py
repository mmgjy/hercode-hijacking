"""Qualify clusters into opportunities, name them, and derive Swiss search terms.

A cluster only becomes an opportunity when it meets the configured minimum
thresholds (see ``scoring.yaml``). Thresholds are never lowered silently; if
nothing qualifies the run reports NO_QUALIFYING_CLUSTERS.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import load_market_profile, load_scoring
from app.models import NormalizedSignal, Opportunity, OpportunitySignal, RawSignal
from app.services.clustering_service import Cluster

NAMING_VERSION = "naming-1.0.0"


@dataclass
class QualificationResult:
    qualified: bool
    reasons: list[str]
    signal_count: int
    independent_source_count: int
    brand_count: int
    market_count: int


def _raw(raw_by_id: dict[str, RawSignal], ns: NormalizedSignal) -> RawSignal | None:
    return raw_by_id.get(ns.raw_signal_id)


def _dominant(values: list[str]) -> str | None:
    values = [v for v in values if v]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _top_n(values: list[str], n: int) -> list[str]:
    flat = [v for v in values if v]
    return [v for v, _ in Counter(flat).most_common(n)]


def qualify_cluster(
    cluster: Cluster,
    raw_by_id: dict[str, RawSignal],
    lookback_days: int,
) -> QualificationResult:
    cfg = load_scoring().get("qualification", {})
    min_signals = int(cfg.get("min_signals", 3))
    min_sources = int(cfg.get("min_independent_sources", 2))
    min_diversity = int(cfg.get("min_brands_products_markets", 2))
    max_group_share = float(cfg.get("max_independence_group_share", 0.60))

    raws = [r for r in (_raw(raw_by_id, m.signal) for m in cluster.members) if r]
    n = len(raws)
    groups = Counter(r.independence_group or r.id for r in raws)
    independent_sources = len(groups)
    brands = {(r.brand or "").lower() for r in raws if r.brand}
    markets = {(r.market or "").upper() for r in raws if r.market}
    products = {(r.product_name or "").lower() for r in raws if r.product_name}
    diversity = max(len(brands), len(markets), len(products))

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)
    recent = any(r.observed_at and _aware(r.observed_at) >= cutoff for r in raws)

    top_group_share = (max(groups.values()) / n) if n else 1.0

    reasons: list[str] = []
    if n < min_signals:
        reasons.append(f"only {n} signals (<{min_signals})")
    if independent_sources < min_sources:
        reasons.append(f"only {independent_sources} independent sources (<{min_sources})")
    if diversity < min_diversity:
        reasons.append(f"diversity {diversity} (<{min_diversity} brands/products/markets)")
    if not recent:
        reasons.append("no signal within observation period")
    if n and top_group_share > max_group_share:
        reasons.append(
            f"one independence group provides {top_group_share:.0%} (>{max_group_share:.0%})"
        )

    return QualificationResult(
        qualified=not reasons,
        reasons=reasons,
        signal_count=n,
        independent_source_count=independent_sources,
        brand_count=len(brands),
        market_count=len(markets),
    )


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _generate_name(
    product_type: str | None,
    features: list[str],
    materials: list[str],
    customer: str | None,
    usage: str | None,
) -> tuple[str, list[str]]:
    lead = (features[:1] or materials[:1] or [None])[0]
    terms = [t for t in [lead, product_type] if t]
    name_parts = [t for t in [lead, product_type] if t]
    if customer:
        name_parts.append(f"for {customer}")
        terms.append(customer)
    elif usage:
        name_parts.append(f"for {usage}")
        terms.append(usage)
    name = " ".join(name_parts).strip()
    if not name:
        name = product_type or "Outdoor product opportunity"
    return name[:1].upper() + name[1:], terms


def _strongest_and_earliest_market(raws: list[RawSignal]) -> tuple[str | None, str | None, datetime | None, datetime | None]:
    market_counts = Counter((r.market or "").upper() for r in raws if r.market)
    strongest = market_counts.most_common(1)[0][0] if market_counts else None
    dated = [(r.market, _aware(r.observed_at)) for r in raws if r.observed_at and r.market]
    earliest_market = None
    earliest_at = None
    latest_at = None
    if dated:
        dated.sort(key=lambda x: x[1])
        earliest_market = (dated[0][0] or "").upper() or None
        earliest_at = dated[0][1]
        latest_at = dated[-1][1]
    return strongest, earliest_market, earliest_at, latest_at


def generate_search_terms(
    product_type: str | None,
    features: list[str],
    materials: list[str],
    customer: str | None,
    usage: str | None,
) -> list[dict]:
    """Return [{term, language, reason}] derived from opportunity attributes."""
    profile = load_market_profile()
    vocab = profile.get("retail_vocabulary", {})
    terms: list[dict] = []

    def add(term: str | None, language: str, reason: str):
        if not term:
            return
        term = term.strip()
        if term and not any(t["term"].lower() == term.lower() for t in terms):
            terms.append({"term": term, "language": language, "reason": reason})

    if product_type:
        add(product_type, "en", "normalized product type")
    for f in features:
        add(f, "en", "defining feature")
        for tr in vocab.get(f, []):
            add(tr["term"], tr.get("language", "de"), f"localized vocabulary for '{f}'")
    for m in materials:
        add(m, "en", "defining material")
        for tr in vocab.get(m, []):
            add(tr["term"], tr.get("language", "de"), f"localized vocabulary for '{m}'")
    if customer:
        add(customer, "en", "target customer")
    if usage:
        add(usage, "en", "usage occasion")
    return terms


def build_opportunity(
    db: Session,
    *,
    discovery_run_id: str,
    category: str,
    cluster: Cluster,
    raw_by_id: dict[str, RawSignal],
    qualification: QualificationResult,
) -> Opportunity:
    raws = [r for r in (_raw(raw_by_id, m.signal) for m in cluster.members) if r]
    nss = [m.signal for m in cluster.members]

    product_type = _dominant([s.normalized_product_type for s in nss])
    features = _top_n([f for s in nss for f in (s.normalized_features or [])], 5)
    materials = _top_n([m for s in nss for m in (s.normalized_materials or [])], 5)
    customer = _dominant([s.normalized_customer_segment for s in nss])
    usage = _dominant([s.normalized_usage_occasion for s in nss])

    name, naming_terms = _generate_name(product_type, features, materials, customer, usage)
    strongest, earliest_mkt, earliest_at, latest_at = _strongest_and_earliest_market(raws)
    search_terms = generate_search_terms(product_type, features, materials, customer, usage)

    description = (
        f"Auto-discovered pattern across {qualification.signal_count} signals from "
        f"{qualification.independent_source_count} independent sources during the "
        f"selected observation period."
    )

    opp = Opportunity(
        discovery_run_id=discovery_run_id,
        name=name,
        category=category,
        description=description,
        strongest_observed_market=strongest,
        earliest_observed_market=earliest_mkt,
        earliest_observed_at=earliest_at,
        latest_observed_at=latest_at,
        dominant_product_type=product_type,
        dominant_features=features,
        dominant_materials=materials,
        customer_segment=customer,
        usage_occasion=usage,
        search_terms=search_terms,
        signal_count=qualification.signal_count,
        independent_source_count=qualification.independent_source_count,
        brand_count=qualification.brand_count,
        market_count=qualification.market_count,
        naming_terms=naming_terms,
        naming_method="rule_based",
        naming_version=NAMING_VERSION,
        origin="AUTO_DISCOVERED",
    )
    db.add(opp)
    db.flush()

    for member in cluster.members:
        db.add(
            OpportunitySignal(
                opportunity_id=opp.id,
                normalized_signal_id=member.signal.id,
                cluster_similarity=member.similarity,
                cluster_terms=member.terms,
            )
        )
    db.flush()
    return opp
