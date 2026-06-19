"""Swiss transferability assessment driven entirely by the market profile.

No hidden AI judgement: every factor score comes from a transparent rule or
piece of evidence in ``market_profile_ch.yaml``. Each factor returns its score,
rationale, the rule/evidence source, a confidence, limitations and
origin=CALCULATED. When no rule applies the factor is marked unknown (not
invented) and contributes a neutral default so it neither rewards nor punishes.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import load_market_profile
from app.models import Opportunity, RawSignal, TransferabilityAssessment
from app.services.text_utils import token_set

WEIGHTS = {
    "climate": 0.20,
    "geography": 0.20,
    "customer_fit": 0.20,
    "regulatory": 0.15,
    "price_fit": 0.15,
    "seasonality": 0.10,
}
# Profile-key alias for the customer_fit factor (profile uses "customer_use").
PROFILE_KEY = {
    "climate": "climate",
    "geography": "geography",
    "customer_fit": "customer_use",
    "seasonality": "seasonality",
}
NEUTRAL_UNKNOWN = 50.0


def _opp_tokens(opp: Opportunity) -> set[str]:
    parts = [
        opp.dominant_product_type or "",
        " ".join(opp.dominant_features or []),
        " ".join(opp.dominant_materials or []),
        opp.customer_segment or "",
        opp.usage_occasion or "",
        opp.name or "",
    ]
    return token_set(" ".join(parts))


def _resolve_factor(factor: str, profile: dict, tokens: set[str]) -> dict:
    categories = profile.get(PROFILE_KEY.get(factor, factor), {})
    best = None
    best_overlap = 0
    for cat_key, cat in categories.items():
        match_terms = set()
        for m in cat.get("match", []):
            match_terms |= token_set(m)
        overlap = len(match_terms & tokens)
        if overlap > best_overlap:
            best_overlap = overlap
            best = (cat_key, cat)
    if best is None:
        return {
            "factor": factor,
            "score": NEUTRAL_UNKNOWN,
            "rationale": "No matching rule in the market profile.",
            "rule_source": f"market_profile_ch.{PROFILE_KEY.get(factor, factor)}",
            "confidence": "low",
            "limitations": "Unknown — neutral default applied; not an observed score.",
            "origin": "CALCULATED",
            "unknown": True,
        }
    cat_key, cat = best
    return {
        "factor": factor,
        "score": float(cat.get("score", NEUTRAL_UNKNOWN)),
        "rationale": cat.get("rationale", ""),
        "rule_source": f"market_profile_ch.{PROFILE_KEY.get(factor, factor)}.{cat_key}",
        "confidence": cat.get("confidence", "medium"),
        "limitations": cat.get("limitations", "Rule-based mapping from configured profile."),
        "origin": "CALCULATED",
        "unknown": False,
        "requires_review": cat.get("requires_review", False),
    }


def _regulatory_factor(profile: dict, tokens: set[str]) -> dict:
    flags = profile.get("regulatory_flags", {})
    triggered = []
    min_score = 100.0
    requires_review = False
    for key, flag in flags.items():
        terms = set()
        for m in flag.get("match", []):
            terms |= token_set(m)
        if terms & tokens:
            triggered.append(key)
            min_score = min(min_score, float(flag.get("default_score", 50)))
            requires_review = requires_review or bool(flag.get("requires_review", False))
    if not triggered:
        return {
            "factor": "regulatory",
            "score": float(profile.get("regulatory_default_score", 80)),
            "rationale": "No regulatory flags triggered by the opportunity attributes.",
            "rule_source": "market_profile_ch.regulatory_default_score",
            "confidence": "medium",
            "limitations": "Absence of a flag is not legal clearance.",
            "origin": "CALCULATED",
            "unknown": False,
            "requires_review": False,
        }
    return {
        "factor": "regulatory",
        "score": min_score,
        "rationale": f"Triggered regulatory flags: {', '.join(triggered)}.",
        "rule_source": "market_profile_ch.regulatory_flags",
        "confidence": "medium",
        "limitations": "Public-rule proxy; confirm with compliance before testing.",
        "origin": "CALCULATED",
        "unknown": False,
        "requires_review": requires_review,
    }


def _price_factor(profile: dict, raws: list[RawSignal]) -> dict:
    prices = [float(r.price_value) for r in raws if r.price_value is not None]
    band = profile.get("price_fit", {})
    lo = band.get("acceptable_min")
    hi = band.get("acceptable_max")
    if not prices or lo is None or hi is None:
        return {
            "factor": "price_fit",
            "score": NEUTRAL_UNKNOWN,
            "rationale": "Insufficient observed price data to assess price fit.",
            "rule_source": "market_profile_ch.price_fit",
            "confidence": "low",
            "limitations": "Unknown — no price evidence; neutral default applied.",
            "origin": "CALCULATED",
            "unknown": True,
        }
    in_band = [p for p in prices if lo <= p <= hi]
    score = len(in_band) / len(prices) * 100
    return {
        "factor": "price_fit",
        "score": round(score, 2),
        "rationale": (
            f"{len(in_band)}/{len(prices)} observed prices fall within the Swiss "
            f"acceptable band {lo}-{hi} {band.get('currency', 'CHF')}."
        ),
        "rule_source": "market_profile_ch.price_fit",
        "confidence": "medium",
        "limitations": "Observed prices are global list prices, not Swiss retail prices.",
        "origin": "CALCULATED",
        "unknown": False,
    }


def assess_transferability(
    db: Session, *, opp: Opportunity, raws: list[RawSignal]
) -> TransferabilityAssessment:
    profile = load_market_profile()
    version = profile.get("version", "market-ch-1.0.0")
    tokens = _opp_tokens(opp)

    factors = {
        "climate": _resolve_factor("climate", profile, tokens),
        "geography": _resolve_factor("geography", profile, tokens),
        "customer_fit": _resolve_factor("customer_fit", profile, tokens),
        "regulatory": _regulatory_factor(profile, tokens),
        "price_fit": _price_factor(profile, raws),
        "seasonality": _resolve_factor("seasonality", profile, tokens),
    }

    overall = sum(WEIGHTS[k] * factors[k]["score"] for k in WEIGHTS)

    assessment = TransferabilityAssessment(
        opportunity_id=opp.id,
        climate_score=factors["climate"]["score"],
        geography_score=factors["geography"]["score"],
        customer_fit_score=factors["customer_fit"]["score"],
        regulatory_score=factors["regulatory"]["score"],
        price_fit_score=factors["price_fit"]["score"],
        seasonality_score=factors["seasonality"]["score"],
        overall_score=round(overall, 2),
        factor_details=factors,
        market_profile_version=version,
    )
    db.add(assessment)
    db.flush()
    return assessment
