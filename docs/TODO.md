# TODO / Futures

Single place to collect follow-ups and limitations pulled from docs.\

## Theory Engine / EDA
- Add “Single-Game Monte Carlo” sandbox: given one upcoming/historical game + a micro-model (or a saved `analysis_run` model), run an odds-aware MC to produce a distribution of units/ROI (P5/P50/P95 + drawdown) and persist/share the result. Support admin first; optionally expose to users later with strict guardrails (no auto-bet/promotion gating; requires real odds coverage).

## Local Deploy
- After setup, review highlights and theory surface docs; see deployment guide for full production steps.

## YouTube OAuth / Setup
- Test playlist creation with a simple request.
- Verify tokens refresh automatically; monitor expiration/refresh cycles.
- Set up production OAuth credentials with correct redirect URIs.

## Highlights MVP
- Add user accounts/history/favorites/personalization.
- Improve content mix controls and query specificity.
- Support real-time/auto-refresh playlists.
- Optimize multi-sport and cross-sport scenarios.
- Add video quality filtering.

## Infra / Docker
- Base images for Next.js apps (node + pnpm) and Python services.
- `docker-compose.dev.yml` for FastAPI + workers + Postgres + Redis.
- Build scripts to push images to registry.

## Prompt Game iOS
- Plug in real API key and test live completions on devices.
- Optional palette tuning.
- Add more unit/UI tests.
- Consider persisting solved/failed state across launches.

