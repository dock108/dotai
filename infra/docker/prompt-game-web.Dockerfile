# Multi-stage build for prompt-game-web Next.js app
FROM node:20-alpine AS builder

WORKDIR /app

# Copy workspace configuration and package manifests
# This enables pnpm workspace resolution for shared packages
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY tsconfig.json ./tsconfig.json
COPY apps/prompt-game-web/package.json ./apps/prompt-game-web/
COPY packages/ui/package.json ./packages/ui/
COPY packages/ui-kit/package.json ./packages/ui-kit/

# Install pnpm package manager
RUN npm install -g pnpm

# Copy application source code
COPY apps/prompt-game-web ./apps/prompt-game-web
COPY packages/ui ./packages/ui
COPY packages/ui-kit ./packages/ui-kit

# Install all dependencies (including workspace dependencies).
# Run after sources are copied to ensure workspace linking is correct.
RUN pnpm install --frozen-lockfile

# Build the Next.js application
WORKDIR /app/apps/prompt-game-web
RUN pnpm build

# Production runtime image - minimal footprint
FROM node:20-alpine

WORKDIR /app

# Copy built Next.js output and configuration
COPY --from=builder /app/apps/prompt-game-web/.next ./.next
COPY --from=builder /app/apps/prompt-game-web/public ./public
COPY --from=builder /app/apps/prompt-game-web/package.json ./
COPY --from=builder /app/apps/prompt-game-web/next.config.ts ./
COPY --from=builder /app/apps/prompt-game-web/node_modules ./node_modules

# Expose port 3000 (matches docker-compose.yml service configuration)
EXPOSE 3000

# Start Next.js production server
CMD ["pnpm", "start", "--", "-p", "3000"]

