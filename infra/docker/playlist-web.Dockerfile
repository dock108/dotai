# Multi-stage build for playlist-web Next.js app
FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace configuration and package manifests
# This enables pnpm workspace resolution for shared packages
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/playlist-web/package.json ./apps/playlist-web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/ui-kit/package.json ./packages/ui-kit/

# Install pnpm package manager
RUN npm install -g pnpm

# Install all dependencies (including workspace dependencies)
RUN pnpm install --frozen-lockfile

# Copy application source code
COPY apps/playlist-web ./apps/playlist-web
COPY packages/ui ./packages/ui
COPY packages/ui-kit ./packages/ui-kit

# Build the Next.js application
WORKDIR /app/apps/playlist-web
RUN pnpm build

# Production runtime image - minimal footprint
FROM node:20-alpine

WORKDIR /app

# Copy built Next.js output and configuration
COPY --from=builder /app/apps/playlist-web/.next ./.next
COPY --from=builder /app/apps/playlist-web/public ./public
COPY --from=builder /app/apps/playlist-web/package.json ./
COPY --from=builder /app/apps/playlist-web/next.config.ts ./

# Install only production dependencies
RUN npm install -g pnpm && \
    pnpm install --prod --frozen-lockfile

# Expose port 3002 (matches docker-compose.yml service configuration)
EXPOSE 3002

# Start Next.js production server
CMD ["pnpm", "start", "--", "-p", "3002"]

