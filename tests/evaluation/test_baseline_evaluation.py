import pandas as pd

from nba_forecast.evaluation.baselines import evaluate_baselines
from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS


def test_evaluate_baselines_returns_comparable_metric_rows() -> None:
    train = _model_frame(10)
    test = _model_frame(4)

    results = evaluate_baselines(train, test)

    assert results["model"].tolist() == [
        "constant_home_rate",
        "season_win_pct",
        "elo",
        "logistic_regression",
    ]
    assert {
        "brier_score",
        "log_loss",
        "roc_auc",
        "accuracy",
    }.issubset(results.columns)


def _model_frame(rows: int) -> pd.DataFrame:
    data = {
        feature: [((-1) ** index) * (position + 1) / 10 for index in range(rows)]
        for position, feature in enumerate(MODEL_FEATURE_COLUMNS)
    }
    data["season_win_pct_diff"] = [0.2 if index % 2 else -0.2 for index in range(rows)]
    data["elo_home_win_probability"] = [
        0.7 if index % 2 else 0.3 for index in range(rows)
    ]
    data["home_win"] = [index % 2 for index in range(rows)]
    return pd.DataFrame(data)

