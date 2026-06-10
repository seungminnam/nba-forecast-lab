"""Interpretable NBA home-win probability baselines."""

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS

PROBABILITY_EPSILON = 1e-6


def constant_home_rate_probability(
    train: pd.DataFrame,
    frame: pd.DataFrame,
) -> pd.Series:
    """Predict the training period's observed home-win rate for every row."""
    probability = float(train["home_win"].mean())
    return _clip(pd.Series(probability, index=frame.index, dtype="float64"))


def season_win_pct_probability(frame: pd.DataFrame) -> pd.Series:
    """Convert home-minus-away season win percentage into a probability."""
    return _clip(0.5 + frame["season_win_pct_diff"].astype(float) / 2)


def elo_probability(frame: pd.DataFrame) -> pd.Series:
    """Return the pre-game Elo home-win probability."""
    return _clip(frame["elo_home_win_probability"].astype(float))


def fit_logistic_regression(train: pd.DataFrame) -> Pipeline:
    """Fit a regularized Logistic Regression on declared model features."""
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000)),
        ]
    )
    model.fit(train[list(MODEL_FEATURE_COLUMNS)], train["home_win"])
    return model


def logistic_regression_probability(
    model: Pipeline,
    frame: pd.DataFrame,
) -> pd.Series:
    """Return fitted Logistic Regression home-win probabilities."""
    probabilities = model.predict_proba(frame[list(MODEL_FEATURE_COLUMNS)])[:, 1]
    return _clip(pd.Series(probabilities, index=frame.index))


def _clip(probabilities: pd.Series) -> pd.Series:
    return probabilities.clip(PROBABILITY_EPSILON, 1 - PROBABILITY_EPSILON)

