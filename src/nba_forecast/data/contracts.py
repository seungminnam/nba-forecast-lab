"""Shared data contracts and errors."""

import re

BOX_SCORE_SOURCE_COLUMNS = (
    "FGA",
    "FGM",
    "FTA",
    "OREB",
    "TOV",
)

SUPPORTED_SEASON_TYPES = ("Regular Season", "Playoffs")

SOURCE_TEAM_GAME_COLUMNS = (
    "GAME_ID",
    "GAME_DATE",
    "SEASON_ID",
    "TEAM_ID",
    "TEAM_ABBREVIATION",
    "MATCHUP",
    "WL",
    "PTS",
) + BOX_SCORE_SOURCE_COLUMNS

CANONICAL_GAME_COLUMNS = (
    "game_id",
    "game_date",
    "season_id",
    "season_type",
    "season_key",
    "home_team_id",
    "away_team_id",
    "home_team_abbreviation",
    "away_team_abbreviation",
    "home_points",
    "away_points",
    "home_fga",
    "away_fga",
    "home_fgm",
    "away_fgm",
    "home_fta",
    "away_fta",
    "home_oreb",
    "away_oreb",
    "home_tov",
    "away_tov",
    "home_win",
)


class CanonicalGameError(ValueError):
    """Raised when source rows cannot produce a valid canonical game table."""


def expected_season_id(season_type: str, season_key: str) -> str:
    """Return the NBA Stats season ID required by validated season context."""
    if season_type not in SUPPORTED_SEASON_TYPES:
        raise ValueError(f"Unsupported season_type: {season_type}")
    match = re.fullmatch(r"(\d{4})-(\d{2})", season_key)
    if match is None:
        raise ValueError(f"Invalid season_key: {season_key}")
    start_year = int(match.group(1))
    if match.group(2) != str(start_year + 1)[-2:]:
        raise ValueError(f"Invalid season_key: {season_key}")
    prefix = "2" if season_type == "Regular Season" else "4"
    return f"{prefix}{start_year}"
