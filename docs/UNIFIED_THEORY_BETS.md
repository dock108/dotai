# Unified Theory Bets System

## What changed
- Main page (`/`) now submits directly to the v1 pipeline via `POST /api/theory-runs` and redirects to `/theory/{run_id}` for results.
- Admin tracing added at `/admin/theory-bets/runs` (UI) and `/api/admin/theory-runs` (API) to view all runs.
- Legacy bets endpoint (`POST /api/theory/bets`) removed.
- Legacy `/theory/new` entry page removed (main page is the single entry point).

## How to use
- User: go to `/`, submit a theory, get redirected to `/theory/{run_id}`.
- Admin: go to `/admin/theory-bets/runs` to browse/filter runs and click through to results.
- Admin (EDA / Modeling Lab): go to `/admin/theory-bets/eda` to generate features, preview the full feature matrix (CSV, new tab), view a filterable data-quality report (null %, non-numeric, distinct), and run correlations. Stat targets are evaluated immediately (cohort vs baseline; no model required). Market targets can optionally run a lightweight model and Monte Carlo when odds exist. CSV export and a link to the exact game sample are provided.

## Endpoints
- User: `POST /api/theory-runs`, `GET /api/theory-runs/{id}`
- Admin: `GET /api/admin/theory-runs`, `GET /api/admin/theory-runs/{id}`
- Admin (EDA): `POST /api/admin/sports/eda/generate-features`, `POST /api/admin/sports/eda/preview` (CSV/JSON with filters/sorting), `POST /api/admin/sports/eda/analyze` (evaluation complete without modeling), `POST /api/admin/sports/eda/build-model` (optional, market targets), `POST /api/admin/sports/eda/analyze/export` (CSV, respects cleaning)

