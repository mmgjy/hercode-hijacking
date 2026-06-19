"""Deduplicate signals and assign independence groups.

Duplicate evidence must not count as independent confirmation. We union signals
that are likely derived from the same original (same content hash, same product
URL, or same brand + highly similar title) into an ``independence_group``. The
qualification step then caps how much any single group can contribute.
"""
from __future__ import annotations

from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import RawSignal
from app.services.text_utils import fuzzy_ratio

FUZZY_TITLE_THRESHOLD = 0.9


def _canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    p = urlparse(url)
    return f"{p.netloc}{p.path}".lower().rstrip("/") or None


def assign_independence_groups(db: Session, raw_signals: list[RawSignal]) -> int:
    n = len(raw_signals)
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

    canon = [_canonical_url(s.source_url) for s in raw_signals]
    titles = [(s.raw_title or s.product_name or "") for s in raw_signals]
    brands = [(s.brand or "").lower().strip() for s in raw_signals]

    for i in range(n):
        for j in range(i + 1, n):
            si, sj = raw_signals[i], raw_signals[j]
            same = False
            if si.content_hash and si.content_hash == sj.content_hash:
                same = True
            elif canon[i] and canon[i] == canon[j]:
                same = True
            elif (
                brands[i]
                and brands[i] == brands[j]
                and fuzzy_ratio(titles[i], titles[j]) >= FUZZY_TITLE_THRESHOLD
            ):
                same = True
            if same:
                union(i, j)

    groups: dict[int, str] = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = f"grp-{len(groups) + 1}"
        raw_signals[i].independence_group = groups[root]
    db.flush()
    return len(groups)
