"""Deduplication and independence groups."""
from app.models import RawSignal
from app.services.deduplication_service import assign_independence_groups


def _mk(db, run_id, **kw):
    rs = RawSignal(discovery_run_id=run_id, features=[], materials=[], **kw)
    db.add(rs)
    return rs


def test_same_content_hash_grouped(db):
    from app.tests.conftest import make_run

    run = make_run(db)
    a = _mk(db, run.id, source_url="https://a.com/x", content_hash="H1", raw_title="Tick trousers", brand="X")
    b = _mk(db, run.id, source_url="https://b.com/y", content_hash="H1", raw_title="Tick trousers", brand="X")
    c = _mk(db, run.id, source_url="https://c.com/z", content_hash="H2", raw_title="Different", brand="Y")
    db.commit()
    groups = assign_independence_groups(db, [a, b, c])
    assert a.independence_group == b.independence_group  # syndicated duplicate
    assert a.independence_group != c.independence_group
    assert groups == 2


def test_fuzzy_title_same_brand_grouped(db):
    from app.tests.conftest import make_run

    run = make_run(db)
    a = _mk(db, run.id, source_url="https://a.com/1", raw_title="Insect Protection Hiking Trousers", brand="Craghoppers")
    b = _mk(db, run.id, source_url="https://b.com/2", raw_title="Insect Protection Hiking Trouser", brand="Craghoppers")
    db.commit()
    assign_independence_groups(db, [a, b])
    assert a.independence_group == b.independence_group
