# Hijacking API Reference

Base URL: `http://localhost:8000`. Interactive docs: `/docs` (Swagger) and
`/redoc`. All responses are JSON unless noted. Mutating endpoints
(`POST`) require `X-API-Key` **only when** `API_KEY` is set in the environment.

## Provenance

Many fields carry a `provenance`/`origin` marker so the frontend can show how a
result was produced: `LIVE`, `DEMO`, `REPLAY`, `CALCULATED`, `AUTO_DISCOVERED`,
`MANUAL_REVIEW`, `INTERNAL`.

## Error shape

```json
{ "error": { "code": "INVALID_SOURCE_SET", "message": "…", "details": {} } }
```

---

## Health

### `GET /health`
Returns service status, version, environment and whether Playwright is enabled.

## Source sets

### `GET /api/source-sets`
Lists configured source sets with global-source keys/adapters/credibility and
Swiss retailer keys. Raw source URLs are not leaked (only `url_count`).

## Discovery runs

### `POST /api/discovery-runs`  → `202`
Starts a background discovery run and returns its id. The user does **not**
provide an opportunity name.

```json
{
  "category": "outdoor retail",
  "target_market": "Switzerland",
  "source_set": "outdoor_global_default",
  "lookback_days": 90,
  "maximum_opportunities": 5,
  "focus_keywords": [],
  "mode": "demo"            // live | replay | demo
}
```
Response: `{ "id", "status", "mode", "message" }`.

### `GET /api/discovery-runs`
List recent runs (status, stage, counts, warnings, errors, timestamps).

### `GET /api/discovery-runs/{run_id}`
Single run with stage/status/warnings/error and signal/opportunity counts.

### `GET /api/discovery-runs/{run_id}/signals`
Raw signals collected for the run (includes `independence_group`, `origin`).

### `GET /api/discovery-runs/{run_id}/opportunities`
Auto-discovered opportunities for the run.

## Opportunities

### `GET /api/opportunities/{id}`
Opportunity detail incl. strongest/earliest observed market, dominant
type/features/materials, Swiss search terms, counts, plus
`has_recommendation`, `has_coverage`, `pending_review_count`.

### `GET /api/opportunities/{id}/evidence`
Linked evidence: each normalized signal → raw signal with source name/URL/type,
market, observed date, brand, independence group, cluster similarity & terms.

### `GET /api/opportunities/{id}/coverage`
Latest Swiss coverage snapshot (component scores, `coverage_score`,
`gap_score`). Uses **approved matches only**.

### `GET /api/opportunities/{id}/transferability`
Latest transferability assessment: factor scores plus `factor_details` with
rationale, rule source, confidence, limitations and `origin=CALCULATED` per
factor (unknown factors are marked, not invented).

### `GET /api/opportunities/{id}/recommendation`
Latest recommendation: action, triggered rule, rationale, all component scores,
supporting evidence ids, counter-signal ids, risks, missing evidence,
experiment plan (TEST only), scoring version.

### `GET /api/opportunities/{id}/scan-items?review_status=pending`
Swiss scan items with match score, matched/missing terms, explanation and
review status (`auto_approved` | `pending` | `approved` | `rejected`).

### `POST /api/opportunities/{id}/recalculate`
Recompute coverage, transferability, scores and the recommendation (e.g. after
reviewing uncertain matches). Returns the new recommendation.

## Match review

### `POST /api/scan-items/{scan_item_id}/review`
```json
{ "review_status": "approved", "review_notes": "Explicit insect-protection hiking trousers." }
```
Only `approved` or `rejected` are accepted. Sets `origin=MANUAL_REVIEW`.

## Export

### `GET /api/opportunities/{id}/export.json`
Full opportunity bundle: attributes, recommendation, coverage, transferability,
evidence and Swiss scan items.

### `GET /api/opportunities/{id}/export.csv`
One-row summary with markets, action, all scores and counts.

## Demo

### `POST /api/demo/reset`
Wipes all data and runs a fresh deterministic demo discovery synchronously.
Returns the new `discovery_run_id`, `run_status` and `opportunity_count`.

---

## Typical flow

```bash
# 1. start a run
curl -XPOST localhost:8000/api/discovery-runs -H 'content-type: application/json' \
  -d '{"mode":"demo"}'
# 2. inspect opportunities
curl localhost:8000/api/discovery-runs/<run_id>/opportunities
# 3. inspect a recommendation + evidence
curl localhost:8000/api/opportunities/<opp_id>/recommendation
curl localhost:8000/api/opportunities/<opp_id>/evidence
# 4. review an uncertain Swiss match, then recalculate
curl -XPOST localhost:8000/api/scan-items/<item_id>/review \
  -H 'content-type: application/json' -d '{"review_status":"rejected"}'
curl -XPOST localhost:8000/api/opportunities/<opp_id>/recalculate
```
