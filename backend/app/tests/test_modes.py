"""Demo reset, replay determinism, and live-failure handling (offline)."""
from app.jobs import run_now
from app.models import DiscoveryRun, Opportunity
from app.services.collection_service import Collector
from app.tests.conftest import make_run


def _run_and_names(db, mode):
    run = make_run(db, mode=mode)
    run_now(run.id)
    db.expire_all()
    opps = (
        db.query(Opportunity)
        .filter(Opportunity.discovery_run_id == run.id)
        .order_by(Opportunity.name)
        .all()
    )
    return db.get(DiscoveryRun, run.id), [o.name for o in opps]


def test_demo_run_produces_multiple_opportunities(db):
    run, names = _run_and_names(db, "demo")
    assert run.status == "completed"
    assert len(names) >= 3


def test_replay_is_deterministic(db):
    run1, names1 = _run_and_names(db, "replay")
    run2, names2 = _run_and_names(db, "replay")
    assert run1.status == "completed"
    assert names1 == names2
    assert len(names1) >= 1


def test_demo_reset_endpoint(client):
    r1 = client.post("/api/demo/reset")
    assert r1.status_code == 200
    body = r1.json()
    assert body["ok"] is True
    run_id = body["discoveryRunId"]
    opps = client.get(f"/api/discovery-runs/{run_id}/opportunities").json()
    assert len(opps) >= 3
    # Idempotent: a second reset wipes and rebuilds cleanly.
    assert client.post("/api/demo/reset").status_code == 200


def test_live_failure_does_not_fabricate(db):
    """A disallowed live URL is recorded as failed; no signals fabricated."""
    run = make_run(db, mode="live")
    collector = Collector("live")
    result = collector.collect(
        db,
        discovery_run_id=run.id,
        source_key="bad",
        url="https://not-in-allowlist.example.net/x",
        source_type="web",
        market="US",
    )
    assert result.document is None
    assert result.source_document.collection_status == "failed"
    assert result.source_document.error_code == "SOURCE_NOT_ALLOWED"


def test_replay_missing_fixture_records_error(db):
    run = make_run(db, mode="replay")
    collector = Collector("replay")
    result = collector.collect(
        db,
        discovery_run_id=run.id,
        source_key="does_not_exist",
        url="https://example.com/x",
        source_type="web",
        market="US",
    )
    assert result.document is None
    assert result.source_document.collection_status == "failed"
