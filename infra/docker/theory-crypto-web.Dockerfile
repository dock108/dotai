FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/theory-crypto-web/package.json ./apps/theory-crypto-web/
COPY packages/ui-kit/package.json ./packages/ui-kit/

# Install pnpm
RUN npm install -g pnpm

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY apps/theory-crypto-web ./apps/theory-crypto-web
COPY packages/ui-kit ./packages/ui-kit

# Build the app
WORKDIR /app/apps/theory-crypto-web
RUN pnpm build

# Production image
FROM node:20-alpine

WORKDIR /app

# Copy built files
COPY --from=builder /app/apps/theory-crypto-web/.next ./.next
COPY --from=builder /app/apps/theory-crypto-web/public ./public
COPY --from=builder /app/apps/theory-crypto-web/package.json ./
COPY --from=builder /app/apps/theory-crypto-web/next.config.ts ./

# Install production dependencies only
RUN npm install -g pnpm && \
    pnpm install --prod --frozen-lockfile

EXPOSE 3002

CMD ["pnpm", "start", "--", "-p", "3002"]

