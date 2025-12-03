#!/bin/bash
# Wrapper script to run docker-compose with the root .env file
# This ensures all passwords and configuration are loaded from .env (single source of truth)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Change to infra directory for docker-compose.yml
cd "$SCRIPT_DIR"

# Run docker-compose with the root .env file for variable substitution
# Use docker-compose (v1) or docker compose (v2) - try both
if command -v docker-compose &> /dev/null; then
    docker-compose --env-file "$ROOT_DIR/.env" -f docker-compose.yml "$@"
elif docker compose version &> /dev/null; then
    docker compose --env-file "$ROOT_DIR/.env" -f docker-compose.yml "$@"
else
    echo "Error: docker-compose not found. Please install Docker Compose." >&2
    exit 1
fi

