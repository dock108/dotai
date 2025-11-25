#!/usr/bin/env python3
"""Run database migrations."""
import asyncio
from alembic.config import Config
from alembic import command

# Load alembic config
alembic_cfg = Config("alembic.ini")

# Run migration
command.upgrade(alembic_cfg, "head")
print("✅ Migrations applied successfully")

