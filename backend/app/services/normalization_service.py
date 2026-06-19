"""Normalize raw signal fields using configurable dictionaries.

Keeps both raw and normalized values. Normalization covers casing, punctuation,
singular/plural, and synonym mapping for product types, materials, features,
customer segments, usage occasions, currencies and brand spelling. Dictionaries
live in ``config_data/normalization.yaml``.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.config import load_normalization
from app.models import NormalizedSignal, RawSignal

NORMALIZATION_VERSION = "norm-1.0.0"

_PUNCT_RE = re.compile(r"[^\w\s-]")
_WS_RE = re.compile(r"\s+")


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    text = text.lower().strip()
    text = _PUNCT_RE.sub(" ", text)
    text = text.replace("-", " ")
    text = _WS_RE.sub(" ", text).strip()
    return text or None


def _singularize_token(tok: str) -> str:
    if len(tok) > 4 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 3 and tok.endswith("ses"):
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def _singularize(text: str | None) -> str | None:
    if not text:
        return None
    return " ".join(_singularize_token(t) for t in text.split())


class Normalizer:
    def __init__(self) -> None:
        cfg = load_normalization()
        self.product_types = self._build_map(cfg.get("product_types", {}))
        self.materials = self._build_map(cfg.get("materials", {}))
        self.features = self._build_map(cfg.get("features", {}))
        self.customer_segments = self._build_map(cfg.get("customer_segments", {}))
        self.usage_occasions = self._build_map(cfg.get("usage_occasions", {}))
        self.currencies = {
            k.upper(): v for k, v in cfg.get("currencies", {}).items()
        }
        self.brands = self._build_map(cfg.get("brands", {}))

    @staticmethod
    def _build_map(mapping: dict) -> dict[str, str]:
        """canonical -> [synonyms] becomes synonym(normalized) -> canonical."""
        out: dict[str, str] = {}
        for canonical, synonyms in mapping.items():
            norm_canon = _singularize(_clean(canonical)) or canonical
            out[norm_canon] = canonical
            for syn in synonyms or []:
                key = _singularize(_clean(syn))
                if key:
                    out[key] = canonical
        return out

    def _map_value(self, value: str | None, table: dict[str, str]) -> tuple[str | None, str | None]:
        """Return (normalized_value, matched_synonym_or_None)."""
        cleaned = _singularize(_clean(value))
        if not cleaned:
            return None, None
        if cleaned in table:
            return table[cleaned], cleaned
        # substring match against known canonical phrases
        for key, canon in table.items():
            if key and key in cleaned:
                return canon, key
        return cleaned, None  # cleaned but unmapped

    def _map_list(self, values, table) -> tuple[list[str], list[str]]:
        normalized: list[str] = []
        matched: list[str] = []
        for v in values or []:
            norm, hit = self._map_value(v, table)
            if norm and norm not in normalized:
                normalized.append(norm)
            if hit:
                matched.append(hit)
        return normalized, matched

    def normalize(self, raw: RawSignal) -> NormalizedSignal:
        terms: dict[str, list[str]] = {}
        pt, pt_hit = self._map_value(raw.product_type or raw.raw_title, self.product_types)
        if pt_hit:
            terms.setdefault("product_type", []).append(pt_hit)
        feats, feat_hits = self._map_list(
            self._derive_features(raw), self.features
        )
        if feat_hits:
            terms["features"] = feat_hits
        mats, mat_hits = self._map_list(raw.materials, self.materials)
        if mat_hits:
            terms["materials"] = mat_hits
        cust, cust_hit = self._map_value(raw.target_customer, self.customer_segments)
        if cust_hit:
            terms.setdefault("customer", []).append(cust_hit)
        usage, usage_hit = self._map_value(raw.usage_occasion, self.usage_occasions)
        if usage_hit:
            terms.setdefault("usage", []).append(usage_hit)
        brand, brand_hit = self._map_value(raw.brand, self.brands)
        if brand_hit:
            terms.setdefault("brand", []).append(brand_hit)

        return NormalizedSignal(
            raw_signal_id=raw.id,
            discovery_run_id=raw.discovery_run_id,
            normalized_product_type=pt,
            normalized_features=feats,
            normalized_materials=mats,
            normalized_customer_segment=cust,
            normalized_usage_occasion=usage,
            normalized_brand=brand or (_clean(raw.brand)),
            normalization_terms=terms,
            normalization_version=NORMALIZATION_VERSION,
        )

    def _derive_features(self, raw: RawSignal) -> list[str]:
        """Pull candidate feature phrases from explicit features + title/desc."""
        feats = list(raw.features or [])
        text = " ".join(filter(None, [raw.raw_title, raw.raw_description]))
        cleaned = _singularize(_clean(text)) or ""
        for key in self.features:
            if key and key in cleaned:
                feats.append(key)
        return feats


def normalize_run(db: Session, raw_signals: list[RawSignal]) -> list[NormalizedSignal]:
    normalizer = Normalizer()
    out: list[NormalizedSignal] = []
    for raw in raw_signals:
        ns = normalizer.normalize(raw)
        db.add(ns)
        out.append(ns)
    db.flush()
    return out
