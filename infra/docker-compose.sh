#!/bin/bash
# Wrapper script to run docker-compose with the root .env file

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Run docker-compose with the root .env file
docker compose --env-file "$ROOT_DIR/.env" "$@"

