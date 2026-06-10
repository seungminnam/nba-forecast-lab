"""Shared data contracts and errors."""

SOURCE_TEAM_GAME_COLUMNS = (
    "GAME_ID",
    "GAME_DATE",
    "SEASON_ID",
    "TEAM_ID",
    "TEAM_ABBREVIATION",
    "MATCHUP",
    "WL",
    "PTS",
)

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
    "home_win",
)


class CanonicalGameError(ValueError):
    """Raised when source rows cannot produce a valid canonical game table."""

