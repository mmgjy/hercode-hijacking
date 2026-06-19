"""End-to-end API tests via TestClient (background tasks run synchronously)."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_source_sets(client):
    r = client.get("/api/source-sets")
    assert r.status_code == 200
    sets = r.json()
    assert any(s["key"] == "outdoor_global_default" for s in sets)
    # Raw URLs are not leaked; counts are exposed instead.
    s = sets[0]
    assert "url_count" in s["global_sources"][0]


def test_full_flow_demo(client):
    # Start a demo discovery run; TestClient runs the background task to completion.
    r = client.post("/api/discovery-runs", json={"mode": "demo"})
    assert r.status_code == 202
    run_id = r.json()["id"]

    run = client.get(f"/api/discovery-runs/{run_id}").json()
    assert run["status"] == "completed"
    assert run["opportunity_count"] >= 3

    signals = client.get(f"/api/discovery-runs/{run_id}/signals").json()
    assert len(signals) >= 3

    opps = client.get(f"/api/discovery-runs/{run_id}/opportunities").json()
    assert opps
    opp = opps[0]
    oid = opp["id"]
    assert opp["origin"] == "AUTO_DISCOVERED"

    # Evidence links back to source signals.
    ev = client.get(f"/api/opportunities/{oid}/evidence").json()
    assert ev["evidence"]
    assert ev["evidence"][0]["source_url"]

    # Coverage + transferability + recommendation present.
    assert client.get(f"/api/opportunities/{oid}/coverage").status_code == 200
    assert client.get(f"/api/opportunities/{oid}/transferability").status_code == 200
    rec = client.get(f"/api/opportunities/{oid}/recommendation").json()
    assert rec["action"] in ("TEST", "CONTACT", "RESEARCH", "MONITOR", "REJECT")
    assert rec["scoring_version"]

    # Exports
    assert client.get(f"/api/opportunities/{oid}/export.json").status_code == 200
    csv_resp = client.get(f"/api/opportunities/{oid}/export.csv")
    assert csv_resp.status_code == 200
    assert "opportunity_id" in csv_resp.text


def test_review_then_recalculate(client):
    client.post("/api/demo/reset")
    # Find an opportunity with a pending scan item.
    runs = client.get("/api/discovery-runs").json()
    run_id = runs[0]["id"]
    opps = client.get(f"/api/discovery-runs/{run_id}/opportunities").json()

    target = None
    pending_item = None
    for opp in opps:
        items = client.get(
            f"/api/opportunities/{opp['id']}/scan-items", params={"review_status": "pending"}
        ).json()
        if items:
            target = opp
            pending_item = items[0]
            break
    assert pending_item, "demo should produce at least one pending review item"

    # Reject the uncertain match.
    rr = client.post(
        f"/api/scan-items/{pending_item['id']}/review",
        json={"review_status": "rejected", "review_notes": "not a true match"},
    )
    assert rr.status_code == 200
    assert rr.json()["review_status"] == "rejected"
    assert rr.json()["origin"] == "MANUAL_REVIEW"

    # Recalculate the recommendation after review.
    rc = client.post(f"/api/opportunities/{target['id']}/recalculate")
    assert rc.status_code == 200
    assert rc.json()["action"] in ("TEST", "CONTACT", "RESEARCH", "MONITOR", "REJECT")


def test_review_rejects_invalid_status(client):
    client.post("/api/demo/reset")
    runs = client.get("/api/discovery-runs").json()
    opps = client.get(f"/api/discovery-runs/{runs[0]['id']}/opportunities").json()
    items = client.get(f"/api/opportunities/{opps[0]['id']}/scan-items").json()
    if not items:
        return
    r = client.post(
        f"/api/scan-items/{items[0]['id']}/review",
        json={"review_status": "auto_approved"},  # not allowed via review
    )
    assert r.status_code == 422
