import pytest

from nba_forecast.application.model_performance import (
    ModelPerformanceReport,
    build_model_performance_report,
)


def test_final_metrics_match_frozen_model_card() -> None:
    report = build_model_performance_report()

    assert isinstance(report, ModelPerformanceReport)
    assert list(report.final_metrics.columns) == [
        "Brier Score",
        "Log Loss",
        "ECE",
        "ROC-AUC",
        "Accuracy",
    ]
    assert len(report.final_metrics) == 1
    final = report.final_metrics.iloc[0]
    assert final["Brier Score"] == pytest.approx(0.207254)
    assert final["Log Loss"] == pytest.approx(0.601983)
    assert final["ECE"] == pytest.approx(0.039914)
    assert final["ROC-AUC"] == pytest.approx(0.732116)
    assert final["Accuracy"] == pytest.approx(0.689431)


def test_baseline_comparison_matches_untouched_test_results() -> None:
    report = build_model_performance_report()

    assert list(report.baseline_comparison["Model"]) == [
        "Constant home rate",
        "Season win percentage",
        "Elo",
        "Logistic Regression",
    ]
    logreg = report.baseline_comparison.iloc[-1]
    assert logreg["Brier Score"] == pytest.approx(0.20649)
    assert logreg["ROC-AUC"] == pytest.approx(0.73357)


def test_training_window_comparison_selects_recent_five_logistic_regression() -> None:
    report = build_model_performance_report()

    assert len(report.training_window_comparison) == 6
    best = report.training_window_comparison.iloc[0]
    assert best["Model"] == "Logistic Regression"
    assert best["Training window"] == "Recent 5"
    assert best["Brier Score"] == pytest.approx(0.208594)


def test_calibration_selection_retains_raw() -> None:
    report = build_model_performance_report()

    assert list(report.calibration_selection["Method"]) == ["Raw", "Isotonic", "Platt"]
    raw = report.calibration_selection.iloc[0]
    assert raw["Brier Score"] == pytest.approx(0.201537)
    assert raw["ECE"] == pytest.approx(0.032448)


def test_evaluation_comparison_includes_measured_playoff_backtest() -> None:
    report = build_model_performance_report()

    assert report.evaluation_comparison["Evaluation"].tolist() == [
        "2025-26 Regular Season",
        "2025-26 Playoffs",
    ]
    playoffs = report.evaluation_comparison.iloc[1]
    assert playoffs["Games"] == 85
    assert playoffs["Brier Score"] == pytest.approx(0.221755)
    assert playoffs["ECE"] == pytest.approx(0.082080)
