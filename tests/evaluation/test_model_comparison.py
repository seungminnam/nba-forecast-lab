import pandas as pd

from nba_forecast.evaluation.model_comparison import (
    build_training_windows,
    compare_models_by_training_window,
)
from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS


def test_build_training_windows_selects_only_pre_validation_seasons() -> None:
    features = _model_frame(["22020", "22021", "22022", "22023", "22024", "22025"])

    windows = build_training_windows(features, validation_season="22024")

    assert windows["recent_3"].seasons == ("22021", "22022", "22023")
    assert windows["recent_5"].seasons == (
        "22020",
        "22021",
        "22022",
        "22023",
    )
    assert windows["decayed_full_history"].seasons == (
        "22020",
        "22021",
        "22022",
        "22023",
    )
    assert "22024" not in windows["decayed_full_history"].frame["season_id"].tolist()
    assert "22025" not in windows["decayed_full_history"].frame["season_id"].tolist()


def test_full_history_weights_decay_by_season_age() -> None:
    features = _model_frame(["22020", "22021", "22022", "22023", "22024"])

    window = build_training_windows(
        features,
        validation_season="22024",
        annual_decay=0.8,
    )["decayed_full_history"]

    assert window.sample_weight.tolist() == [0.8**3, 0.8**2, 0.8, 1.0]


def test_compare_models_uses_identical_validation_rows_for_every_result() -> None:
    features = _model_frame(
        [
            "22018",
            "22018",
            "22019",
            "22019",
            "22020",
            "22020",
            "22021",
            "22021",
            "22022",
            "22022",
            "22023",
            "22023",
            "22024",
            "22024",
            "22025",
        ]
    )

    results = compare_models_by_training_window(features, validation_season="22024")

    assert len(results) == 6
    assert set(results["model"]) == {"logistic_regression", "xgboost"}
    assert set(results["training_window"]) == {
        "recent_3",
        "recent_5",
        "decayed_full_history",
    }
    assert results["validation_rows"].tolist() == [2] * 6
    assert {
        "brier_score",
        "log_loss",
        "roc_auc",
        "accuracy",
    }.issubset(results.columns)


def _model_frame(seasons: list[str]) -> pd.DataFrame:
    rows = len(seasons)
    data = {
        feature: [
            ((-1) ** index) * (position + 1) / 10
            for index in range(rows)
        ]
        for position, feature in enumerate(MODEL_FEATURE_COLUMNS)
    }
    data["game_id"] = [f"game-{index}" for index in range(rows)]
    data["game_date"] = pd.date_range("2018-01-01", periods=rows, freq="180D")
    data["season_id"] = seasons
    data["home_win"] = [index % 2 for index in range(rows)]
    return pd.DataFrame(data)
