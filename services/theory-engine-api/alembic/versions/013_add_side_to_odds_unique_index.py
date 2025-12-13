"""Add side to sports_game_odds unique index and widen side column."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "013_add_side_to_odds_unique_index"
down_revision: str | None = "012_add_theory_run_table"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    # Remove exact duplicates (same game/book/market/is_closing/side), keep latest id
    op.execute(
        """
        DELETE FROM sports_game_odds a
        USING sports_game_odds b
        WHERE a.id < b.id
          AND a.game_id = b.game_id
          AND a.book = b.book
          AND a.market_type = b.market_type
          AND a.is_closing_line = b.is_closing_line
          AND COALESCE(a.side, '') = COALESCE(b.side, '')
        """
    )

    # Drop old index and widen side column
    op.drop_index("uq_sports_game_odds_identity", table_name="sports_game_odds")
    op.alter_column("sports_game_odds", "side", type_=sa.String(length=50))

    # Add new unique index including side
    op.create_index(
        "uq_sports_game_odds_identity",
        "sports_game_odds",
        ["game_id", "book", "market_type", "side", "is_closing_line"],
        unique=True,
    )


def downgrade() -> None:
    # Revert to previous index/column size (may truncate longer side values)
    op.drop_index("uq_sports_game_odds_identity", table_name="sports_game_odds")
    op.alter_column("sports_game_odds", "side", type_=sa.String(length=20))
    op.create_index(
        "uq_sports_game_odds_identity",
        "sports_game_odds",
        ["game_id", "book", "market_type", "is_closing_line"],
        unique=True,
    )

