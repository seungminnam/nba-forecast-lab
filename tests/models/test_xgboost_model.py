import pandas as pd

from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS
from nba_forecast.models.xgboost_model import (
    fit_xgboost,
    xgboost_probability,
)


def test_xgboost_probabilities_are_bounded_and_deterministic() -> None:
    frame = _model_frame(20)

    first = xgboost_probability(fit_xgboost(frame), frame)
    second = xgboost_probability(fit_xgboost(frame), frame)

    assert first.between(0, 1, inclusive="neither").all()
    assert first.tolist() == second.tolist()


def test_xgboost_accepts_sample_weights() -> None:
    frame = _model_frame(20)
    weights = pd.Series([0.5] * 10 + [1.0] * 10)

    model = fit_xgboost(frame, sample_weight=weights)

    assert len(xgboost_probability(model, frame)) == len(frame)


def _model_frame(rows: int) -> pd.DataFrame:
    data = {
        feature: [
            ((-1) ** index) * (position + 1) / 10
            for index in range(rows)
        ]
        for position, feature in enumerate(MODEL_FEATURE_COLUMNS)
    }
    data["home_win"] = [index % 2 for index in range(rows)]
    return pd.DataFrame(data)
