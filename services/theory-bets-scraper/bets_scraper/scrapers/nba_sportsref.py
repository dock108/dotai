"""NBA scraper powered by Basketball Reference."""

from __future__ import annotations

from datetime import date, datetime
from typing import Sequence
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import GameIdentification, NormalizedGame, NormalizedTeamBoxscore, TeamIdentity
from .base import BaseSportsReferenceScraper, ScraperError


class NBASportsReferenceScraper(BaseSportsReferenceScraper):
    sport = "nba"
    league_code = "NBA"
    base_url = "https://www.basketball-reference.com/boxscores/"

    def _parse_team_row(self, row) -> tuple[TeamIdentity, int]:
        team_link = row.find("a")
        if not team_link:
            raise ScraperError("Missing team link")
        team_name = team_link.text.strip()
        href_parts = team_link["href"].strip("/").split("/")
        abbreviation = href_parts[1] if len(href_parts) > 1 else team_name[:3].upper()
        score_cell = row.find("td", class_="right")
        if score_cell is None:
            raise ScraperError("Missing score cell")
        score = int(score_cell.text.strip())
        identity = TeamIdentity(
            league_code=self.league_code,
            name=team_name,
            short_name=team_name,
            abbreviation=abbreviation.upper(),
            external_ref=abbreviation.upper(),
        )
        return identity, score

    def _extract_team_stats(self, soup: BeautifulSoup, team_abbr: str) -> dict:
        table = soup.find("table", id=f"box-{team_abbr.lower()}-game-basic")
        if not table:
            return {}
        totals = {}
        tfoot = table.find("tfoot")
        if not tfoot:
            return totals
        for cell in tfoot.find_all("td"):
            stat = cell.get("data-stat")
            totals[stat] = cell.text.strip()
        return totals

    def _build_team_boxscore(self, identity: TeamIdentity, is_home: bool, score: int, stats: dict) -> NormalizedTeamBoxscore:
        def _to_int(value: str | None) -> int | None:
            if value in (None, "", "-"):
                return None
            return int(float(value))

        return NormalizedTeamBoxscore(
            team=identity,
            is_home=is_home,
            points=score,
            rebounds=_to_int(stats.get("trb")),
            assists=_to_int(stats.get("ast")),
            turnovers=_to_int(stats.get("tov")),
            raw_stats=stats,
        )

    def _season_from_date(self, day: date) -> int:
        return day.year if day.month >= 7 else day.year - 1

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
                raise ScraperError("Missing boxscore link")
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


