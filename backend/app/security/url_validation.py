"""Allowlist enforcement.

We never crawl arbitrary user-provided domains. Only hosts present in the
configured source sets and retailer definitions are fetchable.
"""
from __future__ import annotations

from urllib.parse import urlparse

from app.config import load_retailers, load_source_sets


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().lstrip("www.")


def allowed_hosts() -> set[str]:
    hosts: set[str] = set()
    for sset in load_source_sets().values():
        for src in sset.get("global_sources", []):
            for url in src.get("urls", []):
                hosts.add(_host(url))
    for retailer in load_retailers().values():
        domain = (retailer.get("domain") or "").lower().lstrip("www.")
        if domain:
            hosts.add(domain)
        for url in retailer.get("scan_urls", []):
            hosts.add(_host(url))
    hosts.discard("")
    return hosts


def is_allowed_url(url: str) -> bool:
    host = _host(url)
    if not host:
        return False
    allow = allowed_hosts()
    return any(host == h or host.endswith("." + h) for h in allow)
