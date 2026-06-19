# Hijacking — Retail Opportunity Decision Engine (Backend)

Hijacking discovers repeated product patterns from a configured global
outdoor-retail source set, checks whether they are a **real Swiss assortment
gap**, and recommends an action: **TEST, CONTACT, RESEARCH, MONITOR, or REJECT**.

> Honest language: it reports the **strongest observed market** (not "where the
> trend began") and a **repeated recent pattern** (not unproven "growth %").

The frontend is built separately in Lovable; this repo is the backend + REST API.

---

## Product purpose

The user **never types an opportunity**. The system automatically: collects
global signals → extracts product info → normalizes & deduplicates → clusters
repeated patterns → generates opportunities → finds the strongest observed market
→ scans Swiss competitors → measures coverage → assesses Swiss transferability →
scores opportunity & confidence → recommends **TEST / CONTACT / RESEARCH /
MONITOR / REJECT**.

## Who does what

| Actor | Responsibilities |
| --- | --- |
| **System** | Everything automatic: collect, cluster, create opportunities + evidence, scan Swiss retailers, score matches, route uncertain ones to review, compute coverage/transferability/scores, recommend. |
| **User** | Start a run; optionally pick category/source set/period/keywords; review **uncertain** Swiss matches; recalculate. Does **not** create the opportunity. |
| **Admin/dev** | Configure sources, retailers, market profile, weights, dictionaries — all in `app/config_data/*.yaml`. |

## One focused capability

Discover repeated product patterns from a configured global source set, then
decide if they are a real Swiss assortment gap. **Not** built: general
web-search, open AI research, social/TikTok/Amazon scraping, forecasting,
inventory, supplier ordering, autonomous buying, chatbot.

---

## Architecture

```
backend/app/
  main.py / config.py / database.py / dependencies.py / jobs.py / errors.py
  api/          routers: health, source_sets, discovery_runs, opportunities,
                scan_items, exports, demo
  models/       ORM models (one file per table)
  schemas/      Pydantic v2 request/response models
  adapters/     jsonld, configurable_listing, global_retailer,
                global_corroborating_source, swiss_retailer
  services/     pipeline + scoring (see below)
  security/     SSRF guard, allowlist, rate limit
  config_data/  source_sets / retailers / market_profile_ch / normalization / scoring
  fixtures/     demo (structured) + global/swiss (replay HTML)
  tests/        offline, deterministic pytest suite
backend/  alembic/  Dockerfile  pyproject.toml  .env.example
```

### Pipeline (services)

```
source set → collection → extraction → normalization → deduplication →
clustering → opportunity → swiss_scan → product_matching → coverage →
transferability → scoring → recommendation → export
```

Every stage records status/timestamps/warnings/errors. A partial source failure
never kills the run, and **no data is fabricated** after an extraction failure.

### Why pure-Python ML

Clustering (TF-IDF + cosine + agglomerative) and fuzzy matching are pure Python
(stdlib `difflib`), so the pipeline is deterministic and installs with no native
ML wheels. scikit-learn / RapidFuzz / Playwright are optional drop-ins
(`pip install -e ".[ml]"`). No runtime LLM is required.

---

## Installation

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate   # 3.11–3.12
pip install -e ".[dev]"
cp .env.example .env
```

### Environment variables (`.env`)

| Var | Purpose |
| --- | --- |
| `APP_ENV`, `PORT`, `LOG_LEVEL` | runtime |
| `DATABASE_URL` | SQLite default; `postgresql+psycopg://…` for Postgres/Supabase |
| `SUPABASE_*`, `STORAGE_*` | snapshot storage (service-role key is **server-side only**) |
| `ALLOWED_ORIGINS` | CORS origins (`*` dev only) |
| `SCAN_*`, `PLAYWRIGHT_ENABLED` | outbound fetch safety |
| `API_KEY` | optional; when set, mutating endpoints require `X-API-Key` |

### Database migration

```bash
alembic upgrade head     # required for Postgres/Supabase; SQLite auto-creates on startup
```

### Run the API

```bash
uvicorn app.main:app --reload --port 8000     # docs: http://localhost:8000/docs
```

### Run the tests

```bash
pytest -q     # 62 tests, offline & deterministic
```

---

## Live, replay and demo modes

| Mode | Behaviour | Network |
| --- | --- | --- |
| **demo** | Seeded fixtures; full pipeline; supports review + recalculate. Use this for the frontend. | no |
| **replay** | Real adapters on stored HTML snapshots; deterministic. | no |
| **live** | Fetch the configured (allowlisted, SSRF-guarded) URLs; never substitutes demo data. | yes |

```bash
curl -XPOST localhost:8000/api/demo/reset                  # seed + run a demo
curl localhost:8000/api/discovery-runs                     # find the run id
curl localhost:8000/api/discovery-runs/<id>/opportunities
```

The demo shows **not every pattern becomes TEST** (well-covered "city-camping" →
MONITOR; an unreviewed pattern → CONTACT/RESEARCH → TEST after review).

---

## Adding a source

Add an entry under `global_sources:` in `app/config_data/source_sets.yaml`
(key, adapter, market, credibility, urls; `selectors:` for `configurable_listing`)
and a replay fixture at `app/fixtures/global/<key>.html`. Listing in the YAML also
allowlists the host. Prefer JSON-LD → listing → CSS → Playwright.

## Adding a Swiss retailer

Add to `app/config_data/retailers.yaml` (key, domain, `adapter: swiss_retailer`,
optional `selectors`/`scan_urls`), reference its key under a source set's
`swiss_retailers:`, and add `app/fixtures/swiss/<key>.html`. One generic Swiss
adapter handles all retailers.

## Tuning behaviour

- `scoring.yaml` — clustering, qualification, match, coverage, decision thresholds.
- `market_profile_ch.yaml` — transferability rules + Swiss search vocabulary.
- `normalization.yaml` — synonym dictionaries.

---

## Security

Allowlist (admin hosts only) · SSRF protection (private/loopback/link-local IPs
blocked) · http(s) only · redirect re-validation · timeouts · size limits ·
per-domain rate limiting · safe user-agent · no secrets in source control · no
service-role key in the frontend.

## Error codes

`INVALID_SOURCE_SET`, `SOURCE_NOT_ALLOWED`, `SOURCE_TIMEOUT`, `SOURCE_BLOCKED`,
`CAPTCHA_DETECTED`, `HTTP_ERROR`, `NO_SIGNALS_FOUND`, `EXTRACTION_FAILED`,
`NO_QUALIFYING_CLUSTERS`, `SWISS_SCAN_PARTIAL`, `NO_PRODUCTS_FOUND`,
`REVIEW_REQUIRED`, `RECOMMENDATION_INCOMPLETE`.

## API

Full endpoint reference in [API.md](API.md); live OpenAPI docs at `/docs`.

## Known limitations

- Source URLs are `example.com` placeholders; live mode needs real ones.
- Pure-Python clustering/matching: clear, not built for huge scale.
- Commercial feasibility is a public-data proxy (no margin/MOQ/conversion).
- Transferability is rule-based, not a compliance review.
- Background jobs are single-process (FastAPI BackgroundTasks).
