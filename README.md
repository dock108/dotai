# dock108 Monorepo

A single home for every dock108 surface: the AI theory engine, the guardrails that sit in front of GPT/OpenAI, the future React frontends, and the existing Swift prompting game. The repo is intentionally structured so each product experience can share the same Python backend and shared packages while deploying to Hetzner via Docker (and Kubernetes later).

## Directory Map

```
apps/                 # All user-facing experiences
  dock108-web/        # Marketing + docs hub (Next.js placeholder)
  game-web/           # Swift prototype today, React/Next.js target
  playlist-web/       # Running YouTube curator MVP (Next.js)
  theory-*-web/       # Domain-specific theory surfaces (placeholders)
services/             # Python + worker backends
packages/             # Shared UI + client/server libraries
infra/                # Docker, k8s, nginx deploy assets for Hetzner
docs/                 # Living architecture + guardrail specs
```

## Current Apps

- `apps/playlist-web`: existing Next.js playlist builder with all source + scripts.
- `apps/game-web/swift-prototype`: the shipping SwiftUI AI lesson game; doubles as the spec for the future React port.
- `apps/highlight-channel-web`: Sports highlight channel builder - create custom highlight playlists from natural language requests.

## Sports Highlight Channel Feature

The Sports Highlight Channel feature allows users to build custom YouTube playlists of sports highlights using natural language. The system:

1. **Parses user requests** using AI to extract sport, teams, dates, and content preferences
2. **Searches YouTube** for relevant highlight videos using official channels and major sports networks
3. **Scores and filters** videos based on relevance, channel reputation, freshness, and view counts
4. **Builds playlists** that match requested duration with intelligent caching to reduce API costs
5. **Provides explanations** showing assumptions, filters applied, and ranking factors

### Local Development

#### Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend apps)
- PostgreSQL database
- YouTube Data API key

#### Environment Variables

Create a `.env` file in `services/theory-engine-api/`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dock108

# YouTube API
YOUTUBE_API_KEY=your_youtube_api_key_here

# Optional - for playlist creation
YOUTUBE_OAUTH_ACCESS_TOKEN=your_oauth_token
YOUTUBE_PLAYLIST_CHANNEL_ID=your_channel_id

# OpenAI (for AI parsing)
OPENAI_API_KEY=your_openai_key
```

#### Running the API

```bash
cd services/theory-engine-api
uv sync  # Install dependencies
alembic upgrade head  # Run database migrations
uvicorn app.main:app --reload --port 8000
```

#### Running the Frontend

```bash
cd apps/highlight-channel-web
npm install
npm run dev  # Runs on http://localhost:3005
```

#### API Endpoints

- `POST /api/highlights/plan` - Plan a highlight playlist from user query
- `GET /api/highlights/{playlist_id}` - Get detailed playlist information
- `GET /api/highlights/metrics` - Get metrics (sports requested, avg duration, cache hit rate)
- `GET /api/highlights/metrics/csv` - Get metrics as CSV for dashboard

See `docs/HIGHLIGHTS_API.md` for detailed API documentation.

## Testing and Deployment

- **Local Development**: See `docs/LOCAL_DEPLOY.md` for comprehensive local setup and testing guide (Sports Highlight Channel feature)
- **Production Deployment**: See `infra/DEPLOYMENT.md` for full monorepo deployment guide (all services and apps)

## Getting Started

1. Install `asdf` or a shared version manager for Node (for the Next.js apps) and Python (for FastAPI + workers).
2. Copy `.env.example` files that live inside each app/service.
3. Use Docker Compose under `infra/docker` (coming soon) to boot Hetzner-like environments locally.

## Next Steps

- Flesh out `services/theory-engine-api` (FastAPI) and `services/data-workers` (ETL jobs for odds/prices/YouTube caching).
- Stand up the shared packages (`ui-kit`, `js-core`, `py-core`) once interfaces settle.
- Replace the Swift prototype with a shared React experience once the guardrails + backend are ready.
- Document deployment runbooks in `infra/` once Hetzner stack is scripted.
