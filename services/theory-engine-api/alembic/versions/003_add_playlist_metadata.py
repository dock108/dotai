"""add_playlist_metadata

Revision ID: 003_add_playlist_metadata
Revises: 002_add_playlist_tables
Create Date: 2024-11-18 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_add_playlist_metadata'
down_revision: Union[str, None] = '002_add_playlist_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add metadata fields to playlist_queries table for future integration with betting util / theory engine
    op.add_column('playlist_queries', sa.Column('sport', sa.String(length=50), nullable=True))
    op.add_column('playlist_queries', sa.Column('league', sa.String(length=100), nullable=True))
    op.add_column('playlist_queries', sa.Column('teams', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('playlist_queries', sa.Column('event_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('playlist_queries', sa.Column('is_playoff', sa.Boolean(), nullable=True))
    
    # Create indexes for efficient querying
    op.create_index('ix_playlist_queries_sport', 'playlist_queries', ['sport'], unique=False)
    op.create_index('ix_playlist_queries_event_date', 'playlist_queries', ['event_date'], unique=False)
    op.create_index('idx_queries_sport_event', 'playlist_queries', ['sport', 'event_date'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_queries_sport_event', table_name='playlist_queries')
    op.drop_index('ix_playlist_queries_event_date', table_name='playlist_queries')
    op.drop_index('ix_playlist_queries_sport', table_name='playlist_queries')
    
    # Drop columns
    op.drop_column('playlist_queries', 'is_playoff')
    op.drop_column('playlist_queries', 'event_date')
    op.drop_column('playlist_queries', 'teams')
    op.drop_column('playlist_queries', 'league')
    op.drop_column('playlist_queries', 'sport')

