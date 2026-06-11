import math

from nba_forecast.evaluation.metrics import probability_metrics


def test_probability_metrics_match_known_example() -> None:
    metrics = probability_metrics([1, 0], [0.8, 0.3])

    assert math.isclose(metrics["brier_score"], 0.065)
    assert math.isclose(metrics["log_loss"], 0.2899092476)
    assert metrics["roc_auc"] == 1.0
    assert metrics["accuracy"] == 1.0


def test_probability_metrics_returns_nan_auc_for_one_class() -> None:
    metrics = probability_metrics([1, 1], [0.6, 0.7])

    assert math.isnan(metrics["roc_auc"])


def test_probability_metrics_reports_expected_calibration_error() -> None:
    metrics = probability_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])

    assert math.isclose(metrics["expected_calibration_error"], 0.15)
