# TODO / Futures

Single place to collect follow-ups and limitations.

## Theory Builder / EDA

### Completed (Dec 2025)
- ✅ Replace old EDA page with Theory Builder (Define → Run → Results flow)
- ✅ Implement `TheoryDraft` schema as single source of truth
- ✅ Context presets (Minimal, Standard, Market-aware, Verbose, Custom)
- ✅ Collapsible stats selector with summary
- ✅ Structured verdict with checkmarks (lift, sample size, stability)
- ✅ Human-readable summary sentences
- ✅ Sample games table with Date, Home/Score, Away/Score, Target, Result
- ✅ Collapsed correlations with diagnostic framing
- ✅ Tab validation (disable Run until valid, disable Results until analysis)
- ✅ Side made optional for spread/ML targets

### In Progress
- [ ] Populate micro rows with actual game data (home_team, away_team, scores, date)
- [ ] Stability visualization (bar charts instead of raw objects)
- [ ] Walk-forward results display

### Future
- [ ] Single-Game Monte Carlo sandbox: given one game + saved model, run odds-aware MC to produce P5/P50/P95 distribution and drawdown. Admin first, optionally expose to users with guardrails.
- [ ] "Why this might work" auto-summary based on detected concepts
- [ ] Saved theory templates (reuse common configurations)
- [ ] Bulk theory comparison view

## Local Deploy
- [ ] After setup, review highlights and theory surface docs
- [ ] See deployment guide for full production steps

## YouTube OAuth / Setup
- [ ] Test playlist creation with a simple request
- [ ] Verify tokens refresh automatically
- [ ] Set up production OAuth credentials with correct redirect URIs

## Highlights MVP
- [ ] Add user accounts/history/favorites/personalization
- [ ] Improve content mix controls and query specificity
- [ ] Support real-time/auto-refresh playlists
- [ ] Optimize multi-sport and cross-sport scenarios
- [ ] Add video quality filtering

## Infra / Docker
- [ ] Base images for Next.js apps (node + pnpm) and Python services
- [ ] `docker-compose.dev.yml` for FastAPI + workers + Postgres + Redis
- [ ] Build scripts to push images to registry

## Prompt Game iOS
- [ ] Plug in real API key and test live completions on devices
- [ ] Optional palette tuning
- [ ] Add more unit/UI tests
- [ ] Consider persisting solved/failed state across launches
