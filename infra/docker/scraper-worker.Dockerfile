FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy only dependency files needed for installation
COPY services/theory-bets-scraper/pyproject.toml ./
COPY services/theory-engine-api/pyproject.toml ./services/theory-engine-api/
COPY packages/py-core/pyproject.toml ./packages/py-core/

# Install dependencies (including Celery)
RUN uv pip install --system -e . && \
    uv pip install --system -e ./services/theory-engine-api && \
    uv pip install --system -e ./packages/py-core && \
    uv pip install --system celery redis psycopg[binary]

# Copy application code (scraper needs theory-engine-api for db_models)
COPY services/theory-bets-scraper/ ./services/theory-bets-scraper/
COPY services/theory-engine-api/ ./services/theory-engine-api/
COPY packages/py-core/ ./packages/py-core/

# Set working directory to service
WORKDIR /app/services/theory-bets-scraper

# Run Celery worker for scraper
CMD ["celery", "-A", "bets_scraper.celery_app.app", "worker", "--loglevel=info", "--queues=bets-scraper"]
