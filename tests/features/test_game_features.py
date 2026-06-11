from pathlib import Path

import pandas as pd

from nba_forecast.data.transform import team_rows_to_games
from nba_forecast.features.game_features import (
    MODEL_FEATURE_COLUMNS,
    build_game_features,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "team_game_rows.csv"


def test_build_game_features_creates_one_model_row_per_game() -> None:
    team_rows = pd.read_csv(
        FIXTURE_PATH,
        dtype={"GAME_ID": "string", "SEASON_ID": "string"},
    )
    games = team_rows_to_games(
        team_rows,
        season_type="Regular Season",
        season_key="2025-26",
    )

    features = build_game_features(games)

    assert len(features) == len(games)
    assert features["game_id"].is_unique
    assert "elo_diff" in MODEL_FEATURE_COLUMNS
    assert "season_win_pct_diff" in MODEL_FEATURE_COLUMNS
    assert "home_is_back_to_back" in MODEL_FEATURE_COLUMNS
    assert "away_is_back_to_back" in MODEL_FEATURE_COLUMNS
    assert "home_win" not in MODEL_FEATURE_COLUMNS
    assert set(MODEL_FEATURE_COLUMNS).issubset(features.columns)
    assert features["season_type"].eq("Regular Season").all()
    assert features["season_key"].eq("2025-26").all()
