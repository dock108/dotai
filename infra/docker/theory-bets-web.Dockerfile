# Multi-stage build for theory-bets-web Next.js app
FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace configuration and package manifests
# This enables pnpm workspace resolution for shared packages
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/theory-bets-web/package.json ./apps/theory-bets-web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/ui-kit/package.json ./packages/ui-kit/
COPY packages/js-core/package.json ./packages/js-core/

# Install pnpm package manager
RUN npm install -g pnpm

# Install all dependencies (including workspace dependencies)
RUN pnpm install --frozen-lockfile

# Copy application source code
COPY apps/theory-bets-web ./apps/theory-bets-web
COPY packages/ui ./packages/ui
COPY packages/ui-kit ./packages/ui-kit
COPY packages/js-core ./packages/js-core

# Ensure public directory exists (Next.js requires it even if empty)
RUN mkdir -p apps/theory-bets-web/public

# Build the Next.js application
WORKDIR /app/apps/theory-bets-web
RUN pnpm build

# Production runtime image - minimal footprint
FROM node:20-alpine

WORKDIR /app

# Copy built Next.js output and configuration
COPY --from=builder /app/apps/theory-bets-web/.next ./.next
COPY --from=builder /app/apps/theory-bets-web/public ./public
COPY --from=builder /app/apps/theory-bets-web/package.json ./
COPY --from=builder /app/apps/theory-bets-web/next.config.ts ./

# Install only production dependencies
RUN npm install -g pnpm && \
    pnpm install --prod --frozen-lockfile

# Expose port 3001 (matches docker-compose.yml service configuration)
EXPOSE 3001

# Start Next.js production server
CMD ["pnpm", "start", "--", "-p", "3001"]

