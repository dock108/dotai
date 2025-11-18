FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/theory-conspiracy-web/package.json ./apps/theory-conspiracy-web/
COPY packages/ui-kit/package.json ./packages/ui-kit/

# Install pnpm
RUN npm install -g pnpm

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source code
COPY apps/theory-conspiracy-web ./apps/theory-conspiracy-web
COPY packages/ui-kit ./packages/ui-kit

# Build the app
WORKDIR /app/apps/theory-conspiracy-web
RUN pnpm build

# Production image
FROM node:20-alpine

WORKDIR /app

# Copy built files
COPY --from=builder /app/apps/theory-conspiracy-web/.next ./.next
COPY --from=builder /app/apps/theory-conspiracy-web/public ./public
COPY --from=builder /app/apps/theory-conspiracy-web/package.json ./
COPY --from=builder /app/apps/theory-conspiracy-web/next.config.ts ./

# Install production dependencies only
RUN npm install -g pnpm && \
    pnpm install --prod --frozen-lockfile

EXPOSE 3004

CMD ["pnpm", "start", "--", "-p", "3004"]

