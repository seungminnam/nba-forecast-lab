"""Static model performance tables transcribed from documented results.

Values mirror docs/experiments.md and docs/model_card.md. This module
performs no computation and reads no files; it exists so the Streamlit Model
Performance tab and its tests share one source of the documented numbers.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ModelPerformanceReport:
    """Documented frozen-model and experiment-history tables."""

    final_metrics: pd.DataFrame
    evaluation_comparison: pd.DataFrame
    baseline_comparison: pd.DataFrame
    training_window_comparison: pd.DataFrame
    calibration_selection: pd.DataFrame


def build_model_performance_report() -> ModelPerformanceReport:
    """Return the documented experiment and final-model result tables."""
    final_metrics = pd.DataFrame(
        [
            {
                "Brier Score": 0.207254,
                "Log Loss": 0.601983,
                "ECE": 0.039914,
                "ROC-AUC": 0.732116,
                "Accuracy": 0.689431,
            }
        ]
    )
    evaluation_comparison = pd.DataFrame(
        [
            {
                "Evaluation": "2025-26 Regular Season",
                "Games": 1230,
                "Brier Score": 0.207254,
                "Log Loss": 0.601983,
                "ECE": 0.039914,
                "ROC-AUC": 0.732116,
                "Accuracy": 0.689431,
            },
            {
                "Evaluation": "2025-26 Playoffs",
                "Games": 85,
                "Brier Score": 0.221755,
                "Log Loss": 0.635268,
                "ECE": 0.082080,
                "ROC-AUC": 0.672452,
                "Accuracy": 0.635294,
            },
        ]
    )

    baseline_comparison = pd.DataFrame(
        [
            {
                "Model": "Constant home rate",
                "Brier Score": 0.24715,
                "Log Loss": 0.68745,
                "ROC-AUC": 0.50000,
                "Accuracy": 0.55447,
            },
            {
                "Model": "Season win percentage",
                "Brier Score": 0.22179,
                "Log Loss": 0.69051,
                "ROC-AUC": 0.71839,
                "Accuracy": 0.66992,
            },
            {
                "Model": "Elo",
                "Brier Score": 0.21360,
                "Log Loss": 0.61797,
                "ROC-AUC": 0.72531,
                "Accuracy": 0.66585,
            },
            {
                "Model": "Logistic Regression",
                "Brier Score": 0.20649,
                "Log Loss": 0.60051,
                "ROC-AUC": 0.73357,
                "Accuracy": 0.68293,
            },
        ]
    )

    training_window_comparison = pd.DataFrame(
        [
            {
                "Model": "Logistic Regression",
                "Training window": "Recent 5",
                "Train rows": 5829,
                "Brier Score": 0.208594,
                "Log Loss": 0.603709,
                "ROC-AUC": 0.730156,
                "Accuracy": 0.678049,
            },
            {
                "Model": "Logistic Regression",
                "Training window": "Decayed full history",
                "Train rows": 10749,
                "Brier Score": 0.208670,
                "Log Loss": 0.603964,
                "ROC-AUC": 0.730329,
                "Accuracy": 0.680488,
            },
            {
                "Model": "Logistic Regression",
                "Training window": "Recent 3",
                "Train rows": 3690,
                "Brier Score": 0.208736,
                "Log Loss": 0.604207,
                "ROC-AUC": 0.730118,
                "Accuracy": 0.678862,
            },
            {
                "Model": "XGBoost",
                "Training window": "Decayed full history",
                "Train rows": 10749,
                "Brier Score": 0.211099,
                "Log Loss": 0.609608,
                "ROC-AUC": 0.723284,
                "Accuracy": 0.653659,
            },
            {
                "Model": "XGBoost",
                "Training window": "Recent 3",
                "Train rows": 3690,
                "Brier Score": 0.211292,
                "Log Loss": 0.610053,
                "ROC-AUC": 0.722403,
                "Accuracy": 0.655285,
            },
            {
                "Model": "XGBoost",
                "Training window": "Recent 5",
                "Train rows": 5829,
                "Brier Score": 0.211721,
                "Log Loss": 0.611173,
                "ROC-AUC": 0.721448,
                "Accuracy": 0.672358,
            },
        ]
    )

    calibration_selection = pd.DataFrame(
        [
            {
                "Method": "Raw",
                "Brier Score": 0.201537,
                "Log Loss": 0.588339,
                "ECE": 0.032448,
                "ROC-AUC": 0.750629,
                "Accuracy": 0.689431,
            },
            {
                "Method": "Isotonic",
                "Brier Score": 0.204388,
                "Log Loss": 0.630123,
                "ECE": 0.037552,
                "ROC-AUC": 0.744941,
                "Accuracy": 0.682927,
            },
            {
                "Method": "Platt",
                "Brier Score": 0.205197,
                "Log Loss": 0.598572,
                "ECE": 0.053973,
                "ROC-AUC": 0.750629,
                "Accuracy": 0.686179,
            },
        ]
    )

    return ModelPerformanceReport(
        final_metrics=final_metrics,
        evaluation_comparison=evaluation_comparison,
        baseline_comparison=baseline_comparison,
        training_window_comparison=training_window_comparison,
        calibration_selection=calibration_selection,
    )
