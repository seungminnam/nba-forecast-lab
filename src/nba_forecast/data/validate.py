"""Validation rules for canonical completed games."""

import pandas as pd

from nba_forecast.data.contracts import (
    CANONICAL_GAME_COLUMNS,
    SUPPORTED_SEASON_TYPES,
    CanonicalGameError,
    expected_season_id,
)


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
    if not games["season_type"].isin(SUPPORTED_SEASON_TYPES).all():
        failures.append("unsupported season_type values are not allowed")
    empty_season_keys = games["season_key"].astype(str).str.strip().eq("")
    if games["season_key"].isna().any() or empty_season_keys.any():
        failures.append("season_key must be non-empty")
    if not _has_consistent_season_context(games):
        failures.append("inconsistent season context is not allowed")

    if failures:
        raise CanonicalGameError("; ".join(failures))


def _has_consistent_season_context(games: pd.DataFrame) -> bool:
    contexts = games[["season_id", "season_type", "season_key"]].drop_duplicates()
    for context in contexts.itertuples(index=False):
        season_type = str(context.season_type)
        season_key = str(context.season_key)
        try:
            expected_id = expected_season_id(season_type, season_key)
        except ValueError:
            return False
        if str(context.season_id) != expected_id:
            return False
    return True
