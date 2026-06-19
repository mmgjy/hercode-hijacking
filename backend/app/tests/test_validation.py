"""Discovery-request validation."""
import pytest
from pydantic import ValidationError

from app.schemas import DiscoveryRunCreate


def test_defaults():
    req = DiscoveryRunCreate()
    assert req.mode.value == "demo"
    assert req.lookback_days == 90
    assert req.target_market == "Switzerland"


def test_focus_keywords_are_stripped():
    req = DiscoveryRunCreate(focus_keywords=["  tick ", "", "  "])
    assert req.focus_keywords == ["tick"]


def test_invalid_mode_rejected():
    with pytest.raises(ValidationError):
        DiscoveryRunCreate(mode="banana")


def test_lookback_bounds():
    with pytest.raises(ValidationError):
        DiscoveryRunCreate(lookback_days=0)
    with pytest.raises(ValidationError):
        DiscoveryRunCreate(maximum_opportunities=0)


def test_create_run_rejects_unknown_source_set(client):
    resp = client.post("/api/discovery-runs", json={"source_set": "nope", "mode": "demo"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_SOURCE_SET"
