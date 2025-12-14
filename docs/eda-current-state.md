# EDA Current State (Dec 2025)

Admin-only EDA / Modeling Lab as of the current codebase. Sources: `services/theory-engine-api/app/routers/sports_eda.py`, `apps/theory-bets-web/src/app/admin/theory-bets/eda/page.tsx`, `apps/theory-bets-web/src/components/admin/eda/*`, `apps/theory-bets-web/src/lib/api/sportsAdmin.ts`.

## Endpoints (sports_eda)
- `GET /api/admin/sports/eda/stat-keys/{league}`: distinct team/player stat keys from boxscores for the league.
- `POST /generate-features`: turns selected raw stats into derived feature descriptors + summary.
- `POST /preview`: feature matrix sample; `format=json` returns data-quality stats, `format=csv` streams rows (optionally with target).
- `POST /analyze`: builds feature matrix, computes target values, correlations, micro rows, evaluation block. Returns top-level blocks: `meta`, `theory`, `cohort` (with `odds_coverage_pct`), `micro_rows`, `evaluation` (stat uses numeric formatting, not percent), `modeling` (available/has_run), `monte_carlo` (available/has_run), `notes`. Persists run payload + micro rows CSV pointer (see Persistence).
- `POST /analyze/export`: streams aligned feature matrix with target.
- `POST /micro-model/export`: streams micro_model rows (game-level outputs).
- `POST /build-model`: trains lightweight logistic regression for market targets, runs MC, exposure controls, theory candidates (market only), and returns model snapshot. Stat targets skip training/MC but still return descriptive payloads.
- `GET /analysis-runs`, `GET /analysis-runs/{id}`: list/load persisted runs (metadata + micro sample).
- `POST /walkforward`: rolling train/test replay for market targets; persists slice metrics + predictions CSV pointer.
- Shared knobs: `context` (`deployable` drops post-game features; `diagnostic` allows them), `cleaning` (drop null/non-numeric/min non-null), `feature_mode` (`admin`/`full`), filters (seasons, phase, recent_days, team, player, spread band).

- UI surface (theory-bets-web admin)
- Pipeline tabs: Theory Definition → Cohort & Micro → Evaluation → Market Mapping → Modeling → Robustness MC → Walk-forward → Live Matches (stubs).
- Filters: league, seasons + scope (full/current/recent), NCAAB phase, team/player search, spread band, optional season/market/side text, team/player stat-key multiselects (player keys collected but not sent to API today).
- Workflow copy is target-aware: stat targets end at Evaluation (complete); market targets can continue to optional modeling/MC.
- Results: feature list/summary, status banner, ResultsSection (stat path hides market columns; market path shows micro table with odds/model columns, metrics, modeling + MC status), publishing readiness checklist, model weights, suggested theories/candidates (market only), MC summary/assumptions/interpretation, theory drafts (local-only), odds coverage shown when available.
- Advanced diagnostics: cleaning toggles, data-quality table (from preview JSON), correlation table, CSV exports (feature matrix, micro rows, preview).
- Run viewer: saved runs can be opened (replay micro/evaluation/modeling/MC), micro rows download link shown when persisted.

## Target definitions (UI lists)
- Stat targets (metric_type numeric unless noted, odds_required=false): `home_points`, `away_points`, `combined_score`, `margin_of_victory`, `winner` (binary).
- Market targets (metric_type binary, odds_required=true): `ats_cover` (spread, side home/away), `moneyline_win` (moneyline, side home/away), `total_over_hit` (total, side over/under).
- Default: stat `combined_score`, locked by default; switching class updates required fields (market_type/side).

## Persistence today
- Runs persisted via micro store with UUIDs: target, request, evaluation, modeling/MC status, micro_rows_ref (CSV), optional model_snapshot/mc_summary.
- `EDA_RUNS_DIR` (default `/tmp/eda_runs`) stores micro rows CSV and walkforward predictions.
- `GET /analysis-runs` / `GET /analysis-runs/{id}` provide summaries and samples; no DB writes yet.
- Walkforward persists slice metrics + predictions CSV pointer.

- ## Noted mismatches / caveats
- Player stat key selections collected in UI are not included in `generate-features`/`analyze`/`preview`/`build-model` requests; only team stat keys are sent.
- Modeling status is returned for stat targets (descriptive only); triggers/MC disabled for stats.
- Suggested theories are generated only for market/binary targets; stat targets skip candidates.

