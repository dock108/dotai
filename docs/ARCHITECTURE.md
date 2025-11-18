# dock108 Architecture Overview

## 0. Vision Snapshot

Dock108 hosts a family of “theory surfaces” (bets, crypto, stocks, conspiracies, playlists) and a prompting game. Every surface connects to the same Python theory engine, data workers, and guardrails before any LLM call. Frontends are React (Next.js) apps, with the existing Swift game living alongside them until the React port lands.

## 1. Monorepo Layers

1. **Apps** – user-facing UIs (Next.js web apps and the Swift prototype). They share UI and client libraries housed in `packages/`.
2. **Services** – Python FastAPI `theory-engine-api` plus async/cron `data-workers` that hydrate caches (YouTube, sports odds, prices, news).
3. **Packages** – `ui-kit` (shared React components + Tailwind tokens), `js-core` (SDK, hooks, validation), `py-core` (Pydantic schemas, guardrail utilities, scoring logic).
4. **Infra** – Dockerfiles, docker-compose, Kubernetes manifests, and nginx/Traefik configs tuned for Hetzner bare metal.
5. **Docs** – canonical knowledge base for architecture, guardrails, theory scoring, and the roadmap.

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

## 4. Deploy Strategy (Hetzner)

1. Build Docker images for each app/service with shared base images.
2. Use docker-compose for single-node dev/staging; promote to Kubernetes (optional) when multiple nodes/auto-scaling are needed.
3. Terminate TLS on nginx (or Traefik) and route subdomains (`bets.dock108.ai`, etc.) to the relevant frontend containers. All hit the same backend service via internal networking.

## 5. Environments

- **Local** – `docker compose up` for API + data workers, `pnpm dev`/`npm run dev` for Apps.
- **Staging** – Hetzner CX or AX machine mirroring prod, nightly data worker runs.
- **Production** – Two-node setup (apps/services split) with managed Postgres + Redis instances. Guardrails + monitoring (Grafana/Prometheus) ship here first.

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
