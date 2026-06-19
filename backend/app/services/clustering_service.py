"""Deterministic, inspectable clustering of normalized signals.

Method:
1. Build a text document per signal from normalized product type, features,
   materials, customer segment and usage occasion.
2. Vectorize with TF-IDF.
3. Link signals whose cosine similarity >= threshold AND that share a
   rule-based safeguard (same product-type family or a shared defining
   feature/material) so unrelated broad categories never merge.
4. Single-linkage agglomerative clustering via union-find.
5. Persist the terms that caused each signal to join its cluster.

No LLM is required. An optional LLM may only produce a readable name/summary
later — it never creates signals or changes scores.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config import load_scoring
from app.models import NormalizedSignal
from app.services.text_utils import (
    TfidfVectorizer,
    cosine_sparse,
    shared_terms,
    token_set,
)

CLUSTERING_VERSION = "cluster-1.0.0"


@dataclass
class ClusterMember:
    signal: NormalizedSignal
    similarity: float
    terms: list[str]


@dataclass
class Cluster:
    members: list[ClusterMember] = field(default_factory=list)

    @property
    def signals(self) -> list[NormalizedSignal]:
        return [m.signal for m in self.members]


def _signal_text(s: NormalizedSignal) -> str:
    parts = [
        s.normalized_product_type or "",
        " ".join(s.normalized_features or []),
        " ".join(s.normalized_materials or []),
        s.normalized_customer_segment or "",
        s.normalized_usage_occasion or "",
    ]
    return " ".join(p for p in parts if p).strip()


def _defining_tokens(s: NormalizedSignal) -> set[str]:
    toks: set[str] = set()
    for f in s.normalized_features or []:
        toks |= token_set(f)
    for m in s.normalized_materials or []:
        toks |= token_set(m)
    return toks


def _product_type_family(s: NormalizedSignal) -> set[str]:
    return token_set(s.normalized_product_type)


def cluster_signals(signals: list[NormalizedSignal]) -> list[Cluster]:
    cfg = load_scoring().get("clustering", {})
    threshold = float(cfg.get("similarity_threshold", 0.18))
    # A shared defining feature/material may bridge differing product types, but
    # only when similarity is clearly high — otherwise a single generic token
    # (e.g. "protection") could merge unrelated categories.
    bridge_threshold = float(cfg.get("feature_bridge_threshold", 0.45))

    usable = [s for s in signals if _signal_text(s)]
    if not usable:
        return []

    docs = [_signal_text(s) for s in usable]
    vec = TfidfVectorizer()
    vectors = vec.fit_transform(docs)

    n = len(usable)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    fams = [_product_type_family(s) for s in usable]
    defs = [_defining_tokens(s) for s in usable]

    for i in range(n):
        for j in range(i + 1, n):
            sim = cosine_sparse(vectors[i], vectors[j])
            if sim < threshold:
                continue
            # Safeguard: same product-type family always allowed to merge; a
            # shared defining feature/material only bridges differing product
            # types when similarity is clearly high.
            same_family = bool(fams[i] & fams[j])
            shared_defining = bool(defs[i] & defs[j])
            if same_family or (shared_defining and sim >= bridge_threshold):
                union(i, j)

    grouped: dict[int, list[int]] = {}
    for i in range(n):
        grouped.setdefault(find(i), []).append(i)

    clusters: list[Cluster] = []
    for members_idx in grouped.values():
        # centroid = densest member's vector (first by index for determinism)
        anchor = members_idx[0]
        cluster = Cluster()
        for idx in members_idx:
            sim = cosine_sparse(vectors[idx], vectors[anchor]) if idx != anchor else 1.0
            terms = shared_terms(vectors[idx], vectors[anchor], vec.vocab)
            if not terms:
                terms = sorted(_defining_tokens(usable[idx]) | _product_type_family(usable[idx]))[:6]
            cluster.members.append(
                ClusterMember(signal=usable[idx], similarity=round(sim, 4), terms=terms)
            )
        clusters.append(cluster)
    # Deterministic ordering: largest clusters first
    clusters.sort(key=lambda c: (-len(c.members), c.members[0].signal.id))
    return clusters
