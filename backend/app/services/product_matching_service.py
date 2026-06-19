"""Deterministic product matching between Swiss scan items and an opportunity.

Score components (configurable in ``scoring.yaml``):
    product-type match 35%, defining feature 30%, material 15%,
    usage/customer 10%, keyword overlap 10%.

Review routing (configurable):
    >= auto_approve_min -> auto_approved (unless a critical feature is missing)
    >= review_min       -> pending (human review)
    below               -> rejected
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import load_scoring
from app.models import Opportunity, ScanItem
from app.services.text_utils import jaccard, token_set


@dataclass
class MatchResult:
    score: float
    matched_terms: list[str]
    missing_terms: list[str]
    explanation: str
    review_status: str


def _coverage(target: set[str], text: set[str]) -> tuple[float, list[str], list[str]]:
    if not target:
        return 1.0, [], []
    matched = sorted(t for t in target if t in text)
    missing = sorted(t for t in target if t not in text)
    return len(matched) / len(target), matched, missing


def match_item(opp: Opportunity, item: ScanItem) -> MatchResult:
    cfg = load_scoring().get("matching", {})
    weights = cfg.get(
        "weights",
        {
            "product_type": 0.35,
            "feature": 0.30,
            "material": 0.15,
            "usage_customer": 0.10,
            "keyword": 0.10,
        },
    )
    auto_min = float(cfg.get("auto_approve_min", 85))
    review_min = float(cfg.get("review_min", 55))

    item_text = token_set(
        " ".join(
            filter(
                None,
                [item.title, item.brand, " ".join(item.features or [])],
            )
        )
    )

    pt_target = token_set(opp.dominant_product_type)
    feat_target = token_set(" ".join(opp.dominant_features or []))
    mat_target = token_set(" ".join(opp.dominant_materials or []))
    uc_target = token_set(" ".join(filter(None, [opp.customer_segment, opp.usage_occasion])))
    kw_target = token_set(" ".join(t["term"] for t in (opp.search_terms or [])))

    pt_cov, pt_m, pt_miss = _coverage(pt_target, item_text)
    feat_cov, feat_m, feat_miss = _coverage(feat_target, item_text)
    mat_cov, mat_m, _ = _coverage(mat_target, item_text)
    uc_cov, uc_m, _ = _coverage(uc_target, item_text)
    kw_cov = jaccard(kw_target, item_text)

    score = 100 * (
        weights["product_type"] * pt_cov
        + weights["feature"] * feat_cov
        + weights["material"] * mat_cov
        + weights["usage_customer"] * uc_cov
        + weights["keyword"] * kw_cov
    )
    score = round(score, 2)

    matched_terms = sorted(set(pt_m + feat_m + mat_m + uc_m))
    missing_terms = sorted(set(pt_miss + feat_miss))

    # Critical defining feature missing blocks auto-approval.
    critical_missing = bool(feat_target) and feat_cov < 1.0

    if score >= auto_min and not critical_missing:
        status = "auto_approved"
    elif score >= review_min:
        status = "pending"
    else:
        status = "rejected"

    explanation = (
        f"product_type={pt_cov:.0%}, feature={feat_cov:.0%}, material={mat_cov:.0%}, "
        f"usage/customer={uc_cov:.0%}, keyword={kw_cov:.0%}."
    )
    if critical_missing and score >= auto_min:
        explanation += " Held for review: a defining feature is unmatched."

    return MatchResult(
        score=score,
        matched_terms=matched_terms,
        missing_terms=missing_terms,
        explanation=explanation,
        review_status=status,
    )


def apply_match(opp: Opportunity, item: ScanItem) -> ScanItem:
    result = match_item(opp, item)
    item.match_score = result.score
    item.matched_terms = result.matched_terms
    item.missing_terms = result.missing_terms
    item.match_explanation = result.explanation
    item.review_status = result.review_status
    item.origin = item.origin or "AUTO_DISCOVERED"
    return item
