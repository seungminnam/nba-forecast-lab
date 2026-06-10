"""Shared data contracts and errors."""

BOX_SCORE_SOURCE_COLUMNS = (
    "FGA",
    "FGM",
    "FTA",
    "OREB",
    "TOV",
)

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
