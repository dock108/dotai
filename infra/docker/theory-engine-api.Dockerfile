FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY services/theory-engine-api/pyproject.toml services/theory-engine-api/README.md ./
COPY packages/py-core/pyproject.toml ../packages/py-core/

# Install dependencies
RUN uv pip install --system -e . && \
    uv pip install --system -e ../packages/py-core

# Copy application code
COPY services/theory-engine-api/ ./services/theory-engine-api/
COPY packages/py-core/ ./packages/py-core/

# Set working directory to service
WORKDIR /app/services/theory-engine-api

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

