"""Build one scheduled-matchup feature row from an as-of history snapshot."""

from dataclasses import dataclass

import pandas as pd

from nba_forecast.data.contracts import CANONICAL_GAME_COLUMNS, expected_season_id
from nba_forecast.features.game_features import build_game_features


@dataclass(frozen=True)
class ScheduledMatchup:
    """Identifiers known before one scheduled game's tip-off."""

    game_id: str
    game_date: pd.Timestamp
    season_id: str
    season_type: str
    season_key: str
    home_team_id: int
    away_team_id: int
    home_team_abbreviation: str
    away_team_abbreviation: str


def build_scheduled_matchup_features(
    completed_games: pd.DataFrame,
    matchup: ScheduledMatchup,
    *,
    as_of_date: pd.Timestamp,
) -> pd.DataFrame:
    """Return one feature row using games strictly before ``as_of_date``."""
    cutoff = pd.Timestamp(as_of_date).normalize()
    game_date = pd.Timestamp(matchup.game_date).normalize()
    _validate_matchup(matchup, cutoff, game_date)

    history = completed_games.copy()
    history["game_date"] = pd.to_datetime(history["game_date"], errors="raise")
    history = history.loc[history["game_date"] < cutoff].copy()
    if matchup.game_id in history["game_id"].astype(str).tolist():
        raise ValueError("scheduled game_id already exists before as_of_date")

    scheduled_row = _scheduled_game_row(matchup, game_date)
    feature_input = pd.concat([history, scheduled_row], ignore_index=True)
    features = build_game_features(feature_input)
    scheduled_features = features.loc[
        features["game_id"].astype(str) == matchup.game_id
    ].copy()
    scheduled_features.insert(1, "as_of_date", cutoff)
    return scheduled_features.reset_index(drop=True)


def _scheduled_game_row(
    matchup: ScheduledMatchup,
    game_date: pd.Timestamp,
) -> pd.DataFrame:
    missing = float("nan")
    row = {
        "game_id": matchup.game_id,
        "game_date": game_date,
        "season_id": matchup.season_id,
        "season_type": matchup.season_type,
        "season_key": matchup.season_key,
        "home_team_id": matchup.home_team_id,
        "away_team_id": matchup.away_team_id,
        "home_team_abbreviation": matchup.home_team_abbreviation,
        "away_team_abbreviation": matchup.away_team_abbreviation,
        "home_points": missing,
        "away_points": missing,
        "home_fga": missing,
        "away_fga": missing,
        "home_fgm": missing,
        "away_fgm": missing,
        "home_fta": missing,
        "away_fta": missing,
        "home_oreb": missing,
        "away_oreb": missing,
        "home_tov": missing,
        "away_tov": missing,
        "home_win": missing,
    }
    return pd.DataFrame([row], columns=CANONICAL_GAME_COLUMNS)


def _validate_matchup(
    matchup: ScheduledMatchup,
    as_of_date: pd.Timestamp,
    game_date: pd.Timestamp,
) -> None:
    if as_of_date > game_date:
        raise ValueError("as_of_date must be on or before the scheduled game date")
    if matchup.home_team_id == matchup.away_team_id:
        raise ValueError("home and away teams must differ")
    if not matchup.game_id.strip():
        raise ValueError("scheduled game_id must be non-empty")
    try:
        expected_id = expected_season_id(matchup.season_type, matchup.season_key)
    except ValueError as error:
        message = f"scheduled matchup has invalid season context: {error}"
        raise ValueError(message) from error
    if matchup.season_id != expected_id:
        raise ValueError("scheduled matchup has inconsistent season context")
