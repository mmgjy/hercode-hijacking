"""SSRF protection helpers.

The collector only ever fetches administrator-configured URLs, but we still
defend in depth: enforce http(s) only, resolve the host, and reject any address
that maps to a private / loopback / link-local / reserved range. Redirects must
be re-validated by the caller before following.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.errors import AppError, ErrorCode

ALLOWED_SCHEMES = {"http", "https"}


def is_public_host(host: str) -> bool:
    """Return True only if every resolved address for ``host`` is public."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def assert_safe_url(url: str, *, resolve: bool = True) -> None:
    """Raise AppError if ``url`` is unsafe to fetch.

    ``resolve=False`` skips DNS resolution (useful in offline tests); scheme and
    host-shape checks still apply.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise AppError(
            ErrorCode.SOURCE_NOT_ALLOWED,
            f"Scheme '{parsed.scheme}' is not allowed; only http/https.",
        )
    if not parsed.hostname:
        raise AppError(ErrorCode.SOURCE_NOT_ALLOWED, "URL has no host.")
    # Reject explicit IP literals that are private.
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if not ip.is_global:
            raise AppError(
                ErrorCode.SOURCE_BLOCKED,
                "URL points at a non-public IP address.",
            )
        return
    except ValueError:
        pass  # not a literal IP; resolve below
    if resolve and not is_public_host(parsed.hostname):
        raise AppError(
            ErrorCode.SOURCE_BLOCKED,
            f"Host '{parsed.hostname}' resolves to a non-public address.",
        )
