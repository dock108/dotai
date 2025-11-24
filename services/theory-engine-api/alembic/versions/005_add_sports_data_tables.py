"""add sports data tables

Revision ID: 005_add_sports_data_tables
Revises: 004_add_strategy_tables
Create Date: 2025-11-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "005_add_sports_data_tables"
down_revision: Union[str, None] = "004_add_strategy_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sports_leagues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_sports_leagues_code", "sports_leagues", ["code"], unique=True)

    leagues_table = table(
        "sports_leagues",
        column("id", sa.Integer()),
        column("code", sa.String()),
        column("name", sa.String()),
        column("level", sa.String()),
    )
    op.bulk_insert(
        leagues_table,
        [
            {"id": 1, "code": "NBA", "name": "National Basketball Association", "level": "pro"},
            {"id": 2, "code": "NFL", "name": "National Football League", "level": "pro"},
            {"id": 3, "code": "NCAAF", "name": "NCAA Football", "level": "college"},
            {"id": 4, "code": "NCAAB", "name": "NCAA Basketball", "level": "college"},
            {"id": 5, "code": "MLB", "name": "Major League Baseball", "level": "pro"},
            {"id": 6, "code": "NHL", "name": "National Hockey League", "level": "pro"},
        ],
    )
    op.execute("SELECT setval('sports_leagues_id_seq', (SELECT MAX(id) FROM sports_leagues))")

    op.create_table(
        "sports_teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("external_ref", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("short_name", sa.String(length=100), nullable=False),
        sa.Column("abbreviation", sa.String(length=20), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("external_codes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["league_id"], ["sports_leagues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sports_teams_league", "sports_teams", ["league_id"], unique=False)
    op.create_index("idx_sports_teams_league_abbr", "sports_teams", ["league_id", "abbreviation"], unique=True)

    op.create_table(
        "sports_games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("season_type", sa.String(length=50), nullable=False),
        sa.Column("game_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("venue", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("source_game_key", sa.String(length=100), nullable=True),
        sa.Column("scrape_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_ids", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["away_team_id"], ["sports_teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["home_team_id"], ["sports_teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["league_id"], ["sports_leagues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("league_id", "season", "game_date", "home_team_id", "away_team_id", name="uq_game_identity"),
        sa.UniqueConstraint("source_game_key", name="uq_sports_game_source_key"),
    )
    op.create_index("idx_games_league_season_date", "sports_games", ["league_id", "season", "game_date"], unique=False)
    op.create_index("idx_games_teams", "sports_games", ["home_team_id", "away_team_id"], unique=False)

    op.create_table(
        "sports_team_boxscores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("is_home", sa.Boolean(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("rebounds", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("turnovers", sa.Integer(), nullable=True),
        sa.Column("passing_yards", sa.Integer(), nullable=True),
        sa.Column("rushing_yards", sa.Integer(), nullable=True),
        sa.Column("receiving_yards", sa.Integer(), nullable=True),
        sa.Column("hits", sa.Integer(), nullable=True),
        sa.Column("runs", sa.Integer(), nullable=True),
        sa.Column("errors", sa.Integer(), nullable=True),
        sa.Column("shots_on_goal", sa.Integer(), nullable=True),
        sa.Column("penalty_minutes", sa.Integer(), nullable=True),
        sa.Column("raw_stats_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["sports_games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["sports_teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "team_id", name="uq_team_boxscore_game_team"),
    )
    op.create_index("ix_team_boxscores_game", "sports_team_boxscores", ["game_id"], unique=False)

    op.create_table(
        "sports_player_boxscores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("player_external_ref", sa.String(length=100), nullable=False),
        sa.Column("player_name", sa.String(length=200), nullable=False),
        sa.Column("minutes", sa.Float(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("rebounds", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("yards", sa.Integer(), nullable=True),
        sa.Column("touchdowns", sa.Integer(), nullable=True),
        sa.Column("shots_on_goal", sa.Integer(), nullable=True),
        sa.Column("penalties", sa.Integer(), nullable=True),
        sa.Column("raw_stats_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["sports_games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["sports_teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "team_id", "player_external_ref", name="uq_player_boxscore_identity"),
    )
    op.create_index("ix_player_boxscores_game", "sports_player_boxscores", ["game_id"], unique=False)

    op.create_table(
        "sports_game_odds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("book", sa.String(length=50), nullable=False),
        sa.Column("market_type", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=20), nullable=True),
        sa.Column("line", sa.Float(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("is_closing_line", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_key", sa.String(length=100), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["sports_games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_sports_odds_identity", "sports_game_odds", ["game_id", "book", "market_type", "is_closing_line"], unique=False)

    op.create_table(
        "sports_scrape_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scraper_type", sa.String(length=50), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.Integer(), nullable=True),
        sa.Column("season_type", sa.String(length=50), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(length=200), nullable=True),
        sa.Column("job_id", sa.String(length=100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["league_id"], ["sports_leagues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scrape_runs_league_status", "sports_scrape_runs", ["league_id", "status"], unique=False)
    op.create_index("idx_scrape_runs_created", "sports_scrape_runs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_scrape_runs_created", table_name="sports_scrape_runs")
    op.drop_index("idx_scrape_runs_league_status", table_name="sports_scrape_runs")
    op.drop_table("sports_scrape_runs")

    op.drop_index("idx_sports_odds_identity", table_name="sports_game_odds")
    op.drop_table("sports_game_odds")

    op.drop_index("ix_player_boxscores_game", table_name="sports_player_boxscores")
    op.drop_table("sports_player_boxscores")

    op.drop_index("ix_team_boxscores_game", table_name="sports_team_boxscores")
    op.drop_table("sports_team_boxscores")

    op.drop_index("idx_games_teams", table_name="sports_games")
    op.drop_index("idx_games_league_season_date", table_name="sports_games")
    op.drop_table("sports_games")

    op.drop_index("idx_sports_teams_league_abbr", table_name="sports_teams")
    op.drop_index("ix_sports_teams_league", table_name="sports_teams")
    op.drop_table("sports_teams")

    op.drop_index("ix_sports_leagues_code", table_name="sports_leagues")
    op.drop_table("sports_leagues")

