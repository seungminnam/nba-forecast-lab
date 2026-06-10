"""Validation rules for canonical completed games."""

import pandas as pd

from nba_forecast.data.contracts import CANONICAL_GAME_COLUMNS, CanonicalGameError


def validate_games(games: pd.DataFrame) -> None:
    """Raise CanonicalGameError when completed canonical games are invalid."""
    failures: list[str] = []

    missing_columns = sorted(set(CANONICAL_GAME_COLUMNS) - set(games.columns))
    if missing_columns:
        failures.append(f"missing canonical columns: {', '.join(missing_columns)}")
        raise CanonicalGameError("; ".join(failures))

    if games["game_id"].duplicated().any():
        failures.append("duplicate game_id values are not allowed")
    if (games["home_team_id"] == games["away_team_id"]).any():
        failures.append("home and away teams must differ")
    if games[["home_points", "away_points"]].isna().any(axis=None):
        failures.append("scores must be present for completed games")
    if not games["home_win"].isin([0, 1]).all():
        failures.append("home_win must be 0 or 1")

    if failures:
        raise CanonicalGameError("; ".join(failures))

