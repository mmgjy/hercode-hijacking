"""URL security: allowlist + SSRF protection."""
import pytest

from app.errors import AppError
from app.security import is_allowed_url
from app.security.ssrf import assert_safe_url


def test_allowlist_accepts_configured_hosts():
    assert is_allowed_url("https://www.transa.ch/search")
    assert is_allowed_url("https://example.com/new-arrivals")


def test_allowlist_rejects_unconfigured_hosts():
    assert not is_allowed_url("https://evil.example.net/x")
    assert not is_allowed_url("https://internal.local/")


def test_ssrf_blocks_non_http_scheme():
    with pytest.raises(AppError):
        assert_safe_url("file:///etc/passwd")
    with pytest.raises(AppError):
        assert_safe_url("ftp://example.com/x")


def test_ssrf_blocks_private_ip_literal():
    with pytest.raises(AppError):
        assert_safe_url("http://127.0.0.1/")
    with pytest.raises(AppError):
        assert_safe_url("http://169.254.169.254/latest/meta-data/")
    with pytest.raises(AppError):
        assert_safe_url("http://10.0.0.5/")


def test_ssrf_allows_public_without_resolution():
    # resolve=False skips DNS but still enforces scheme/host shape.
    assert_safe_url("https://example.com/path", resolve=False)
