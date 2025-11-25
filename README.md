# dock108 Monorepo

A unified platform for AI-powered theory evaluation across multiple domains. This monorepo contains all dock108 surfaces: theory evaluation engines (bets, crypto, stocks, conspiracies), sports highlight generation, and a prompting game. Every surface shares the same Python backend, guardrails, and shared UI components, enabling rapid development and consistent user experiences.

**Key Features:**
- **Multi-domain theory evaluation** with domain-specific analysis and guardrails
- **Sports betting data ingestion** with boxscore and odds scraping
- **Sports highlight playlist generation** with AI-powered parsing
- **Shared UI components** for consistent branding across all apps
- **Centralized infrastructure** with Docker Compose and Traefik routing

## Directory Map

```
apps/                      # All user-facing experiences (Next.js)
  dock108-web/             # Unified landing portal and app directory
  highlights-web/          # Sports highlights playlist generator ⭐ Active
  theory-bets-web/        # Sports betting theory evaluation ⭐ Active
  theory-crypto-web/      # Crypto strategy interpreter ⭐ Active
  theory-stocks-web/      # Stock analysis theory evaluation ⭐ Active
  conspiracy-web/         # Conspiracy theory fact-checking ⭐ Active
  prompt-game-web/        # AI prompting game (React/Next.js + Swift prototype)
  playlist-web/           # Legacy YouTube curator MVP

services/                  # Python backend services
  theory-engine-api/       # FastAPI backend (all theory domains, highlights) ⭐ Active
  theory-bets-scraper/    # Sports data ingestion (boxscores, odds) ⭐ Active
  data-workers/           # Celery workers (YouTube cache, odds snapshots, prices) ⭐ Active

packages/                  # Shared libraries
  py-core/                # Python schemas, guardrails, scoring, API clients ⭐ Active
  js-core/                # TypeScript SDK, React hooks, API client ⭐ Active
  ui/                     # Shared UI components (DockHeader, DockFooter, theme) ⭐ Active
  ui-kit/                 # Domain-specific UI components (TheoryForm, TheoryCard) ⭐ Active

infra/                     # Infrastructure and deployment
  docker/                 # Dockerfiles for all services and apps
  docker-compose.yml      # Full stack orchestration
  traefik/                # Reverse proxy and SSL configuration
  k8s/                    # Kubernetes manifests (future)

docs/                      # Comprehensive documentation
  ARCHITECTURE.md         # System architecture overview
  LOCAL_DEPLOY.md         # Local development guide
  ROADMAP.md              # Future plans and features
  ...                     # Feature-specific documentation
```

## Current Status

### Active Features

#### Theory Evaluation Surfaces
All theory evaluation apps are fully functional with shared UI components and backend integration:

- **Sports Betting** (`apps/theory-bets-web`): Evaluate betting theories with data-driven analysis
  - Sports data admin UI for boxscore/odds ingestion monitoring
  - Game browser with advanced filtering and detail views
  - Integration with theory-engine-api for evaluation

- **Crypto Strategies** (`apps/theory-crypto-web`): Crypto strategy interpreter with backtesting
  - LLM-powered strategy interpretation
  - Backtest blueprint generation
  - Alert specification and management
  - Full strategy detail views with tabs

- **Stock Analysis** (`apps/theory-stocks-web`): Stock market theory evaluation
  - Pattern recognition and analysis
  - Data-driven feedback

- **Conspiracy Theory** (`apps/conspiracy-web`): Fact-checking with narrative analysis
  - Mini-documentary summaries
  - Evidence comparison and rubric-based scoring (0-100)
  - Wikipedia and fact-check database integration
  - See [`docs/CONSPIRACY_THEORY.md`](docs/CONSPIRACY_THEORY.md) for details

#### Sports Data Ingestion
- **Boxscore + Odds Scraper** (`services/theory-bets-scraper`): Historical sports data collection
  - Configurable ingestion for major US sports (NFL, NCAAF, NBA, NCAAB, MLB, NHL)
  - Idempotent persistence with no duplicate games
  - Admin UI for monitoring and triggering scrape runs
  - Odds API integration for betting lines

#### Sports Highlights
- **Highlight Playlist Generator** (`apps/highlights-web`): Natural language playlist creation
  - AI-powered parsing of user queries
  - YouTube search with channel reputation scoring
  - Intelligent caching to reduce API costs
  - Embedded player with temporary watch links (48-hour expiration)
  - See [Sports Highlight Channel Feature](#sports-highlight-channel-feature) below

### Other Apps

- `apps/dock108-web`: Unified landing portal with app directory
- `apps/playlist-web`: Legacy YouTube curator MVP (original playlist builder)
- `apps/prompt-game-web`: AI prompting game (React/Next.js port in progress, Swift prototype available)

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
6. Start frontend: `cd apps/highlights-web && pnpm install && pnpm dev`

### API Endpoints

**Highlights API:**
- `POST /api/highlights/plan` - Plan a highlight playlist from user query
- `GET /api/highlights/{playlist_id}` - Get detailed playlist information
- `POST /api/highlights/{playlist_id}/watch-token` - Generate temporary watch token (48-hour expiration)
- `GET /api/highlights/watch/{token}` - Access playlist via watch token
- `GET /api/highlights/metrics` - Get metrics (sports requested, avg duration, cache hit rate)
- `GET /api/highlights/metrics/csv` - Get metrics as CSV for dashboard

See [`docs/HIGHLIGHTS_API.md`](docs/HIGHLIGHTS_API.md) for detailed API documentation.

## Testing and Deployment

- **Local Development**: See `docs/LOCAL_DEPLOY.md` for comprehensive local setup and testing guide (Sports Highlight Channel feature)
- **Production Deployment**: See `infra/DEPLOYMENT.md` for full monorepo deployment guide (all services and apps)

## Quick Start

### Prerequisites

- **Python 3.11+** with `uv` package manager
- **Node.js 18+** with `pnpm`
- **PostgreSQL 14+** (local or Docker)
- **Redis** (for caching and Celery)
- **API Keys**:
  - OpenAI API key (for LLM evaluation)
  - YouTube Data API key (for highlights feature)
  - Odds API key (for sports betting data, optional)

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repo-url>
   cd dock108
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Install dependencies**:
   ```bash
   # Python packages
   cd services/theory-engine-api
   uv sync
   uv pip install -e ../../packages/py-core
   
   # Node packages (from repo root)
   pnpm install
   ```

3. **Start infrastructure**:
   ```bash
   cd infra
   ./docker-compose.sh up -d postgres redis
   ```

4. **Run database migrations**:
   ```bash
   cd services/theory-engine-api
   alembic upgrade head
   ```

5. **Start backend**:
   ```bash
   cd services/theory-engine-api
   uv run uvicorn app.main:app --reload
   ```

6. **Start frontend** (choose one):
   ```bash
   # Main portal
   cd apps/dock108-web && pnpm dev
   
   # Or specific app
   cd apps/theory-bets-web && pnpm dev
   ```

### Production Deployment

See [`infra/DEPLOYMENT.md`](infra/DEPLOYMENT.md) for complete production deployment guide.

### Documentation

- **[`docs/README.md`](docs/README.md)** - Complete documentation index
- **[`docs/LOCAL_DEPLOY.md`](docs/LOCAL_DEPLOY.md)** - Detailed local development guide
- **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** - System architecture overview
- **[`infra/README.md`](infra/README.md)** - Infrastructure documentation
- **[`START.md`](START.md)** - Quick Docker-based startup guide
- **[`LOAD_SPORTS_DATA.md`](LOAD_SPORTS_DATA.md)** - Guide for loading sports data via admin UI

## Project Status

### Completed ✅

#### Core Infrastructure
- **Monorepo Structure**: Unified codebase with shared packages and services
- **Docker Compose**: Full stack orchestration with Traefik routing
- **Environment Management**: Centralized `.env` file at repo root
- **Shared UI Components** (`packages/ui`): DockHeader, DockFooter, theme system
- **Shared UI Kit** (`packages/ui-kit`): TheoryForm, TheoryCard, LoadingSpinner, ErrorDisplay, and more
- **JavaScript Core** (`packages/js-core`): TypeScript SDK with API clients, React hooks, type-safe endpoints
- **Python Core** (`packages/py-core`): Schemas, guardrails, scoring utilities, API clients

#### Backend Services
- **Theory Engine API** (`services/theory-engine-api`): FastAPI backend with:
  - Multi-domain theory evaluation (bets, crypto, stocks, conspiracies)
  - Sports highlights playlist generation
  - Sports data admin endpoints
  - Strategy interpretation and backtesting
  - Database models and Alembic migrations
  - Structured logging with structlog
  - Centralized utilities (datetime, error handling, date ranges)

- **Sports Data Scraper** (`services/theory-bets-scraper`): 
  - Boxscore ingestion for major US sports
  - Odds API integration
  - Celery-based job execution
  - Idempotent persistence

- **Data Workers** (`services/data-workers`): Celery workers for:
  - YouTube video metadata caching
  - Odds snapshot collection
  - Market price updates

#### Frontend Apps
- **All Theory Apps**: Fully functional with shared components and backend integration
  - `theory-bets-web`: Sports betting evaluation + admin UI
  - `theory-crypto-web`: Crypto strategy interpreter with backtesting
  - `theory-stocks-web`: Stock analysis evaluation
  - `conspiracy-web`: Conspiracy fact-checking with narrative engine

- **Highlights Web**: Sports highlight playlist generator with AI parsing
- **Dock108 Web**: Unified landing portal and app directory

#### Code Quality
- **Modular Architecture**: Clear separation of concerns across services
- **No Duplicates**: Centralized utilities and shared components
- **Comprehensive Comments**: Well-documented code with architecture explanations
- **Type Safety**: TypeScript and Pydantic throughout
- **Standards Compliance**: Consistent patterns across all services and apps

### In Progress 🚧

- **React Game Port** (`apps/prompt-game-web`): Porting Swift prototype to React/Next.js
- **Kubernetes Deployment**: GitOps pipeline for Hetzner cluster
- **Custom Models**: Training bespoke graders on collected theory data

### Planned 📋

- **Custom Models**: Train bespoke graders on collected theory data
- **API Cache Integration**: Update theory-engine-api to use Redis cache from workers

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for detailed roadmap.
