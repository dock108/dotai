# dock108 Architecture Overview

## 0. Vision Snapshot

Dock108 hosts a family of “theory surfaces” (bets, crypto, stocks, conspiracies, playlists) and a prompting game. Every surface connects to the same Python theory engine, data workers, and guardrails before any LLM call. Frontends are React (Next.js) apps, with the existing Swift game living alongside them until the React port lands.

## 1. Monorepo Layers

1. **Apps** (`apps/`) – User-facing Next.js web applications:
   - `dock108-web` - Unified landing portal and app directory
   - `highlights-web` - Sports highlight playlist generator
   - `theory-bets-web` - Sports betting theory evaluation + admin UI
   - `theory-crypto-web` - Crypto strategy interpreter with backtesting
   - `theory-stocks-web` - Stock analysis theory evaluation
   - `conspiracy-web` - Conspiracy theory fact-checking
   - `prompt-game-web` - AI prompting game (React + Swift prototype)
   - `playlist-web` - Legacy YouTube curator MVP
   
   All apps share UI components and client libraries from `packages/`.

2. **Services** (`services/`) – Python backend services:
   - `theory-engine-api` - FastAPI backend for all theory domains, highlights, and admin APIs
   - `theory-bets-scraper` - Sports data ingestion (boxscores, odds) via Celery
   - `data-workers` - Celery workers for YouTube caching, odds snapshots, market prices

3. **Packages** (`packages/`) – Shared libraries:
   - `ui` - Core UI components (DockHeader, DockFooter, theme system)
   - `ui-kit` - Domain-specific components (TheoryForm, TheoryCard, etc.)
   - `js-core` - TypeScript SDK with API clients, React hooks, type-safe endpoints
   - `py-core` - Python schemas, guardrails, scoring utilities, API clients

4. **Infra** (`infra/`) – Deployment infrastructure:
   - Dockerfiles for all services and apps
   - Docker Compose orchestration with Traefik routing
   - Kubernetes manifests (future)
   - Centralized environment variable management

5. **Docs** (`docs/`) – Comprehensive documentation:
   - Architecture, deployment guides, API documentation
   - Feature-specific documentation
   - Roadmap and planning documents

## 2. Request Flow (high level)

```
User browser/app → Guardrails layer (prompt templating, filters)
                  → theory-engine-api (FastAPI)
                    → Domain routers (bets/crypto/stocks/playlist)
                      → Data loaders (Redis/Postgres/3rd-party APIs)
                        → Guarded LLM call (OpenAI today, custom later)
                  ← Response object ("Card" + data provenance)
```

Key traits:
- Every request is tagged with domain + risk class before an LLM call.
- All theory submissions are stored anonymized for later training/graders.
- Outputs follow a shared “Card” schema so any frontend can render it.

## 3. Data + Storage

- **Primary DB**: Postgres (Supabase-compatible) for users, theories, run metadata.
- **Cache**: Redis for YouTube search results, sports odds snapshots, price data.
- **Object Storage**: S3-compatible bucket on Hetzner for large datasets + logs.
- **Secrets**: 1Password → Hetzner Secrets or Doppler (TBD) injected at deploy time.

### Data Privacy

- **No PII stored**: Only anonymous user IDs and subscription tiers.
- **Opt-in model improvement**: Users can explicitly allow anonymized data for aggregated analytics.
- **Theory text**: Stored as-is (no PII extraction). Future: embeddings-only storage option.

See `docs/DATA_PRIVACY.md` for full privacy model.

## 4. Deploy Strategy (Hetzner)

1. Build Docker images for each app/service with shared base images.
2. Use docker-compose for single-node dev/staging; promote to Kubernetes (optional) when multiple nodes/auto-scaling are needed.
3. Terminate TLS on Traefik and route subdomains (`bets.dock108.ai`, etc.) to the relevant frontend containers. All hit the same backend service via internal networking.

### Subdomain Routing (via Traefik)

- `dock108.ai` → Main landing portal (`dock108-web`)
- `highlights.dock108.ai` → Sports highlights (`highlights-web`)
- `bets.dock108.ai` → Sports betting theory (`theory-bets-web`)
- `crypto.dock108.ai` → Crypto strategy interpreter (`theory-crypto-web`)
- `stocks.dock108.ai` → Stock analysis (`theory-stocks-web`)
- `conspiracies.dock108.ai` → Conspiracy fact-checking (`conspiracy-web`)
- `game.dock108.ai` → AI prompting game (`prompt-game-web`)
- `playlist.dock108.ai` → Legacy playlist curator (`playlist-web`)
- `api.dock108.ai` → Theory engine API (internal routing)

All subdomains route through Traefik with automatic Let's Encrypt SSL certificates.

See [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) for deployment instructions.

## 5. Environments

- **Local Development**:
  - Infrastructure: `cd infra && ./docker-compose.sh up -d postgres redis`
  - Backend: `cd services/theory-engine-api && uv run uvicorn app.main:app --reload`
  - Frontend: `cd apps/<app-name> && pnpm dev`
  - Workers: `cd services/data-workers && uv run celery -A app.main.app worker`
  - Scraper: `cd services/theory-bets-scraper && uv run celery -A bets_scraper.celery_app.app worker`

- **Staging** – Hetzner CX or AX machine mirroring production, nightly data worker runs.

- **Production** – Full stack deployment via Docker Compose:
  - Traefik reverse proxy with automatic SSL
  - All frontend apps and backend services containerized
  - PostgreSQL and Redis for data and caching
  - Celery workers for async tasks
  - Centralized environment variable management via root `.env`

## 6. Next Milestones

- Bootstrap FastAPI project + shared Pydantic schemas.
- Add Redis/Postgres containers to `infra/docker` and wire playlist app to the API stub.
- Define CI (GitHub Actions) to lint/test apps + services before packaging Docker images.

## 7. Tooling & Workspaces

- **JavaScript/TypeScript**: Root `pnpm-workspace.yaml` treats `apps/*` + `packages/*` as workspaces. Run `pnpm install` once, then `pnpm --filter apps/playlist-web dev` (etc.) for per-app servers. `eslint.config.mjs` + `.prettierrc.json` keep the fleet aligned.
- **Python**: Each service (`services/theory-engine-api`) and shared lib (`packages/py-core`) ships its own `pyproject.toml` managed via `uv`. Use `uv sync` inside those folders, or `uvx <tool>` from the repo root for ad-hoc commands.
- **Quality Gates**: `Makefile` exposes `make lint`, `make test`, `make dev`, and `make fmt`:
  - `make lint` → pnpm lint + `ruff`/`black --check`.
  - `make test` → pnpm recursive tests + placeholder `pytest`.
  - `make dev` → parallel pnpm dev servers (filter per app as needed).
- **Guardrails**: Ruff config (`ruff.toml`) + Black settings (`pyproject.toml`) enforce consistent Python style; JS relies on ESLint + Prettier. All tooling runs in CI before Docker builds.
