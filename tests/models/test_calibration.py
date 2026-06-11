import pandas as pd

from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS
from nba_forecast.models.calibration import (
    CALIBRATION_METHODS,
    fit_calibrator,
    run_calibration_experiment,
    split_calibration_period,
)


def test_split_calibration_period_is_chronological() -> None:
    frame = pd.DataFrame(
        {
            "game_date": pd.date_range("2025-01-01", periods=6),
            "game_id": [f"game-{index}" for index in range(6)],
        }
    )

    fit, selection = split_calibration_period(frame)

    assert fit["game_id"].tolist() == ["game-0", "game-1", "game-2"]
    assert selection["game_id"].tolist() == ["game-3", "game-4", "game-5"]
    assert fit["game_date"].max() < selection["game_date"].min()


def test_calibrators_return_bounded_probabilities() -> None:
    probabilities = pd.Series([0.1, 0.2, 0.4, 0.6, 0.8, 0.9])
    targets = pd.Series([0, 0, 0, 1, 1, 1])

    for method in CALIBRATION_METHODS:
        calibrator = fit_calibrator(method, probabilities, targets)
        calibrated = calibrator.predict(probabilities)

        assert calibrated.between(0, 1, inclusive="neither").all()


def test_test_labels_do_not_change_calibration_selection() -> None:
    features = _historical_model_frame()

    original = run_calibration_experiment(
        features,
        validation_season="22024",
        test_season="22025",
    )
    changed = features.copy()
    changed.loc[changed["season_id"] == "22025", "home_win"] = (
        1 - changed.loc[changed["season_id"] == "22025", "home_win"]
    )
    mutated = run_calibration_experiment(
        changed,
        validation_season="22024",
        test_season="22025",
    )

    assert original.selected_method == mutated.selected_method
    pd.testing.assert_frame_equal(
        original.selection_metrics,
        mutated.selection_metrics,
    )
    assert not original.test_metrics.equals(mutated.test_metrics)


def _historical_model_frame() -> pd.DataFrame:
    seasons = [f"220{year:02d}" for year in range(19, 26)]
    rows_per_season = 20
    rows = len(seasons) * rows_per_season
    data = {
        feature: [
            ((-1) ** index) * (position + 1) / 10 + (index % 5) / 20
            for index in range(rows)
        ]
        for position, feature in enumerate(MODEL_FEATURE_COLUMNS)
    }
    data["game_id"] = [f"game-{index}" for index in range(rows)]
    data["game_date"] = pd.date_range("2019-10-01", periods=rows, freq="7D")
    data["season_id"] = [
        season for season in seasons for _ in range(rows_per_season)
    ]
    data["home_win"] = [index % 2 for index in range(rows)]
    return pd.DataFrame(data)
