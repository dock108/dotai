FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY services/data-workers/pyproject.toml services/data-workers/README.md ./
COPY packages/py-core/pyproject.toml ../packages/py-core/

# Install dependencies (including Celery)
RUN uv pip install --system -e . && \
    uv pip install --system -e ../packages/py-core && \
    uv pip install --system celery redis

# Copy application code
COPY services/data-workers/ ./services/data-workers/
COPY packages/py-core/ ./packages/py-core/

# Set working directory to service
WORKDIR /app/services/data-workers

# Run Celery worker
CMD ["celery", "-A", "app", "worker", "--loglevel=info"]

