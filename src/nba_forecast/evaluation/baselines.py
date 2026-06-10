"""Comparable probability baseline evaluation."""

import pandas as pd

from nba_forecast.evaluation.metrics import probability_metrics
from nba_forecast.models.baselines import (
    constant_home_rate_probability,
    elo_probability,
    fit_logistic_regression,
    logistic_regression_probability,
    season_win_pct_probability,
)


def evaluate_baselines(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Evaluate all initial baselines against identical test rows."""
    logistic_model = fit_logistic_regression(train)
    predictions = {
        "constant_home_rate": constant_home_rate_probability(train, test),
        "season_win_pct": season_win_pct_probability(test),
        "elo": elo_probability(test),
        "logistic_regression": logistic_regression_probability(logistic_model, test),
    }
    rows = [
        {
            "model": model_name,
            **probability_metrics(test["home_win"].tolist(), probabilities.tolist()),
        }
        for model_name, probabilities in predictions.items()
    ]
    return pd.DataFrame(rows)

