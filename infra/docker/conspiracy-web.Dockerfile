# Multi-stage build for conspiracy-web Next.js app
FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace configuration and package manifests
# This enables pnpm workspace resolution for shared packages
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY tsconfig.json ./tsconfig.json
COPY apps/conspiracy-web/package.json ./apps/conspiracy-web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/ui-kit/package.json ./packages/ui-kit/
COPY packages/js-core/package.json ./packages/js-core/

# Install pnpm package manager
RUN npm install -g pnpm

# Copy application source code
COPY apps/conspiracy-web ./apps/conspiracy-web
COPY packages/ui ./packages/ui
COPY packages/ui-kit ./packages/ui-kit
COPY packages/js-core ./packages/js-core

# Install all dependencies (including workspace dependencies).
# Run after sources are copied to ensure workspace linking is correct.
RUN pnpm install --frozen-lockfile

# Build the Next.js application
WORKDIR /app/apps/conspiracy-web
RUN pnpm build

# Production runtime image - minimal footprint
FROM node:20-alpine

WORKDIR /app

# Copy built Next.js output and configuration
COPY --from=builder /app/apps/conspiracy-web/.next ./.next
COPY --from=builder /app/apps/conspiracy-web/public ./public
COPY --from=builder /app/apps/conspiracy-web/package.json ./
COPY --from=builder /app/apps/conspiracy-web/next.config.ts ./
COPY --from=builder /app/apps/conspiracy-web/node_modules ./node_modules

# Expose port 3004 (matches docker-compose.yml service configuration)
EXPOSE 3004

# Start Next.js production server
CMD ["pnpm", "start", "--", "-p", "3004"]

