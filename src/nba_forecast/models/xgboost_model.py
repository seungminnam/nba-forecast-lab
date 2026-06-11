"""Conservative XGBoost probability model."""

from typing import Optional

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS
from nba_forecast.models.baselines import PROBABILITY_EPSILON


def fit_xgboost(
    train: pd.DataFrame,
    *,
    sample_weight: Optional[pd.Series] = None,
) -> Pipeline:
    """Fit a fixed-configuration XGBoost model on declared model features."""
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                XGBClassifier(
                    n_estimators=300,
                    max_depth=3,
                    learning_rate=0.03,
                    min_child_weight=5,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    reg_lambda=1.0,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ]
    )
    fit_params = (
        {"classifier__sample_weight": sample_weight}
        if sample_weight is not None
        else {}
    )
    model.fit(
        train[list(MODEL_FEATURE_COLUMNS)],
        train["home_win"],
        **fit_params,
    )
    return model


def xgboost_probability(model: Pipeline, frame: pd.DataFrame) -> pd.Series:
    """Return fitted XGBoost home-win probabilities."""
    probabilities = model.predict_proba(frame[list(MODEL_FEATURE_COLUMNS)])[:, 1]
    return pd.Series(probabilities, index=frame.index).clip(
        PROBABILITY_EPSILON,
        1 - PROBABILITY_EPSILON,
    )
