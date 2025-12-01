FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY services/theory-crypto-worker/pyproject.toml ./services/theory-crypto-worker/
COPY services/theory-engine-api/pyproject.toml ./services/theory-engine-api/
COPY packages/py-core/pyproject.toml ./packages/py-core/

# Install dependencies (including Celery and ccxt for free exchange data)
RUN uv pip install --system -e ./services/theory-crypto-worker && \
    uv pip install --system -e ./services/theory-engine-api && \
    uv pip install --system -e ./packages/py-core && \
    uv pip install --system celery redis psycopg[binary] ccxt

# Copy application code (worker needs theory-engine-api for db_models)
COPY services/theory-crypto-worker/ ./services/theory-crypto-worker/
COPY services/theory-engine-api/ ./services/theory-engine-api/
COPY packages/py-core/ ./packages/py-core/

# Set working directory to service
WORKDIR /app/services/theory-crypto-worker

# Run Celery worker for crypto ingestion
CMD ["celery", "-A", "crypto_worker.tasks.app", "worker", "--loglevel=info", "--queues=crypto-worker"]


