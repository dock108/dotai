"""add team name index

Revision ID: 006_add_team_name_index
Revises: 005_add_sports_data_tables
Create Date: 2025-11-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "006_add_team_name_index"
down_revision: Union[str, None] = "005_add_sports_data_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index on (league_id, lower(name)) for faster team name lookups
    op.create_index(
        "idx_sports_teams_league_name_lower",
        "sports_teams",
        [sa.text("league_id"), sa.text("lower(name)")],
    )


def downgrade() -> None:
    op.drop_index("idx_sports_teams_league_name_lower", table_name="sports_teams")

