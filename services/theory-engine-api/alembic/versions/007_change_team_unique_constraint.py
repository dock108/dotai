"""change team unique constraint

Revision ID: 007_change_team_unique_constraint
Revises: 006_add_team_name_index
Create Date: 2025-11-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "007_team_name_constraint"
down_revision: Union[str, None] = "006_add_team_name_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old abbreviation-based unique constraint if it exists
    # Use raw SQL with IF EXISTS to handle case where index doesn't exist
    from sqlalchemy import text
    
    connection = op.get_bind()
    
    # Drop old index if it exists (using IF EXISTS)
    op.execute(text("DROP INDEX IF EXISTS idx_sports_teams_league_abbr"))
    
    # Create new name-based unique constraint
    # Check if it already exists first to avoid errors
    result = connection.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE indexname = 'idx_sports_teams_league_name'
        )
    """))
    if not result.scalar():
        op.create_index(
            "idx_sports_teams_league_name",
            "sports_teams",
            ["league_id", "name"],
            unique=True,
        )


def downgrade() -> None:
    # Drop name-based constraint
    op.drop_index("idx_sports_teams_league_name", table_name="sports_teams")
    # Restore abbreviation-based constraint
    op.create_index(
        "idx_sports_teams_league_abbr",
        "sports_teams",
        ["league_id", "abbreviation"],
        unique=True,
    )

