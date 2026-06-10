"""Assemble one pre-game model feature row per game."""

import pandas as pd

from nba_forecast.features.elo import build_elo_features
from nba_forecast.features.team_state import (
    PREGAME_TEAM_FEATURE_COLUMNS,
    build_team_state,
)

DIFFERENCE_TEAM_FEATURES = tuple(
    feature
    for feature in PREGAME_TEAM_FEATURE_COLUMNS
    if feature != "is_back_to_back"
)
MODEL_FEATURE_COLUMNS = (
    "elo_diff",
    "elo_home_win_probability",
    *(f"{feature}_diff" for feature in DIFFERENCE_TEAM_FEATURES),
    "home_is_back_to_back",
    "away_is_back_to_back",
)


def build_game_features(games: pd.DataFrame) -> pd.DataFrame:
    """Return identifiers, target, and strictly pre-game model features."""
    team_state = build_team_state(games)
    home_state = _side_state(team_state, is_home=True)
    away_state = _side_state(team_state, is_home=False)
    elo_features = build_elo_features(games)

    features = games[
        [
            "game_id",
            "game_date",
            "season_id",
            "home_team_id",
            "away_team_id",
            "home_win",
        ]
    ].copy()
    features = features.merge(home_state, on="game_id", validate="one_to_one")
    features = features.merge(away_state, on="game_id", validate="one_to_one")
    features = features.merge(elo_features, on="game_id", validate="one_to_one")

    for feature in DIFFERENCE_TEAM_FEATURES:
        features[f"{feature}_diff"] = (
            features[f"home_{feature}"] - features[f"away_{feature}"]
        )

    features["home_is_back_to_back"] = features["home_is_back_to_back"].astype(int)
    features["away_is_back_to_back"] = features["away_is_back_to_back"].astype(int)
    return features.sort_values(["game_date", "game_id"], ignore_index=True)


def _side_state(team_state: pd.DataFrame, *, is_home: bool) -> pd.DataFrame:
    prefix = "home" if is_home else "away"
    columns = ["game_id", *PREGAME_TEAM_FEATURE_COLUMNS]
    side = team_state.loc[team_state["is_home"] == int(is_home), columns].copy()
    return side.rename(
        columns={
            feature: f"{prefix}_{feature}"
            for feature in PREGAME_TEAM_FEATURE_COLUMNS
        }
    )

