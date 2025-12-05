# Roadmap

## Completed ✅

### Infrastructure & Architecture
- Monorepo structure with pnpm workspaces
- Docker Compose orchestration with centralized `.env`
- PostgreSQL database with Alembic migrations
- Redis for caching and Celery task queue
- Makefile for simplified Docker commands

### Backend Services
- **Theory Engine API** (FastAPI)
  - Multi-domain theory evaluation (bets, crypto, stocks, conspiracies)
  - Sports highlights playlist generation with AI parsing
  - Admin endpoints for data management
  - Structured logging with structlog
  
- **Sports Data Scraper** (Celery workers)
  - Boxscore ingestion for 6 major US sports (NBA, NFL, MLB, NHL, NCAAB, NCAAF)
  - Odds API integration for betting lines
  - Team name normalization
  - Idempotent persistence

### Frontend Applications
- Theory evaluation surfaces (bets, crypto, stocks, conspiracies)
- Sports highlights playlist generator
- Unified landing portal (dock108-web)
- Admin UI for data management and tracing

### Shared Packages
- `py-core`: Python schemas, guardrails, scoring
- `js-core`: TypeScript SDK, React hooks
- `ui`: Shared UI components
- `ui-kit`: Domain-specific components

### Theory Bets v1 Pipeline
- LLM prompt grading and config inference
- Historical data retrieval with "last seen" odds
- 2-season historical performance analysis
- 30-day backtest
- Monte Carlo simulation for upcoming bets
- Kelly criterion and P2P pricing
- Results page with tabbed interface
- Admin tracing for debugging

## In Progress 🚧

### Model Refinement
- Real filters implementation (back-to-back, altitude, etc.)
- Enhanced Monte Carlo simulations with actual model predictions
- Better edge detection algorithms

### Admin Tools
- Improved data browser styling
- Aggregate stats in API responses
- Enhanced filtering capabilities

## Planned 📋

### Short Term
- [ ] Fix admin UI contrast issues
- [ ] Add aggregate stats to games API
- [ ] Implement real theory filters
- [ ] Enhanced Monte Carlo with trained models

### Medium Term
- [ ] User authentication and theory history
- [ ] Kubernetes manifests for production deployment
- [ ] API rate limiting and key management
- [ ] Custom model training on collected data

### Long Term
- [ ] Partner API access
- [ ] Real-time market data integration
- [ ] A/B testing infrastructure
- [ ] Mobile apps (React Native)
