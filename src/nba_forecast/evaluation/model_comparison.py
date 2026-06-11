"""Compare model classes and historical training windows."""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from nba_forecast.evaluation.metrics import probability_metrics
from nba_forecast.models.baselines import (
    fit_logistic_regression,
    logistic_regression_probability,
)
from nba_forecast.models.xgboost_model import fit_xgboost, xgboost_probability


@dataclass(frozen=True)
class TrainingWindow:
    """One chronological training frame and its optional sample weights."""

    name: str
    seasons: tuple[str, ...]
    frame: pd.DataFrame
    sample_weight: Optional[pd.Series]


def build_training_windows(
    features: pd.DataFrame,
    *,
    validation_season: str,
    annual_decay: float = 0.8,
) -> dict[str, TrainingWindow]:
    """Build recent and decayed windows using only pre-validation seasons."""
    if not 0 < annual_decay <= 1:
        raise ValueError("annual_decay must be greater than 0 and at most 1")

    available_seasons = sorted(features["season_id"].astype(str).unique())
    if validation_season not in available_seasons:
        raise ValueError(f"Validation season is missing: {validation_season}")

    training_seasons = tuple(
        season for season in available_seasons if season < validation_season
    )
    if not training_seasons:
        raise ValueError("At least one pre-validation training season is required")

    windows: dict[str, TrainingWindow] = {}
    for size in (3, 5):
        seasons = training_seasons[-size:]
        name = f"recent_{size}"
        windows[name] = TrainingWindow(
            name=name,
            seasons=seasons,
            frame=_select_seasons(features, seasons),
            sample_weight=None,
        )

    season_weights = {
        season: annual_decay ** (len(training_seasons) - position - 1)
        for position, season in enumerate(training_seasons)
    }
    full_history = _select_seasons(features, training_seasons)
    windows["decayed_full_history"] = TrainingWindow(
        name="decayed_full_history",
        seasons=training_seasons,
        frame=full_history,
        sample_weight=full_history["season_id"].astype(str).map(season_weights),
    )
    return windows


def compare_models_by_training_window(
    features: pd.DataFrame,
    *,
    validation_season: str,
    annual_decay: float = 0.8,
) -> pd.DataFrame:
    """Evaluate Logistic Regression and XGBoost on one validation season."""
    validation = _select_seasons(features, (validation_season,))
    if validation.empty:
        raise ValueError(f"Validation season is missing: {validation_season}")

    rows: list[dict[str, object]] = []
    for window in build_training_windows(
        features,
        validation_season=validation_season,
        annual_decay=annual_decay,
    ).values():
        models = {
            "logistic_regression": (
                fit_logistic_regression(
                    window.frame,
                    sample_weight=window.sample_weight,
                ),
                logistic_regression_probability,
            ),
            "xgboost": (
                fit_xgboost(
                    window.frame,
                    sample_weight=window.sample_weight,
                ),
                xgboost_probability,
            ),
        }
        for model_name, (model, probability_function) in models.items():
            probabilities = probability_function(model, validation)
            rows.append(
                {
                    "model": model_name,
                    "training_window": window.name,
                    "train_seasons": ",".join(window.seasons),
                    "train_rows": len(window.frame),
                    "validation_season": validation_season,
                    "validation_rows": len(validation),
                    **probability_metrics(
                        validation["home_win"].tolist(),
                        probabilities.tolist(),
                    ),
                }
            )
    return pd.DataFrame(rows)


def _select_seasons(features: pd.DataFrame, seasons: tuple[str, ...]) -> pd.DataFrame:
    return (
        features.loc[features["season_id"].astype(str).isin(seasons)]
        .sort_values(["game_date", "game_id"])
        .reset_index(drop=True)
    )
