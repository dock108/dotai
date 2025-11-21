# dock108 Monorepo

A single home for every dock108 surface: the AI theory engine, the guardrails that sit in front of GPT/OpenAI, the future React frontends, and the existing Swift prompting game. The repo is intentionally structured so each product experience can share the same Python backend and shared packages while deploying to Hetzner via Docker (and Kubernetes later).

## Directory Map

```
apps/                 # All user-facing experiences
  dock108-web/        # Marketing + docs hub (Next.js placeholder)
  game-web/           # AI prompting game (Swift prototype + React/Next.js)
  playlist-web/       # Legacy YouTube curator MVP (Next.js)
  highlight-channel-web/  # Sports highlight channel builder (Next.js) ⭐ Active
  theory-*-web/       # Domain-specific theory surfaces (bets, crypto, stocks, conspiracies) ⭐ Active
services/             # Python + worker backends
  theory-engine-api/  # FastAPI backend (Sports highlights, theory evaluation) ⭐ Active
  data-workers/       # Celery workers for odds/prices/YouTube caching ⭐ Active
packages/             # Shared UI + client/server libraries
  py-core/           # Python schemas, guardrails, scoring, clients ⭐ Active
  ui-kit/            # Shared React components ⭐ Active
  js-core/            # JavaScript SDK and utilities ⭐ Active
infra/                # Docker, k8s, nginx deploy assets for Hetzner
docs/                 # Living architecture + guardrail specs
```

## Current Status

### Active Features

- **Sports Highlight Channel** (`apps/highlight-channel-web` + `services/theory-engine-api`):
  - Natural language playlist generation from sports queries
  - Guided UI builder with structured input (sports, teams, players, play types, date ranges)
  - AI-powered parsing, guardrails, YouTube search, intelligent caching
  - Iterative filtering with AI-powered description analysis
  - Recent highlights focus (last 48 hours to 30 days)
  - See [Sports Highlight Channel Feature](#sports-highlight-channel-feature) below

### Other Apps

- `apps/playlist-web`: Legacy YouTube curator MVP (Next.js) - original playlist builder
- `apps/game-web/swift-prototype`: Shipping SwiftUI AI lesson game (spec for future React port)
- `apps/game-web`: React/Next.js port (in progress)
- `apps/theory-*-web`: Domain-specific theory surfaces (placeholders for bets, crypto, stocks, conspiracies)

## Sports Highlight Channel Feature

The Sports Highlight Channel feature allows users to build custom YouTube playlists of sports highlights using natural language. The system:

1. **Parses user requests** using AI to extract sport, teams, dates, and content preferences
2. **Searches YouTube** for relevant highlight videos using official channels and major sports networks
3. **Scores and filters** videos based on relevance, channel reputation, freshness, and view counts
4. **Builds playlists** that match requested duration with intelligent caching to reduce API costs
5. **Provides explanations** showing assumptions, filters applied, and ranking factors

### Quick Start

For comprehensive local development and testing instructions, see **[`docs/LOCAL_DEPLOY.md`](docs/LOCAL_DEPLOY.md)**.

**Quick summary:**
1. Install prerequisites: Python 3.11+, Node.js 18+, PostgreSQL 14+, `uv`, `pnpm`
2. Set up database (local PostgreSQL or Docker)
3. Get API keys: YouTube Data API, OpenAI API
4. Configure environment: Copy `.env.example` to `services/theory-engine-api/.env`
5. Start backend: `cd services/theory-engine-api && uv sync && uv pip install -e ../../packages/py-core && alembic upgrade head && uv run uvicorn app.main:app --reload`
6. Start frontend: `cd apps/highlight-channel-web && pnpm install && pnpm dev`

### API Endpoints

**Highlights API:**
- `POST /api/highlights/plan` - Plan a highlight playlist from user query
- `GET /api/highlights/{playlist_id}` - Get detailed playlist information
- `GET /api/highlights/metrics` - Get metrics (sports requested, avg duration, cache hit rate)
- `GET /api/highlights/metrics/csv` - Get metrics as CSV for dashboard

See [`docs/HIGHLIGHTS_API.md`](docs/HIGHLIGHTS_API.md) for detailed API documentation.

## Testing and Deployment

- **Local Development**: See `docs/LOCAL_DEPLOY.md` for comprehensive local setup and testing guide (Sports Highlight Channel feature)
- **Production Deployment**: See `infra/DEPLOYMENT.md` for full monorepo deployment guide (all services and apps)

## Getting Started

1. **For local development**: See [`docs/LOCAL_DEPLOY.md`](docs/LOCAL_DEPLOY.md) for step-by-step setup
2. **For production deployment**: See [`infra/DEPLOYMENT.md`](infra/DEPLOYMENT.md) for full monorepo deployment
3. **Documentation**: See [`docs/README.md`](docs/README.md) for complete documentation index

### Prerequisites

- Python 3.11+ with `uv` package manager
- Node.js 18+ with `pnpm`
- PostgreSQL 14+
- YouTube Data API key
- OpenAI API key

## Project Status

### Completed ✅

- **Sports Highlight Channel MVP**: Full-stack feature with AI parsing, guardrails, caching, and metrics
- **Guided UI Builder**: Structured input with sports checklists, player/team/play type chips, date presets, duration sliders
- **Code Cleanup**: 
  - Backend: Centralized datetime utilities, date range helpers, error handlers
  - Frontend: Extracted constants, types, utilities, and presets into `src/lib/` modules
  - Removed duplicate code and improved modularity
- **Shared Python Core** (`packages/py-core`): Schemas, guardrails, scoring utilities, YouTube client, staleness logic
- **Theory Engine API** (`services/theory-engine-api`): FastAPI backend with highlights endpoints, database models, migrations
- **Infrastructure**: Docker Compose setup for full monorepo deployment
- **Documentation**: Comprehensive guides for local development and production deployment

### In Progress 🚧

- **React Game Port** (`apps/game-web`): Porting Swift prototype to React/Next.js
- **Kubernetes Deployment**: GitOps pipeline for Hetzner cluster

### Completed ✅ (Latest)

- **Theory Surfaces** (`apps/theory-*-web`): All 4 theory apps (bets, crypto, stocks, conspiracies) now functional with shared components
- **JavaScript Core** (`packages/js-core`): TypeScript SDK with API client, React hooks, and type-safe endpoints
- **Shared UI Kit** (`packages/ui-kit`): Expanded with LoadingSpinner, ErrorDisplay, PresetChips, DomainHeader, PageLayout, Container, Section
- **Data Workers** (`services/data-workers`): Celery-based workers for YouTube caching, odds snapshots, and market prices (placeholders ready for API integration)
- **Enhanced TheoryCard**: Domain-specific fields with collapsible sections for all theory types

### Planned 📋

- **Custom Models**: Train bespoke graders on collected theory data
- **API Cache Integration**: Update theory-engine-api to use Redis cache from workers

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for detailed roadmap.
