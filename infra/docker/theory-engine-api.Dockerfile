FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files first (for early dependency resolution)
COPY services/theory-engine-api/pyproject.toml services/theory-engine-api/README.md ./
COPY packages/py-core/pyproject.toml packages/py-core/README.md ../packages/py-core/

# Copy application code before installing (needed for editable installs)
COPY services/theory-engine-api/ ./services/theory-engine-api/
COPY packages/py-core/ ./packages/py-core/

# Install dependencies (now that code is in place for editable installs)
# Install py-core as regular package (not editable) so it persists with volume mounts
RUN uv pip install --system -e . && \
    uv pip install --system ./packages/py-core

# Copy entrypoint script
COPY infra/docker/theory-engine-api-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set working directory to service
WORKDIR /app/services/theory-engine-api

# Expose port
EXPOSE 8000

# Run the application via entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

