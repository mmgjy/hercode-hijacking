"""Global momentum, evidence breadth, confidence, commercial feasibility and the
composite opportunity score.

All inputs are observed/derived data; nothing is invented. Where longitudinal
history is unavailable we describe current state as a "repeated recent pattern",
never as "growth". Weights live in ``scoring.yaml``.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.config import load_scoring, load_source_sets
from app.models import Opportunity, RawSignal

SCORING_VERSION = "scoring-1.0.0"

CREDIBILITY_DEFAULTS = {
    "internal": 100,
    "official": 85,
    "retailer": 85,
    "specialist": 65,
    "publication": 65,
    "social": 40,
    "community": 40,
    "unknown": 25,
}


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _credibility_lookup(source_set_key: str) -> dict[str, int]:
    sset = load_source_sets().get(source_set_key, {})
    out: dict[str, int] = {}
    for src in sset.get("global_sources", []):
        if "credibility" in src:
            out[src["key"]] = int(src["credibility"])
    return out


def _signal_credibility(raw: RawSignal, lookup: dict[str, int]) -> int:
    if raw.source_name in lookup:
        return lookup[raw.source_name]
    return CREDIBILITY_DEFAULTS.get((raw.source_type or "unknown").lower(), 25)


def _freshness_score(days: float | None) -> int:
    if days is None:
        return 25
    if days <= 90:
        return 100
    if days <= 180:
        return 80
    if days <= 365:
        return 60
    return 35


def compute_momentum(opp: Opportunity, raws: list[RawSignal], lookback_days: int) -> dict:
    now = datetime.now(timezone.utc)
    n = len(raws)
    # recency: share of signals in the most-recent third of the lookback window
    recent_window = max(30, lookback_days / 3)
    recent = sum(
        1 for r in raws if r.observed_at and (now - _aware(r.observed_at)).days <= recent_window
    )
    recency = (recent / n * 100) if n else 0.0

    independent = opp.independent_source_count
    source_breadth = min(independent / 4, 1.0) * 100

    diversity = max(opp.brand_count, len({(r.product_name or "").lower() for r in raws if r.product_name}))
    diversity_score = min(diversity / 5, 1.0) * 100

    market_breadth = min(opp.market_count / 3, 1.0) * 100

    commercial = sum(1 for r in raws if (r.source_type or "").lower() in ("retailer", "swiss_retailer", "official"))
    commercial_presence = min(commercial / max(1, n), 1.0) * 100

    score = (
        0.30 * recency
        + 0.25 * source_breadth
        + 0.20 * diversity_score
        + 0.15 * market_breadth
        + 0.10 * commercial_presence
    )
    return {
        "score": round(score, 2),
        "components": {
            "recent_signal_activity": round(recency, 2),
            "independent_source_breadth": round(source_breadth, 2),
            "brand_product_diversity": round(diversity_score, 2),
            "market_breadth": round(market_breadth, 2),
            "commercial_source_presence": round(commercial_presence, 2),
        },
        "basis": "repeated recent pattern (no historical growth series available)",
    }


def compute_evidence_breadth(opp: Opportunity, raws: list[RawSignal]) -> dict:
    n = len(raws) or 1
    source_types = len({(r.source_type or "unknown") for r in raws})
    groups = Counter(r.independence_group or r.id for r in raws)
    top_group_share = max(groups.values()) / n

    reward = 0.0
    reward += min(source_types / 3, 1.0) * 30
    reward += min(len(groups) / 4, 1.0) * 25
    reward += 15 if opp.market_count > 1 else 0
    reward += 15 if opp.brand_count > 1 else 0
    reward += 15 if any((r.source_type or "").lower() in ("retailer", "official") for r in raws) else 0

    penalty = 0.0
    penalty += top_group_share * 20  # one-source concentration
    penalty += (sum(1 for r in raws if not r.observed_at) / n) * 10  # missing timestamps
    penalty += (sum(1 for r in raws if not r.source_url) / n) * 10  # missing URLs

    score = max(0.0, min(100.0, reward - penalty))
    return {
        "score": round(score, 2),
        "reward": round(reward, 2),
        "penalty": round(penalty, 2),
        "source_type_count": source_types,
        "independence_group_count": len(groups),
        "top_group_share": round(top_group_share, 3),
    }


def compute_confidence(raws: list[RawSignal], source_set_key: str) -> dict:
    lookup = _credibility_lookup(source_set_key)
    n = len(raws) or 1
    creds = [_signal_credibility(r, lookup) for r in raws]
    avg_cred = sum(creds) / n

    source_diversity = min(len({r.source_name for r in raws if r.source_name}) / 4, 1.0) * 100

    now = datetime.now(timezone.utc)
    fresh = [
        _freshness_score((now - _aware(r.observed_at)).days if r.observed_at else None)
        for r in raws
    ]
    freshness = sum(fresh) / n

    fields = ["product_type", "brand", "price_value", "market", "observed_at"]
    completeness = (
        sum(
            sum(1 for f in fields if getattr(r, f) is not None) / len(fields)
            for r in raws
        )
        / n
        * 100
    )

    score = (
        0.35 * avg_cred
        + 0.25 * source_diversity
        + 0.20 * freshness
        + 0.20 * completeness
    )
    return {
        "score": round(score, 2),
        "components": {
            "source_credibility": round(avg_cred, 2),
            "source_diversity": round(source_diversity, 2),
            "evidence_freshness": round(freshness, 2),
            "data_completeness": round(completeness, 2),
        },
    }


def compute_commercial_feasibility(opp: Opportunity, raws: list[RawSignal]) -> dict:
    """Transparent public-data proxy. NOT a margin/MOQ/conversion estimate."""
    cfg = load_scoring().get("commercial_feasibility", {})
    prices = [float(r.price_value) for r in raws if r.price_value is not None]
    notes = []
    score = 60.0  # neutral baseline

    if prices:
        avg_price = sum(prices) / len(prices)
        if avg_price <= cfg.get("simple_price_ceiling", 150):
            score += 15
            notes.append("observed price range suggests accessible price points")
        elif avg_price >= cfg.get("complex_price_floor", 400):
            score -= 10
            notes.append("high observed prices imply higher commercial complexity")

    complex_terms = set(cfg.get("complexity_terms", ["electronic", "tent", "stove"]))
    text = " ".join(filter(None, [opp.dominant_product_type, " ".join(opp.dominant_materials or [])])).lower()
    if any(t in text for t in complex_terms):
        score -= 10
        notes.append("category implies shipping/handling complexity")

    if opp.brand_count >= 2:
        score += 10
        notes.append("multiple observed brands suggest available supplier landscape")

    score = max(0.0, min(100.0, score))
    return {
        "score": round(score, 2),
        "label": "PROXY",
        "notes": notes,
        "disclaimer": (
            "Public-data proxy only. Excludes retailer margin, supplier terms, MOQ, "
            "internal returns, conversion and stock capacity."
        ),
    }


def compute_opportunity_score(
    *, momentum: float, evidence_breadth: float, transferability: float,
    assortment_gap: float, commercial_feasibility: float,
) -> float:
    cfg = load_scoring().get("opportunity", {})
    w = cfg.get(
        "weights",
        {
            "momentum": 0.25,
            "evidence_breadth": 0.20,
            "transferability": 0.25,
            "assortment_gap": 0.25,
            "commercial_feasibility": 0.05,
        },
    )
    score = (
        w["momentum"] * momentum
        + w["evidence_breadth"] * evidence_breadth
        + w["transferability"] * transferability
        + w["assortment_gap"] * assortment_gap
        + w["commercial_feasibility"] * commercial_feasibility
    )
    return round(score, 2)
