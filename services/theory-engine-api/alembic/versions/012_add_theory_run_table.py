"""add theory_runs table

Revision ID: 012_add_theory_run_table
Revises: 011_add_equity_tables
Create Date: 2025-12-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "012_add_theory_run_table"
down_revision = "011_add_equity_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "theory_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("sport", sa.String(length=20), nullable=False),
        sa.Column("theory_text", sa.Text(), nullable=False),
        sa.Column("model_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("theory_runs")

