"""add_strategy_tables

Revision ID: 004_add_strategy_tables
Revises: 003_add_playlist_metadata
Create Date: 2024-12-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_add_strategy_tables'
down_revision: Union[str, None] = '003_add_playlist_metadata'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create strategies table
    op.create_table(
        'strategies',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('idea_text', sa.Text(), nullable=False),
        sa.Column('interpretation', sa.Text(), nullable=False),
        sa.Column('strategy_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('backtest_blueprint', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('diagnostics', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('alerts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('alerts_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_strategies_user_id', 'strategies', ['user_id'], unique=False)
    op.create_index('idx_strategies_user_created', 'strategies', ['user_id', 'created_at'], unique=False)
    op.create_index('idx_strategies_status', 'strategies', ['status'], unique=False)

    # Create backtests table
    op.create_table(
        'backtests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('strategy_id', sa.String(length=36), nullable=False),
        sa.Column('results_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_backtests_strategy_id', 'backtests', ['strategy_id'], unique=False)
    op.create_index('idx_backtests_strategy_created', 'backtests', ['strategy_id', 'created_at'], unique=False)

    # Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('strategy_id', sa.String(length=36), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alerts_strategy_id', 'alerts', ['strategy_id'], unique=False)
    op.create_index('idx_alerts_strategy_triggered', 'alerts', ['strategy_id', 'triggered_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_alerts_strategy_triggered', table_name='alerts')
    op.drop_index('ix_alerts_strategy_id', table_name='alerts')
    op.drop_index('idx_backtests_strategy_created', table_name='backtests')
    op.drop_index('ix_backtests_strategy_id', table_name='backtests')
    op.drop_index('idx_strategies_status', table_name='strategies')
    op.drop_index('idx_strategies_user_created', table_name='strategies')
    op.drop_index('ix_strategies_user_id', table_name='strategies')

    # Drop tables
    op.drop_table('alerts')
    op.drop_table('backtests')
    op.drop_table('strategies')

