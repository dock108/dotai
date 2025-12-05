# Unified Theory Bets System

## What changed
- Main page (`/`) now submits directly to the v1 pipeline via `POST /api/theory-runs` and redirects to `/theory/{run_id}` for results.
- Admin tracing added at `/admin/theory-bets/runs` (UI) and `/api/admin/theory-runs` (API) to view all runs.
- Legacy bets endpoint (`POST /api/theory/bets`) removed.
- Legacy `/theory/new` entry page removed (main page is the single entry point).

## How to use
- User: go to `/`, submit a theory, get redirected to `/theory/{run_id}`.
- Admin: go to `/admin/theory-bets/runs` to browse/filter runs and click through to results.
- Admin (EDA / Modeling Lab): go to `/admin/theory-bets/eda` to generate features, run correlations, build lightweight models, and export the feature matrix (CSV) in a new tab; link to the exact game sample is provided in the analysis card.

## Endpoints
- User: `POST /api/theory-runs`, `GET /api/theory-runs/{id}`
- Admin: `GET /api/admin/theory-runs`, `GET /api/admin/theory-runs/{id}`
- Admin (EDA): `POST /api/admin/sports/eda/generate-features`, `POST /api/admin/sports/eda/analyze`, `POST /api/admin/sports/eda/build-model`, `POST /api/admin/sports/eda/analyze/export`

## Known limits
- Monte Carlo and filters are still basic/stubbed; refine with real models/filters as next step.

