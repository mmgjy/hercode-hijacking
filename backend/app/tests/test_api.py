"""End-to-end API tests against the frontend contract (camelCase).

Background tasks run synchronously under TestClient.
"""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_source_sets_and_sources(client):
    sets = client.get("/api/source-sets").json()
    assert any(s["id"] == "outdoor_global_default" for s in sets)
    assert "sourceCount" in sets[0] and "scope" in sets[0]
    sources = client.get("/api/sources").json()
    assert sources and {"id", "scope", "geography"} <= set(sources[0])


def test_full_flow_demo(client):
    r = client.post(
        "/api/discovery-runs",
        json={
            "category": "outdoor retail",
            "targetMarket": "Switzerland",
            "sourceSetId": "outdoor_global_default",
            "observationPeriod": "90",
            "maxOpportunities": 5,
            "focusKeywords": "tick, upf",
        },
    )
    assert r.status_code == 202
    run_id = r.json()["id"]

    run = client.get(f"/api/discovery-runs/{run_id}").json()
    assert run["status"] == "complete"
    assert run["rawSignals"] >= 3
    assert run["clusters"] >= 3
    assert {s["status"] for s in run["stages"]} <= {"complete", "partial"}

    opps = client.get(f"/api/discovery-runs/{run_id}/opportunities").json()
    assert len(opps) >= 3
    opp = opps[0]
    assert opp["rank"] == 1
    assert opp["action"] in ("TEST", "CONTACT", "RESEARCH", "MONITOR", "REJECT")
    assert opp["origin"] == "DEMO"
    oid = opp["id"]

    detail = client.get(f"/api/opportunities/{oid}").json()
    assert detail["scoreBreakdown"] and detail["transferability"]
    assert "recommendation" in detail and "rationale" in detail

    ev = client.get(f"/api/opportunities/{oid}/evidence").json()
    assert ev and ev[0]["url"]

    assert isinstance(client.get(f"/api/opportunities/{oid}/coverage").json(), list)
    assert isinstance(client.get(f"/api/opportunities/{oid}/scan-items").json(), list)

    rec = client.get(f"/api/opportunities/{oid}/recommendation").json()
    assert rec["action"] in ("TEST", "CONTACT", "RESEARCH", "MONITOR", "REJECT")
    assert rec["complete"] is True

    # latest + map
    assert len(client.get("/api/discovery-runs/latest/opportunities").json()) >= 3
    m = client.get("/api/opportunity-map").json()
    assert m["opportunities"] and m["markets"]

    # exports
    assert client.get(f"/api/opportunities/{oid}/export.json").status_code == 200
    assert client.get(f"/api/opportunities/{oid}/export.csv").status_code == 200


def test_review_then_recalculate(client):
    client.post("/api/demo/reset")
    opps = client.get("/api/discovery-runs/latest/opportunities").json()

    pending_item = None
    target_id = None
    for opp in opps:
        items = client.get(f"/api/opportunities/{opp['id']}/scan-items").json()
        pend = [i for i in items if i["reviewStatus"] == "pending"]
        if pend:
            pending_item, target_id = pend[0], opp["id"]
            break
    assert pending_item, "demo should produce at least one pending review item"

    rr = client.post(
        f"/api/scan-items/{pending_item['id']}/review",
        json={"status": "rejected", "note": "not a true match"},
    )
    assert rr.status_code == 200 and rr.json()["ok"] is True

    rc = client.post(f"/api/opportunities/{target_id}/recalculate")
    assert rc.status_code == 200
    assert rc.json()["action"] in ("TEST", "CONTACT", "RESEARCH", "MONITOR", "REJECT")


def test_review_rejects_invalid_status(client):
    client.post("/api/demo/reset")
    opps = client.get("/api/discovery-runs/latest/opportunities").json()
    for opp in opps:
        items = client.get(f"/api/opportunities/{opp['id']}/scan-items").json()
        if items:
            r = client.post(
                f"/api/scan-items/{items[0]['id']}/review",
                json={"status": "auto_approved"},  # not allowed via review
            )
            assert r.status_code == 422
            return
