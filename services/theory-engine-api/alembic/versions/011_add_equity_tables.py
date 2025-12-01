"""add equity data tables

Revision ID: 011_add_equity_tables
Revises: 010_add_crypto_tables
Create Date: 2025-12-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "011_add_equity_tables"
down_revision: Union[str, Sequence[str], None] = "010_add_crypto_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.create_table(
      "equity_exchanges",
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
  op.create_index("ix_equity_exchanges_code", "equity_exchanges", ["code"], unique=True)

  op.create_table(
      "equity_assets",
      sa.Column("id", sa.Integer(), nullable=False),
      sa.Column("exchange_id", sa.Integer(), nullable=False),
      sa.Column("ticker", sa.String(length=50), nullable=False),
      sa.Column("name", sa.String(length=200), nullable=True),
      sa.Column("sector", sa.String(length=100), nullable=True),
      sa.Column("industry", sa.String(length=150), nullable=True),
      sa.Column("external_codes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
      sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
      sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
      sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
      sa.ForeignKeyConstraint(["exchange_id"], ["equity_exchanges.id"], ondelete="CASCADE"),
      sa.PrimaryKeyConstraint("id"),
      sa.UniqueConstraint("exchange_id", "ticker", name="uq_equity_asset_exchange_ticker"),
  )
  op.create_index("ix_equity_assets_exchange", "equity_assets", ["exchange_id"], unique=False)
  op.create_index("idx_equity_assets_ticker", "equity_assets", ["ticker"], unique=False)

  op.create_table(
      "equity_candles",
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
      sa.ForeignKeyConstraint(["asset_id"], ["equity_assets.id"], ondelete="CASCADE"),
      sa.ForeignKeyConstraint(["exchange_id"], ["equity_exchanges.id"], ondelete="CASCADE"),
      sa.PrimaryKeyConstraint("id"),
      sa.UniqueConstraint("asset_id", "timeframe", "timestamp", name="uq_equity_candle_identity"),
  )
  op.create_index("ix_equity_candles_asset", "equity_candles", ["asset_id"], unique=False)
  op.create_index("idx_equity_candles_exchange_time", "equity_candles", ["exchange_id", "timeframe", "timestamp"], unique=False)

  op.create_table(
      "equity_ingestion_runs",
      sa.Column("id", sa.Integer(), nullable=False),
      sa.Column("exchange_code", sa.String(length=50), nullable=False),
      sa.Column("tickers", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
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
  op.create_index("idx_equity_ingestion_status", "equity_ingestion_runs", ["status"], unique=False)
  op.create_index("idx_equity_ingestion_created", "equity_ingestion_runs", ["created_at"], unique=False)
  op.create_index("idx_equity_ingestion_exchange_timeframe", "equity_ingestion_runs", ["exchange_code", "timeframe"], unique=False)


def downgrade() -> None:
  op.drop_index("idx_equity_ingestion_exchange_timeframe", table_name="equity_ingestion_runs")
  op.drop_index("idx_equity_ingestion_created", table_name="equity_ingestion_runs")
  op.drop_index("idx_equity_ingestion_status", table_name="equity_ingestion_runs")
  op.drop_table("equity_ingestion_runs")

  op.drop_index("idx_equity_candles_exchange_time", table_name="equity_candles")
  op.drop_index("ix_equity_candles_asset", table_name="equity_candles")
  op.drop_table("equity_candles")

  op.drop_index("idx_equity_assets_ticker", table_name="equity_assets")
  op.drop_index("ix_equity_assets_exchange", table_name="equity_assets")
  op.drop_table("equity_assets")

  op.drop_index("ix_equity_exchanges_code", table_name="equity_exchanges")
  op.drop_table("equity_exchanges")


