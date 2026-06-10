import pandas as pd

from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS
from nba_forecast.models.baselines import (
    constant_home_rate_probability,
    elo_probability,
    fit_logistic_regression,
    logistic_regression_probability,
    season_win_pct_probability,
)


def test_simple_baselines_return_home_win_probabilities() -> None:
    train = pd.DataFrame({"home_win": [1, 0, 1, 1]})
    test = pd.DataFrame(
        {
            "season_win_pct_diff": [0.4, -0.4],
            "elo_home_win_probability": [0.7, 0.3],
        }
    )

    assert constant_home_rate_probability(train, test).tolist() == [0.75, 0.75]
    assert season_win_pct_probability(test).tolist() == [0.7, 0.3]
    assert elo_probability(test).tolist() == [0.7, 0.3]


def test_logistic_regression_returns_bounded_probabilities() -> None:
    train = _model_frame(8)
    test = _model_frame(2)

    model = fit_logistic_regression(train)
    probabilities = logistic_regression_probability(model, test)

    assert len(probabilities) == 2
    assert probabilities.between(0, 1, inclusive="neither").all()


def _model_frame(rows: int) -> pd.DataFrame:
    data = {
        feature: [((-1) ** index) * (position + 1) / 10 for index in range(rows)]
        for position, feature in enumerate(MODEL_FEATURE_COLUMNS)
    }
    data["home_win"] = [index % 2 for index in range(rows)]
    return pd.DataFrame(data)

