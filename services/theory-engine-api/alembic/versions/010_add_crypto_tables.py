"""add crypto data tables

Revision ID: 010_add_crypto_tables
Revises: 009_add_sports_game_odds_identity
Create Date: 2025-12-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "010_add_crypto_tables"
down_revision: Union[str, Sequence[str], None] = "009_add_sports_game_odds_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crypto_exchanges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_crypto_exchanges_code", "crypto_exchanges", ["code"], unique=True)

    op.create_table(
        "crypto_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("base", sa.String(length=50), nullable=True),
        sa.Column("quote", sa.String(length=50), nullable=True),
        sa.Column("external_codes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["exchange_id"], ["crypto_exchanges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exchange_id", "symbol", name="uq_crypto_asset_exchange_symbol"),
    )
    op.create_index("ix_crypto_assets_exchange", "crypto_assets", ["exchange_id"], unique=False)
    op.create_index("idx_crypto_assets_symbol", "crypto_assets", ["symbol"], unique=False)

    op.create_table(
        "crypto_candles",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["crypto_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exchange_id"], ["crypto_exchanges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "timeframe", "timestamp", name="uq_crypto_candle_identity"),
    )
    op.create_index("ix_crypto_candles_asset", "crypto_candles", ["asset_id"], unique=False)
    op.create_index("idx_crypto_candles_exchange_time", "crypto_candles", ["exchange_id", "timeframe", "timestamp"], unique=False)

    op.create_table(
        "crypto_ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange_code", sa.String(length=50), nullable=False),
        sa.Column("symbols", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("timeframe", sa.String(length=10), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(length=200), nullable=True),
        sa.Column("job_id", sa.String(length=100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_crypto_ingestion_status", "crypto_ingestion_runs", ["status"], unique=False)
    op.create_index("idx_crypto_ingestion_created", "crypto_ingestion_runs", ["created_at"], unique=False)
    op.create_index("idx_crypto_ingestion_exchange_timeframe", "crypto_ingestion_runs", ["exchange_code", "timeframe"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_crypto_ingestion_exchange_timeframe", table_name="crypto_ingestion_runs")
    op.drop_index("idx_crypto_ingestion_created", table_name="crypto_ingestion_runs")
    op.drop_index("idx_crypto_ingestion_status", table_name="crypto_ingestion_runs")
    op.drop_table("crypto_ingestion_runs")

    op.drop_index("idx_crypto_candles_exchange_time", table_name="crypto_candles")
    op.drop_index("ix_crypto_candles_asset", table_name="crypto_candles")
    op.drop_table("crypto_candles")

    op.drop_index("idx_crypto_assets_symbol", table_name="crypto_assets")
    op.drop_index("ix_crypto_assets_exchange", table_name="crypto_assets")
    op.drop_table("crypto_assets")

    op.drop_index("ix_crypto_exchanges_code", table_name="crypto_exchanges")
    op.drop_table("crypto_exchanges")


