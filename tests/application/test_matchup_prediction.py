from datetime import datetime, timezone

import pandas as pd

from nba_forecast.application.matchup_prediction import predict_scheduled_matchup
from nba_forecast.features.game_features import (
    MODEL_FEATURE_COLUMNS,
    build_game_features,
)
from nba_forecast.features.matchup_features import ScheduledMatchup
from nba_forecast.models.artifacts import ModelBundle, ModelBundleMetadata
from nba_forecast.models.baselines import fit_logistic_regression
from nba_forecast.models.calibration import RawCalibrator


def test_matchup_prediction_scores_exact_as_of_feature_row() -> None:
    games = _games()
    bundle = _bundle(games)
    matchup = ScheduledMatchup(
        game_id="scheduled-1",
        game_date=pd.Timestamp("2025-10-27"),
        season_id="22025",
        season_type="Regular Season",
        season_key="2025-26",
        home_team_id=1,
        away_team_id=2,
        home_team_abbreviation="HOM",
        away_team_abbreviation="AWY",
    )

    output = predict_scheduled_matchup(
        games,
        matchup,
        as_of_date=pd.Timestamp("2025-10-27"),
        bundle=bundle,
        prediction_timestamp=datetime(2026, 6, 11, 8, 30, tzinfo=timezone.utc),
    )
    expected = float(bundle.predict_probability(output.feature_row).iloc[0])
    report = output.to_report()

    assert output.home_win_probability == expected
    assert output.away_win_probability == 1.0 - expected
    assert output.model_version == "test-raw"
    assert report["prediction_timestamp"] == "2026-06-11T08:30:00+00:00"
    assert report["as_of_date"] == "2025-10-27"
    assert report["feature_version"] == "model-features-v1"
    assert report["final_outcome"] is None
    assert report["matchup"]["home_team_abbreviation"] == "HOM"
    assert report["matchup"]["season_type"] == "Regular Season"
    assert report["matchup"]["season_key"] == "2025-26"
    assert set(report["features"]) == set(MODEL_FEATURE_COLUMNS)


def _bundle(games: pd.DataFrame) -> ModelBundle:
    features = build_game_features(games)
    model = fit_logistic_regression(features)
    metadata = ModelBundleMetadata(
        version="test-raw",
        created_at=datetime(2026, 6, 11, tzinfo=timezone.utc).isoformat(),
        base_model="logistic_regression",
        calibration_method="raw",
        feature_columns=MODEL_FEATURE_COLUMNS,
        training_seasons=("22025",),
        calibration_season="22025",
        test_season="22025",
        metrics={"brier_score": 0.2},
    )
    return ModelBundle(model=model, calibrator=RawCalibrator(), metadata=metadata)


def _games() -> pd.DataFrame:
    rows = []
    for index, (date, home_win, home_points, away_points) in enumerate(
        [
            ("2025-10-21", 1, 110, 100),
            ("2025-10-22", 0, 98, 105),
            ("2025-10-25", 1, 112, 108),
            ("2025-10-26", 0, 101, 109),
        ],
        start=1,
    ):
        rows.append(
            {
                "game_id": f"game-{index}",
                "game_date": pd.Timestamp(date),
                "season_id": "22025",
                "season_type": "Regular Season",
                "season_key": "2025-26",
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team_abbreviation": "HOM",
                "away_team_abbreviation": "AWY",
                "home_points": home_points,
                "away_points": away_points,
                "home_fga": 88,
                "away_fga": 90,
                "home_fgm": 42,
                "away_fgm": 39,
                "home_fta": 20,
                "away_fta": 18,
                "home_oreb": 10,
                "away_oreb": 9,
                "home_tov": 12,
                "away_tov": 14,
                "home_win": home_win,
            }
        )
    return pd.DataFrame(rows)
