# TODO / Futures

## Theory Builder

### MVP Complete ✅
- [x] Replace old EDA page with Theory Builder
- [x] Simple Define → Run → Results flow
- [x] Market targets: ATS, Totals, ML
- [x] Context presets: Minimal, Standard, Market-aware
- [x] Summary sentence with lift %
- [x] Structured assessment with checkmarks
- [x] Sample games table
- [x] Collapsed correlations
- [x] Feature flags for hidden features
- [x] `/future/` folders for parked designs

### Feature-Flagged (Ready When Enabled)
- [ ] `FEATURE_MODEL_BUILDING` - Logistic regression training
- [ ] `FEATURE_MONTE_CARLO` - Bet simulation
- [ ] `FEATURE_STABILITY_BREAKDOWN` - Season stability charts
- [ ] `FEATURE_ROI` - ROI calculation display
- [ ] `FEATURE_PLAYER_MODELING` - Player filters and features
- [ ] `FEATURE_TEAM_STAT_TARGETS` - Non-market stat analysis
- [ ] `FEATURE_CUSTOM_CONTEXT` - Individual feature toggles
- [ ] `FEATURE_DIAGNOSTICS` - Post-game diagnostic features

### Parked (v2+)
See `/future/` for design notes:
- Theory resolution modes (per-team vs game-level)
- Player-level modeling
- Nonlinear bucketing analysis
- Automatic side selection

## Highlights MVP
- [ ] Add user accounts/history/favorites
- [ ] Improve content mix controls
- [ ] Support real-time/auto-refresh playlists
- [ ] Add video quality filtering

## Infrastructure
- [ ] Base Docker images for Next.js and Python
- [ ] `docker-compose.dev.yml` improvements
- [ ] Build scripts for registry

## YouTube OAuth
- [ ] Test playlist creation
- [ ] Verify token refresh
- [ ] Production OAuth credentials
