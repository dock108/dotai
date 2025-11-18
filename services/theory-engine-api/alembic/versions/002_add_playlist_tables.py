"""add_playlist_tables

Revision ID: 002_add_playlist_tables
Revises: 
Create Date: 2024-11-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_add_playlist_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create playlist_queries table
    op.create_table(
        'playlist_queries',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('normalized_signature', sa.String(length=64), nullable=False),
        sa.Column('mode', sa.String(length=30), nullable=False),
        sa.Column('requested_duration_minutes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_queries_signature_mode', 'playlist_queries', ['normalized_signature', 'mode'], unique=False)
    op.create_index('idx_queries_created', 'playlist_queries', ['created_at'], unique=False)
    op.create_index(op.f('ix_playlist_queries_normalized_signature'), 'playlist_queries', ['normalized_signature'], unique=False)
    op.create_index(op.f('ix_playlist_queries_mode'), 'playlist_queries', ['mode'], unique=False)

    # Create playlists table
    op.create_table(
        'playlists',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('query_id', sa.BigInteger(), nullable=False),
        sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('total_duration_seconds', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('stale_after', sa.DateTime(timezone=True), nullable=True),
        sa.Column('explanation', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['query_id'], ['playlist_queries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_playlists_stale_after', 'playlists', ['stale_after'], unique=False)
    op.create_index('idx_playlists_query_created', 'playlists', ['query_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_playlists_query_id'), 'playlists', ['query_id'], unique=False)

    # Create videos table
    op.create_table(
        'videos',
        sa.Column('video_id', sa.String(length=20), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('channel_id', sa.String(length=50), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_sports_highlight', sa.Boolean(), nullable=True),
        sa.Column('last_refreshed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('video_id')
    )
    op.create_index('idx_videos_channel_published', 'videos', ['channel_id', 'published_at'], unique=False)
    op.create_index('idx_videos_sports_highlight', 'videos', ['is_sports_highlight'], unique=False)
    op.create_index(op.f('ix_videos_channel_id'), 'videos', ['channel_id'], unique=False)
    op.create_index(op.f('ix_videos_published_at'), 'videos', ['published_at'], unique=False)


def downgrade() -> None:
    # Drop videos table
    op.drop_index(op.f('ix_videos_published_at'), table_name='videos')
    op.drop_index(op.f('ix_videos_channel_id'), table_name='videos')
    op.drop_index('idx_videos_sports_highlight', table_name='videos')
    op.drop_index('idx_videos_channel_published', table_name='videos')
    op.drop_table('videos')

    # Drop playlists table
    op.drop_index(op.f('ix_playlists_query_id'), table_name='playlists')
    op.drop_index('idx_playlists_query_created', table_name='playlists')
    op.drop_index('idx_playlists_stale_after', table_name='playlists')
    op.drop_table('playlists')

    # Drop playlist_queries table
    op.drop_index(op.f('ix_playlist_queries_mode'), table_name='playlist_queries')
    op.drop_index(op.f('ix_playlist_queries_normalized_signature'), table_name='playlist_queries')
    op.drop_index('idx_queries_created', table_name='playlist_queries')
    op.drop_index('idx_queries_signature_mode', table_name='playlist_queries')
    op.drop_table('playlist_queries')

