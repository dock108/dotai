"""NCAA basketball scraper using sports-reference.com/cbb."""

from __future__ import annotations

from datetime import date, datetime
from typing import Sequence
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import GameIdentification, NormalizedGame, NormalizedTeamBoxscore, TeamIdentity
from ..normalization import normalize_team_name
from ..utils.parsing import parse_int
from .base import BaseSportsReferenceScraper, ScraperError


class NCAABSportsReferenceScraper(BaseSportsReferenceScraper):
    sport = "ncaab"
    league_code = "NCAAB"
    base_url = "https://www.sports-reference.com/cbb/boxscores/"

    def _parse_team_row(self, row) -> tuple[TeamIdentity, int]:
        # NCAAB uses last td for score instead of class="right"
        team_link = row.find("a")
        if not team_link:
            raise ScraperError("Missing team link")
        team_name = team_link.text.strip()
        canonical_name, abbreviation = normalize_team_name(self.league_code, team_name)
        score_cell = row.find_all("td")[-1]
        if score_cell is None:
            raise ScraperError("Missing score cell")
        score = parse_int(score_cell.text.strip())
        if score is None:
            raise ScraperError(f"Invalid score: {score_cell.text.strip()}")
        identity = TeamIdentity(
            league_code=self.league_code,
            name=canonical_name,
            short_name=canonical_name,
            abbreviation=abbreviation,
            external_ref=abbreviation.upper(),
        )
        return identity, score

    def _extract_team_stats(self, soup: BeautifulSoup, team_abbr: str) -> dict:
        """Extract team stats from boxscore table."""
        from ..utils.html_parsing import extract_team_stats_from_table, find_table_by_id
        
        table_id = f"box-{team_abbr.lower()}-game-basic"
        table = find_table_by_id(soup, table_id)
        if not table:
            return {}
        return extract_team_stats_from_table(table, team_abbr, table_id)

    def _build_team_boxscore(self, identity: TeamIdentity, is_home: bool, score: int, stats: dict) -> NormalizedTeamBoxscore:
        return NormalizedTeamBoxscore(
            team=identity,
            is_home=is_home,
            points=score,
            rebounds=parse_int(stats.get("trb")),
            assists=parse_int(stats.get("ast")),
            turnovers=parse_int(stats.get("tov")),
            raw_stats=stats,
        )

    # _season_from_date now inherited from base class

    def fetch_games_for_date(self, day: date) -> Sequence[NormalizedGame]:
        soup = self.fetch_html(self.scoreboard_url(day))
        game_divs = soup.select("div.game_summary")
        games: list[NormalizedGame] = []
        for div in game_divs:
            team_rows = div.select("table.teams tr")
            if len(team_rows) < 2:
                continue
            away_identity, away_score = self._parse_team_row(team_rows[0])
            home_identity, home_score = self._parse_team_row(team_rows[1])

            boxscore_link = div.select_one("p.links a[href*='/boxscores/']")
            if not boxscore_link:
                continue
            boxscore_url = urljoin(self.base_url, boxscore_link["href"])
            source_game_key = boxscore_link["href"].split("/")[-1].replace(".html", "")
            box_soup = self.fetch_html(boxscore_url)

            away_stats = self._extract_team_stats(box_soup, away_identity.abbreviation or "")
            home_stats = self._extract_team_stats(box_soup, home_identity.abbreviation or "")

            identity = GameIdentification(
                league_code=self.league_code,
                season=self._season_from_date(day),
                season_type="regular",
                game_date=datetime.combine(day, datetime.min.time()),
                home_team=home_identity,
                away_team=away_identity,
                source_game_key=source_game_key,
            )
            team_boxscores = [
                self._build_team_boxscore(away_identity, False, away_score, away_stats),
                self._build_team_boxscore(home_identity, True, home_score, home_stats),
            ]
            games.append(
                NormalizedGame(
                    identity=identity,
                    status="completed",
                    home_score=home_score,
                    away_score=away_score,
                    team_boxscores=team_boxscores,
                )
            )
        return games


