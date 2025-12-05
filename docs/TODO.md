# TODO / Futures

Single place to collect follow-ups and limitations pulled from docs.

## Theory Bets / EDA
- Refine Monte Carlo and theory filters with real models/filters.

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

