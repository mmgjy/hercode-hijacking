"""Shared test fixtures.

Tests run against an isolated temporary SQLite database and never touch the
network. The DATABASE_URL is set before any app module is imported so the
module-level engine binds to the temp DB.
"""
from __future__ import annotations

import os
import tempfile

# Must be set before importing app.* (engine binds at import time).
_TMP_DB = os.path.join(tempfile.gettempdir(), "hijacking_test.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ["API_KEY"] = ""

import pytest  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.database import SessionLocal, create_all  # noqa: E402
from app.models import (  # noqa: E402
    CoverageSnapshot,
    DiscoveryRun,
    NormalizedSignal,
    Opportunity,
    OpportunitySignal,
    RawSignal,
    Recommendation,
    Retailer,
    RetailerScan,
    ScanItem,
    SourceDocument,
    TransferabilityAssessment,
)

_MODELS = [
    Recommendation,
    TransferabilityAssessment,
    CoverageSnapshot,
    ScanItem,
    RetailerScan,
    Retailer,
    OpportunitySignal,
    Opportunity,
    NormalizedSignal,
    RawSignal,
    SourceDocument,
    DiscoveryRun,
]


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    create_all()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    for model in _MODELS:
        session.execute(delete(model))
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def make_run(db, mode="demo", **kwargs):
    defaults = dict(
        category="outdoor retail",
        target_market="Switzerland",
        source_set="outdoor_global_default",
        lookback_days=90,
        maximum_opportunities=5,
        focus_keywords=[],
        mode=mode,
        status="pending",
    )
    defaults.update(kwargs)
    run = DiscoveryRun(**defaults)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
