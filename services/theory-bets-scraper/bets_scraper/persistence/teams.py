"""Team persistence helpers.

Handles team upsert and lookup logic, including NCAAB-specific name normalization.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..db import db_models
from ..logging import logger
from ..normalization import normalize_team_name
from ..utils.db_queries import count_team_games
from ..utils.datetime_utils import utcnow

if TYPE_CHECKING:
    from ..models import TeamIdentity


def _normalize_ncaab_name_for_matching(name: str) -> str:
    """Normalize NCAAB team name for matching purposes.
    
    Handles common variations:
    - "St" -> "State"
    - "U" -> "University"
    - Removes punctuation
    - Normalizes whitespace
    - Returns lowercase for case-insensitive comparison
    """
    normalized = name.strip()
    normalized = re.sub(r'\bSt\b', 'State', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'\bU\b', 'University', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'[.,\-]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized.lower()


def _upsert_team(session: Session, league_id: int, identity: TeamIdentity) -> int:
    """Upsert a team, creating or updating as needed.
    
    For NCAAB, abbreviations are optional (None) to avoid collisions.
    For other leagues, abbreviations are required.
    """
    team_name = identity.name
    short_name = identity.short_name or team_name
    league = session.get(db_models.SportsLeague, league_id)
    league_code = league.code if league else None
    
    if not identity.abbreviation and league_code != "NCAAB":
        raise ValueError(f"Team identity must have abbreviation: {team_name}")
    abbreviation = identity.abbreviation
    
    stmt = (
        insert(db_models.SportsTeam)
        .values(
            league_id=league_id,
            external_ref=identity.external_ref,
            name=team_name,
            short_name=short_name,
            abbreviation=abbreviation,
            location=None,
            external_codes={},
        )
        .on_conflict_do_update(
            index_elements=["league_id", "name"],
            set_={
                "short_name": short_name,
                "abbreviation": abbreviation,
                "external_ref": identity.external_ref,
                "updated_at": utcnow(),
            },
        )
        .returning(db_models.SportsTeam.id)
    )
    result = session.execute(stmt).scalar_one()
    return int(result)


def _find_team_by_name(
    session: Session,
    league_id: int,
    team_name: str,
    team_abbr: str | None = None,
) -> int | None:
    """Find existing team by name (exact or normalized match).
    
    Tries multiple strategies:
    1. Exact match on name or short_name
    2. Normalized match for NCAAB (handles "St" vs "State", etc.)
    3. If team_name contains a space, try matching the first word (city name) - non-NCAAB only
    4. Match by abbreviation (skipped for NCAAB to avoid collisions)
    5. Prefer teams with more games (more established)
    """
    def team_usage(team_id: int) -> int:
        return count_team_games(session, team_id)

    league = session.get(db_models.SportsLeague, league_id)
    league_code = league.code if league else None

    candidate_ids: list[int] = []

    if league_code == "NCAAB":
        canonical_name, _ = normalize_team_name(league_code, team_name)
        exact_match_stmt = (
            select(db_models.SportsTeam.id)
            .where(db_models.SportsTeam.league_id == league_id)
            .where(
                or_(
                    db_models.SportsTeam.name == team_name,
                    db_models.SportsTeam.name == canonical_name,
                    db_models.SportsTeam.short_name == team_name,
                    db_models.SportsTeam.short_name == canonical_name,
                    func.lower(db_models.SportsTeam.name) == func.lower(team_name),
                    func.lower(db_models.SportsTeam.name) == func.lower(canonical_name),
                    func.lower(db_models.SportsTeam.short_name) == func.lower(team_name),
                    func.lower(db_models.SportsTeam.short_name) == func.lower(canonical_name),
                )
            )
        )
        exact_matches = [row[0] for row in session.execute(exact_match_stmt).all()]
        candidate_ids.extend(exact_matches)
        
        if not exact_matches:
            normalized_input = _normalize_ncaab_name_for_matching(team_name)
            all_teams_stmt = (
                select(db_models.SportsTeam.id, db_models.SportsTeam.name, db_models.SportsTeam.short_name)
                .where(db_models.SportsTeam.league_id == league_id)
            )
            all_teams = session.execute(all_teams_stmt).all()
            for team_id, db_name, db_short_name in all_teams:
                db_name_norm = _normalize_ncaab_name_for_matching(db_name or "")
                db_short_norm = _normalize_ncaab_name_for_matching(db_short_name or "")
                if (
                    normalized_input == db_name_norm
                    or normalized_input == db_short_norm
                    or normalized_input in db_name_norm
                    or db_name_norm in normalized_input
                    or normalized_input in db_short_norm
                    or db_short_norm in normalized_input
                ):
                    candidate_ids.append(team_id)
    else:
        exact_match_stmt = (
            select(db_models.SportsTeam.id)
            .where(db_models.SportsTeam.league_id == league_id)
            .where(
                or_(
                    db_models.SportsTeam.name == team_name,
                    db_models.SportsTeam.short_name == team_name,
                    func.lower(db_models.SportsTeam.name) == func.lower(team_name),
                    func.lower(db_models.SportsTeam.short_name) == func.lower(team_name),
                )
            )
            .limit(1)
        )
        exact_match_id = session.execute(exact_match_stmt).scalar()
        if exact_match_id is not None:
            candidate_ids.append(exact_match_id)

        if team_name and " " in team_name:
            first_word = team_name.split()[0]
            base_stmt = (
                select(db_models.SportsTeam.id)
                .where(db_models.SportsTeam.league_id == league_id)
                .where(
                    or_(
                        db_models.SportsTeam.name == first_word,
                        db_models.SportsTeam.short_name == first_word,
                        func.lower(db_models.SportsTeam.name) == func.lower(first_word),
                        func.lower(db_models.SportsTeam.short_name) == func.lower(first_word),
                        func.lower(db_models.SportsTeam.name).like(func.lower(first_word) + "%"),
                        func.lower(db_models.SportsTeam.short_name).like(func.lower(first_word) + "%"),
                    )
                )
            )
            base_matches = [row[0] for row in session.execute(base_stmt).all()]
            candidate_ids.extend(base_matches)
        elif team_name:
            single_word_stmt = (
                select(db_models.SportsTeam.id)
                .where(db_models.SportsTeam.league_id == league_id)
                .where(
                    or_(
                        func.lower(db_models.SportsTeam.name).like(func.lower(team_name) + "%"),
                        func.lower(db_models.SportsTeam.short_name).like(func.lower(team_name) + "%"),
                    )
                )
            )
            single_word_matches = [row[0] for row in session.execute(single_word_stmt).all()]
            candidate_ids.extend(single_word_matches)

    if team_abbr and league_code != "NCAAB":
        stmt = (
            select(db_models.SportsTeam.id)
            .where(db_models.SportsTeam.league_id == league_id)
            .where(func.upper(db_models.SportsTeam.abbreviation) == func.upper(team_abbr))
        )
        abbr_matches = [row[0] for row in session.execute(stmt).all()]
        candidate_ids.extend(abbr_matches)

    if not candidate_ids:
        return None

    seen = set()
    unique_candidates = []
    for cid in candidate_ids:
        if cid not in seen:
            seen.add(cid)
            unique_candidates.append(cid)

    if league_code == "NCAAB" and len(unique_candidates) > 1:
        canonical_name, _ = normalize_team_name(league_code, team_name)
        normalized_input = _normalize_ncaab_name_for_matching(team_name)
        exact_matches = []
        for cid in unique_candidates:
            team = session.get(db_models.SportsTeam, cid)
            if not team:
                continue
            if (
                team.name.lower() == team_name.lower() or
                team.name.lower() == canonical_name.lower() or
                team.short_name.lower() == team_name.lower() or
                team.short_name.lower() == canonical_name.lower()
            ):
                exact_matches.append(cid)
            elif normalized_input:
                db_name_norm = _normalize_ncaab_name_for_matching(team.name or "")
                db_short_norm = _normalize_ncaab_name_for_matching(team.short_name or "")
                if normalized_input == db_name_norm or normalized_input == db_short_norm:
                    exact_matches.append(cid)
        
        if exact_matches:
            unique_candidates = exact_matches
        elif unique_candidates:
            team = session.get(db_models.SportsTeam, unique_candidates[0])
            logger.warning(
                "ncaab_team_match_ambiguous",
                requested_name=team_name,
                canonical_name=canonical_name,
                matched_team_id=unique_candidates[0],
                matched_team_name=team.name if team else None,
                total_candidates=len(unique_candidates),
            )

    def team_score(team_id: int) -> tuple[int, int, int]:
        """
        Score teams for selection.
        For NCAAB: prioritize usage (games), then canonical match, then shorter name.
        For others: keep original bias toward canonical and full name, then usage.
        """
        team = session.get(db_models.SportsTeam, team_id)
        if not team:
            return (0, 0, 0)
        
        matches_canonical = False
        if league_code:
            canonical_name, _ = normalize_team_name(league_code, team.name)
            matches_canonical = (team.name == canonical_name)
        
        has_full_name = " " in team.name
        usage = team_usage(team_id)
        if league_code == "NCAAB":
            # usage first, then canonical, then shorter name
            return (usage, 1 if matches_canonical else 0, -len(team.name or ""))
        return (10000 if matches_canonical else 0, 1000 if has_full_name else 0, usage)
    
    scored_candidates = [(team_score(cid), cid) for cid in unique_candidates]
    scored_candidates.sort(reverse=True)
    best_id = scored_candidates[0][1]

    return best_id
