# Multi-stage build for theory-bets-web Next.js app
# Uses standalone output for minimal production image

FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace configuration
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/theory-bets-web/package.json ./apps/theory-bets-web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/ui-kit/package.json ./packages/ui-kit/
COPY packages/js-core/package.json ./packages/js-core/

# Install pnpm and dependencies
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy source code
COPY apps/theory-bets-web ./apps/theory-bets-web
COPY packages/ui ./packages/ui
COPY packages/ui-kit ./packages/ui-kit
COPY packages/js-core ./packages/js-core

# Build (creates .next/standalone with everything bundled)
WORKDIR /app/apps/theory-bets-web

# NEXT_PUBLIC_* vars must be set at build time (embedded in client JS)
# Passed from docker-compose.yml which reads from root .env
ARG NEXT_PUBLIC_THEORY_ENGINE_URL
ENV NEXT_PUBLIC_THEORY_ENGINE_URL=${NEXT_PUBLIC_THEORY_ENGINE_URL}

RUN mkdir -p public && pnpm build

# Production image - minimal, no package manager needed
FROM node:20-alpine

WORKDIR /app

# Copy standalone output (preserves monorepo structure)
COPY --from=builder /app/apps/theory-bets-web/.next/standalone ./
# Copy static assets (not included in standalone)
COPY --from=builder /app/apps/theory-bets-web/.next/static ./apps/theory-bets-web/.next/static
# Copy public assets
COPY --from=builder /app/apps/theory-bets-web/public ./apps/theory-bets-web/public

WORKDIR /app/apps/theory-bets-web

EXPOSE 3001
ENV PORT=3001
ENV HOSTNAME="0.0.0.0"

# Single command - no npm/pnpm needed
CMD ["node", "server.js"]
