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

## Getting Started

1. Install `asdf` or a shared version manager for Node (for the Next.js apps) and Python (for FastAPI + workers).
2. Copy `.env.example` files that live inside each app/service.
3. Use Docker Compose under `infra/docker` (coming soon) to boot Hetzner-like environments locally.

## Next Steps

- Flesh out `services/theory-engine-api` (FastAPI) and `services/data-workers` (ETL jobs for odds/prices/YouTube caching).
- Stand up the shared packages (`ui-kit`, `js-core`, `py-core`) once interfaces settle.
- Replace the Swift prototype with a shared React experience once the guardrails + backend are ready.
- Document deployment runbooks in `infra/` once Hetzner stack is scripted.
