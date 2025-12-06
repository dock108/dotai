#!/bin/bash
set -e

# Handle both Docker build structure and volume mount structure
# Volume mount: /app points to services/theory-engine-api
# Build structure: /app/services/theory-engine-api
if [ -d "/app/app" ]; then
    # Volume mount case: /app is the service root
    cd /app
    # Add service root, src for engine package, and py-core
    export PYTHONPATH=/app:/app/src:/app/packages/py-core:$PYTHONPATH
else
    # Build case: /app/services/theory-engine-api
    cd /app/services/theory-engine-api
    export PYTHONPATH=/app/services/theory-engine-api:/app/services/theory-engine-api/src:/app/packages/py-core:$PYTHONPATH
fi

# Run uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

