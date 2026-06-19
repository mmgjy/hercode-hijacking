# Submission — Hijacking (Retail Opportunity Decision Engine)

## Team

- Team name: Hijacking
- Team members: Sumaya Mohat, Meryem Ghrairi, Maria Kinga Zielinska
- GitHub fork URL: https://github.com/mmgjy/hercode-hijacking.git
- Demo URL, if any: https://lovable.dev/preview/HpO7TmTIL6VR5KqQyDQuJLN1Zz7hKEI6
- Video walkthrough URL, if any: _optional_

## Challenge problem

Retail buying teams are flooded with weak signals and need one clear answer:
*what should we do next?* For a Swiss outdoor retailer, the question is whether
an emerging product / material / feature pattern seen in other markets is a real,
under-served **Swiss assortment gap** worth acting on — and what the action is.

## One focused capability

**Automatically discover repeated product patterns from a configured global
outdoor-retail source set during a selected observation period, then determine
whether those patterns represent a real Swiss assortment gap — and recommend
TEST, CONTACT, RESEARCH, MONITOR, or REJECT.**

The user never enters an opportunity hypothesis; the system discovers it. The
same flow is reusable for another category/market by changing configuration
(source sets, retailers, market profile, dictionaries, weights) — no code
changes.

## Summary

A production-structured **FastAPI + SQLAlchemy** backend with a clear REST API.
It collects global signals, extracts structured product data, normalizes &
deduplicates, clusters repeated patterns deterministically, qualifies
opportunities, scans configured Swiss retailers, scores Swiss product matches
(auto-approving only high-confidence ones, routing the rest to human review),
measures coverage/gap, assesses transferability from a configured Swiss market
profile, computes opportunity & confidence scores, and returns a transparent,
rule-based recommendation with full evidence provenance. Demo mode runs fully
offline; replay mode is deterministic; live mode is SSRF-guarded.

## How to run

### frontend
```bash
cd frontend
npm install
cp .env.example .env          # then set VITE_API_BASE_URL=http://localhost:8000
npm run dev                   # opens http://localhost:5173
```

### backend
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # SQLite works as-is for the demo; set DATABASE_URL for Postgres/Supabase
alembic upgrade head          # or rely on SQLite auto-create for the demo
uvicorn app.main:app --reload # docs at http://localhost:8000/docs
pytest -q                     # 62 tests, offline & deterministic
```

Offline demo:

```bash
curl -XPOST localhost:8000/api/demo/reset
curl localhost:8000/api/discovery-runs            # get the run id
curl localhost:8000/api/discovery-runs/<id>/opportunities
curl localhost:8000/api/opportunities/<opp_id>/recommendation
```

## Inputs

- Market: Switzerland (configurable target market)
- Category: outdoor retail (configurable)
- Source set: `outdoor_global_default` — one global retailer adapter + one
  independent corroborating source; Swiss retailers `transa`, `galaxus`.
- Languages: English + German retail vocabulary (French/Italian configurable)
- Modes: `live` (configured URLs), `replay` (stored snapshots), `demo` (seeded
  fixtures). Optional: category, period (`lookback_days`), focus keywords.

## Source set & data flow

```
configured source set → collect → extract → normalize → deduplicate → cluster →
qualify → opportunities → Swiss search terms → Swiss scan → match → coverage →
transferability → score → recommendation → JSON/CSV export
```

Each stage persists status/timestamps/warnings/errors; a partial source failure
never destroys the run; nothing is fabricated after an extraction failure.

## Opportunity-generation method

Deterministic & inspectable: normalized fields (product type, features,
materials, customer, usage) → TF-IDF vectors → cosine similarity → single-linkage
agglomerative clustering, with a rule-based safeguard so unrelated broad
categories (e.g. a shared generic "protection" token) don't merge. A cluster
becomes an opportunity only if it meets configured minimums (≥3 signals, ≥2
independent sources, ≥2 brands/products/markets, ≥1 recent signal, no single
independence group >60%). Names follow *feature/material + product type +
segment/usage*. Markets are reported as **strongest observed** and **earliest
observed in this dataset** — never an unproven "origin".

## Swiss validation method

Generate German/English (config: FR/IT) search terms → scan configured Swiss
retailers (JSON-LD → structured listing → CSS selectors → Playwright fallback) →
deterministic match scoring (product type 35% / feature 30% / material 15% /
usage-customer 10% / keyword 10%). Matches ≥85 auto-approve (unless a defining
feature is missing), 55–84 go to human review, <55 are rejected. **Only approved
matches** feed Swiss coverage (retailer presence, depth, brand diversity, price
bands, feature coverage, availability) → `gap = 100 − coverage`.

## Scoring

- **Transferability** (climate 20 / geography 20 / customer 20 / regulatory 15 /
  price 15 / seasonality 10) from `market_profile_ch.yaml`; each factor returns
  score + rationale + rule source + confidence + limitations + `origin=CALCULATED`;
  no-rule factors are marked *unknown*, not invented.
- **Confidence** (credibility 35 / diversity 25 / freshness 20 / completeness 20).
- **Opportunity score** (momentum 25 / evidence breadth 20 / transferability 25 /
  assortment gap 25 / commercial feasibility 5 — feasibility is a labelled
  public-data **proxy**).
- Momentum describes a *repeated recent pattern*, not unproven growth.

## Action rules (deterministic, in order)

REJECT (transferability <40, regulatory <30, or a critical counter-signal) →
TEST (score ≥70, confidence ≥60, transferability ≥65, gap ≥55, reviews complete,
sufficient scan coverage) → CONTACT (score ≥65, transferability ≥60, gap ≥50,
supplier access the main gap) → RESEARCH (promising but evidence/review
incomplete) → MONITOR (credible but Swiss assortment already substantial / too
early). Every recommendation returns action, triggered rule, rationale,
supporting & counter-signal ids, scores, risks, missing evidence, provenance and
calculation version/timestamp. A TEST also returns a configurable experiment
plan (explicitly *not* a sales forecast).

## Ranked opportunities (demo output)

| Rank | Opportunity | Evidence | Confidence | Action |
| --- | --- | --- | --- | --- |
| 1 | UPF sun-protection hooded shirts for children | 3 signals, 3 independent sources, US+EU | ~80 | TEST |
| 2 | Insect-protection hiking trousers | 3 signals, US/EU/UK, regulatory flag | ~79 | CONTACT → TEST after review |
| 3 | PFAS-free waterproof shells | 3 signals, EU-strongest | ~79 | CONTACT |
| 4 | City-camping chairs | 3 signals; already well-covered in CH | ~80 | MONITOR |

(Exact scores are reproducible via `POST /api/demo/reset`.)

## Evidence trail

Every opportunity links to its raw signals (source name, URL, type, market,
observed date, brand, independence group) and to its Swiss scan items, coverage
snapshot, transferability assessment and recommendation — inspectable via the API
and the JSON/CSV exports.

## Reusability

All domain knowledge is configuration (`app/config_data/*.yaml`): source sets,
retailers, adapters, credibility, market profile, normalization dictionaries,
clustering/scoring/decision thresholds. Swapping these retargets the same engine
to another category, market or industry. Adapters and the job runner are
behind small interfaces for extension.

## Known limitations

- Ships with placeholder `example.com/.org` source URLs; live mode needs real,
  legally accessible endpoints.
- Pure-Python clustering/fuzzy matching favour clarity over scale (scikit-learn /
  RapidFuzz are optional drop-ins).
- Commercial feasibility is a public-data proxy (no margin/MOQ/conversion).
- Transferability is rule-based, not a compliance review.
- Background jobs are single-process (FastAPI BackgroundTasks).

## Future integrations

Real configured source/retailer endpoints; Playwright for JS-heavy Swiss
retailers; a real job queue (RQ/Celery/Arq); Supabase Storage for snapshots;
optional LLM for readable cluster summaries only (never scores); additional
language vocabularies (FR/IT); internal sell-through data to upgrade momentum
from "repeated pattern" to measured growth.

## Architecture notes

See [`backend/README.md`](backend/README.md) and [`backend/API.md`](backend/API.md).
