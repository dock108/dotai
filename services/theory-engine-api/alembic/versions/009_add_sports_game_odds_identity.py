"""add unique index for sports_game_odds identity

Revision ID: 009_add_sports_game_odds_identity
Revises: 008_team_constraint_swap
Create Date: 2025-11-30 18:25:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "009_add_sports_game_odds_identity"
down_revision: Union[str, Sequence[str], None] = "008_team_constraint_swap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_sports_odds_identity", table_name="sports_game_odds")
    op.create_index(
        "uq_sports_game_odds_identity",
        "sports_game_odds",
        ["game_id", "book", "market_type", "is_closing_line"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_sports_game_odds_identity", table_name="sports_game_odds")
    op.create_index(
        "idx_sports_odds_identity",
        "sports_game_odds",
        ["game_id", "book", "market_type", "is_closing_line"],
        unique=False,
    )

