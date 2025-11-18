# Roadmap

## Phase 0 (now)
- Consolidate code into this monorepo ✅
- Document architecture, guardrails, backend vision ✅
- Keep Swift AI game operational inside `apps/game-web/swift-prototype`

## Phase 1 – Shared Backend Foundations
- Bootstrap FastAPI service with playlist endpoints + health checks
- Create `packages/py-core` with shared schemas + guardrail helpers
- Add docker-compose stack (FastAPI + Postgres + Redis) for local dev
- Wire playlist Next.js app to the FastAPI proxy instead of the built-in API routes

## Phase 2 – Theory Surfaces
- Clone playlist UI patterns into `theory-bets-web`, `theory-crypto-web`, etc.
- Stand up `packages/ui-kit` and `packages/js-core` to unify components + API SDKs
- Build data workers for odds, crypto, stocks; push caches to Redis with TTLs
- Launch guardrail admin dashboard (basic) for manual review

## Phase 3 – Guardrails + Game Port
- Expand guardrail policies per domain (sports compliance, misinformation, financial advice)
- Backfill anonymized theory data into warehouse for scoring improvements
- Start React port of the AI game (`apps/game-web`), reusing shared UI + guardrail aware flows
- Introduce experiments (A/B) for card formatting across surfaces

## Phase 4 – Scale + Custom Models
- Add Kubernetes manifests + GitOps deployment pipeline for Hetzner cluster
- Train bespoke graders on collected theory data; host via `services/theory-engine-api`
- Offer API access for partners (rate limited, key-based)
- Automate onboarding for new theory domains via config-driven routers
