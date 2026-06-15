from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from nba_forecast.application.matchup_prediction import MatchupPredictionOutput
from nba_forecast.application.prediction_registry import (
    REGISTRY_COLUMNS,
    empty_prediction_registry,
    register_prediction,
)
from nba_forecast.data.prediction_registry_storage import (
    load_prediction_registry,
    write_prediction_registry,
)
from nba_forecast.features.matchup_features import ScheduledMatchup


def test_load_prediction_registry_initializes_missing_table(tmp_path: Path) -> None:
    registry = load_prediction_registry(tmp_path)

    assert registry.empty
    assert registry.columns.tolist() == list(REGISTRY_COLUMNS)


def test_write_prediction_registry_round_trips_parquet_and_duckdb(
    tmp_path: Path,
) -> None:
    registry = _registry()

    parquet_path, database_path = write_prediction_registry(registry, tmp_path)
    loaded = load_prediction_registry(tmp_path)

    assert parquet_path == tmp_path / "predictions.parquet"
    assert database_path == tmp_path / "prediction_registry.duckdb"
    pd.testing.assert_frame_equal(loaded, registry)
    with duckdb.connect(str(database_path), read_only=True) as connection:
        rows = connection.execute(
            "SELECT prediction_id, game_id FROM predictions"
        ).fetchall()
    assert rows == [
        (
            registry.iloc[0]["prediction_id"],
            "scheduled-1",
        )
    ]


def test_write_prediction_registry_rejects_invalid_data_before_replacement(
    tmp_path: Path,
) -> None:
    registry = _registry()
    parquet_path, _ = write_prediction_registry(registry, tmp_path)
    original_bytes = parquet_path.read_bytes()
    invalid = registry.assign(home_win_probability=1.2)

    with pytest.raises(ValueError, match="probabilities"):
        write_prediction_registry(invalid, tmp_path)

    assert parquet_path.read_bytes() == original_bytes


def _registry() -> pd.DataFrame:
    prediction = MatchupPredictionOutput(
        matchup=ScheduledMatchup(
            game_id="scheduled-1",
            game_date=pd.Timestamp("2026-10-22"),
            season_id="22026",
            season_type="Regular Season",
            season_key="2026-27",
            home_team_id=1,
            away_team_id=2,
            home_team_abbreviation="HOM",
            away_team_abbreviation="AWY",
        ),
        prediction_timestamp=datetime(2026, 10, 20, 12, tzinfo=timezone.utc),
        as_of_date=pd.Timestamp("2026-10-20"),
        model_version="model-a",
        feature_version="features-v1",
        home_win_probability=0.6,
        away_win_probability=0.4,
        feature_row=pd.DataFrame([{"elo_diff": 12.5}]),
        feature_columns=("elo_diff",),
    )
    return register_prediction(empty_prediction_registry(), prediction).registry
