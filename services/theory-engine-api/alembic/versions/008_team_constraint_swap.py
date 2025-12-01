"""swap sports team unique constraint

Revision ID: 008_team_constraint_swap
Revises: 007_team_name_constraint
Create Date: 2025-11-30 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_team_constraint_swap"
down_revision: Union[str, None] = "007_team_name_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE sports_teams DROP CONSTRAINT IF EXISTS sports_teams_league_abbr_unique")
    op.execute("ALTER TABLE sports_teams ADD CONSTRAINT sports_teams_league_name_unique UNIQUE (league_id, name)")


def downgrade() -> None:
    op.execute("ALTER TABLE sports_teams DROP CONSTRAINT IF EXISTS sports_teams_league_name_unique")
    op.execute("ALTER TABLE sports_teams ADD CONSTRAINT sports_teams_league_abbr_unique UNIQUE (league_id, abbreviation)")

