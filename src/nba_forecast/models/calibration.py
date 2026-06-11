"""Leakage-safe probability calibration selection and evaluation."""

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from nba_forecast.evaluation.metrics import probability_metrics
from nba_forecast.evaluation.model_comparison import build_training_windows
from nba_forecast.models.baselines import (
    PROBABILITY_EPSILON,
    fit_logistic_regression,
    logistic_regression_probability,
)

CALIBRATION_METHODS = ("raw", "platt", "isotonic")


class ProbabilityCalibrator(Protocol):
    """Transform raw probabilities without accessing model features."""

    def predict(self, probabilities: pd.Series) -> pd.Series:
        """Return calibrated probabilities."""


@dataclass(frozen=True)
class CalibrationExperiment:
    """Selected frozen model and metrics from one temporal experiment."""

    selected_method: str
    selection_metrics: pd.DataFrame
    test_metrics: pd.DataFrame
    model: Pipeline
    calibrator: ProbabilityCalibrator
    training_seasons: tuple[str, ...]


class RawCalibrator:
    """Identity calibration candidate."""

    def predict(self, probabilities: pd.Series) -> pd.Series:
        return _clip(probabilities)


class PlattCalibrator:
    """Logistic mapping from raw to calibrated probability."""

    def __init__(self, model: LogisticRegression) -> None:
        self.model = model

    def predict(self, probabilities: pd.Series) -> pd.Series:
        values = self.model.predict_proba(probabilities.to_numpy().reshape(-1, 1))[:, 1]
        return _clip(pd.Series(values, index=probabilities.index))


class IsotonicCalibrator:
    """Monotonic non-parametric probability mapping."""

    def __init__(self, model: IsotonicRegression) -> None:
        self.model = model

    def predict(self, probabilities: pd.Series) -> pd.Series:
        values = self.model.predict(probabilities.to_numpy())
        return _clip(pd.Series(values, index=probabilities.index))


def split_calibration_period(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chronologically split a validation period into fit and selection halves."""
    ordered = frame.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    if len(ordered) < 4:
        raise ValueError("Calibration period requires at least four rows")
    midpoint = len(ordered) // 2
    return ordered.iloc[:midpoint].copy(), ordered.iloc[midpoint:].copy()


def fit_calibrator(
    method: str,
    probabilities: pd.Series,
    targets: pd.Series,
) -> ProbabilityCalibrator:
    """Fit one calibration method to out-of-time base-model predictions."""
    if method == "raw":
        return RawCalibrator()
    values = probabilities.to_numpy().reshape(-1, 1)
    if method == "platt":
        model = LogisticRegression(max_iter=1000, solver="liblinear")
        model.fit(values, targets)
        return PlattCalibrator(model)
    if method == "isotonic":
        model = IsotonicRegression(out_of_bounds="clip")
        model.fit(probabilities.to_numpy(), targets.to_numpy())
        return IsotonicCalibrator(model)
    raise ValueError(f"Unsupported calibration method: {method}")


def run_calibration_experiment(
    features: pd.DataFrame,
    *,
    validation_season: str,
    test_season: str,
) -> CalibrationExperiment:
    """Select calibration on validation halves, then evaluate test exactly once."""
    validation_window = build_training_windows(
        features,
        validation_season=validation_season,
    )["recent_5"]
    validation = _select_season(features, validation_season)
    base_model = fit_logistic_regression(validation_window.frame)
    validation_predictions = _prediction_frame(base_model, validation)
    calibration_fit, calibration_selection = split_calibration_period(
        validation_predictions
    )

    selection_rows: list[dict[str, Any]] = []
    for method in CALIBRATION_METHODS:
        calibrator = fit_calibrator(
            method,
            calibration_fit["raw_probability"],
            calibration_fit["home_win"],
        )
        probabilities = calibrator.predict(calibration_selection["raw_probability"])
        selection_rows.append(
            {
                "calibration_method": method,
                "calibration_fit_rows": len(calibration_fit),
                "selection_rows": len(calibration_selection),
                **probability_metrics(
                    calibration_selection["home_win"].tolist(),
                    probabilities.tolist(),
                ),
            }
        )
    selection_metrics = (
        pd.DataFrame(selection_rows)
        .sort_values(["brier_score", "log_loss", "calibration_method"])
        .reset_index(drop=True)
    )
    selected_method = str(selection_metrics.iloc[0]["calibration_method"])
    final_calibrator = fit_calibrator(
        selected_method,
        validation_predictions["raw_probability"],
        validation_predictions["home_win"],
    )

    final_window = build_training_windows(
        features,
        validation_season=test_season,
    )["recent_5"]
    final_model = fit_logistic_regression(final_window.frame)
    test = _select_season(features, test_season)
    test_raw = logistic_regression_probability(final_model, test)
    test_calibrated = final_calibrator.predict(test_raw)
    test_rows = []
    for method, probabilities in (
        ("raw", test_raw),
        (selected_method, test_calibrated),
    ):
        test_rows.append(
            {
                "calibration_method": method,
                "test_rows": len(test),
                **probability_metrics(
                    test["home_win"].tolist(),
                    probabilities.tolist(),
                ),
            }
        )

    return CalibrationExperiment(
        selected_method=selected_method,
        selection_metrics=selection_metrics,
        test_metrics=pd.DataFrame(test_rows).drop_duplicates(
            subset=["calibration_method"]
        ),
        model=final_model,
        calibrator=final_calibrator,
        training_seasons=final_window.seasons,
    )


def _prediction_frame(model: Pipeline, frame: pd.DataFrame) -> pd.DataFrame:
    predictions = frame[["game_id", "game_date", "home_win"]].copy()
    predictions["raw_probability"] = logistic_regression_probability(model, frame)
    return predictions


def _select_season(features: pd.DataFrame, season: str) -> pd.DataFrame:
    selected = (
        features.loc[features["season_id"].astype(str) == season]
        .sort_values(["game_date", "game_id"])
        .reset_index(drop=True)
    )
    if selected.empty:
        raise ValueError(f"Season is missing: {season}")
    return selected


def _clip(probabilities: pd.Series) -> pd.Series:
    return probabilities.astype(float).clip(
        PROBABILITY_EPSILON,
        1 - PROBABILITY_EPSILON,
    )
