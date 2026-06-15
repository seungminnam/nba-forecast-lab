from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from nba_forecast.application import series_replay
from nba_forecast.models import artifacts

APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"


def _run_app() -> AppTest:
    return AppTest.from_file(str(APP_PATH)).run(timeout=10)


def test_streamlit_app_renders_simulator_results() -> None:
    app = _run_app()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Model-Backed Historical Replay",
        "Assumption Lab",
        "Model Performance",
        "Methodology",
    ]
    assert any("NBA FORECAST LAB" in markdown.value for markdown in app.markdown)
    assert any("Assumption-based demo" in markdown.value for markdown in app.markdown)
    assert app.metric[0].label == "Knicks series win"
    assert {
        "Replay context",
        "Series assumptions",
        "Series outcome distribution",
        "Series length distribution",
    }.issubset({subheader.value for subheader in app.subheader})


def test_streamlit_app_shows_distinct_team_validation_error() -> None:
    app = _run_app()

    app.text_input[3].input("Knicks").run()

    assert not app.exception
    assert app.error[0].value == "Team names must be distinct"


def test_streamlit_app_renders_actual_next_game_forecast_and_fair_odds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_exists = Path.exists
    monkeypatch.setattr(
        Path,
        "exists",
        lambda path: (
            True
            if str(path)
            in {
                "data/snapshots/2026-06-10/games.parquet",
                "data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib",
            }
            else original_exists(path)
        ),
    )
    monkeypatch.setattr(pd, "read_parquet", lambda _: pd.DataFrame())
    monkeypatch.setattr(artifacts, "load_model_bundle", lambda _: object())
    monkeypatch.setattr(
        series_replay,
        "run_series_replay",
        lambda *_: _fake_replay_output(),
    )
    app = _run_app()

    app.button[0].click().run()

    assert not app.exception
    assert any(
        "Next Game Forecast · Game 5" in subheader.value
        for subheader in app.subheader
    )
    assert any(metric.label == "SAS next-game win" for metric in app.metric)
    assert any(metric.label == "NYK next-game win" for metric in app.metric)
    assert any(
        "Model-implied fair odds" in caption.value for caption in app.caption
    )
    assert any(
        "not sportsbook prices or betting advice" in info.value for info in app.info
    )


def test_streamlit_app_has_four_tabs() -> None:
    app = _run_app()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Model-Backed Historical Replay",
        "Assumption Lab",
        "Model Performance",
        "Methodology",
    ]


def test_model_performance_tab_renders_documented_metrics_and_tables() -> None:
    app = _run_app()

    performance_tab = app.tabs[2]
    metric_labels = [metric.label for metric in performance_tab.metric]
    assert metric_labels == [
        "Brier Score",
        "Log Loss",
        "ECE",
        "ROC-AUC",
        "Accuracy",
    ]
    assert performance_tab.metric[0].value == "0.2073"
    assert performance_tab.metric[3].value == "0.7321"

    expander_labels = [expander.label for expander in performance_tab.expander]
    assert expander_labels == [
        "Baseline Comparison (Untouched 2025-26 Test)",
        "Training Window & Model Comparison (2024-25 Validation)",
        "Calibration Selection (2024-25 Validation, Second Half)",
    ]


def test_methodology_tab_renders_expected_sections() -> None:
    app = _run_app()

    methodology_tab = app.tabs[3]
    expander_labels = [expander.label for expander in methodology_tab.expander]
    assert expander_labels == [
        "Research Question",
        "Architecture & Data Flow",
        "Leakage Prevention",
        "Model Limitations & Scope",
    ]


def test_dashboard_hero_renders_featured_historical_forecast() -> None:
    app = _run_app()

    assert not app.exception
    markdown = [element.value for element in app.markdown]
    assert any("FEATURED HISTORICAL FORECAST" in value for value in markdown)
    assert any(
        "SAS" in value and "NYK" in value and "54.6%" in value for value in markdown
    )
    assert any(
        "Frozen model Brier" in value and "0.2073" in value for value in markdown
    )
    assert any(
        "Baseline Logistic Regression" in value and "3.33%" in value
        for value in markdown
    )
    assert not any("LIVE FORECAST" in value for value in markdown)


def test_dashboard_hero_omits_forecast_when_snapshot_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_exists = Path.exists
    monkeypatch.setattr(
        Path,
        "exists",
        lambda path: (
            False
            if str(path)
            in {
                "data/snapshots/2026-06-10/games.parquet",
                "data/snapshots/2026-06-10/2026-06-11-recent5-raw.joblib",
            }
            else original_exists(path)
        ),
    )

    app = _run_app()

    assert not app.exception
    markdown = [element.value for element in app.markdown]
    assert not any("FEATURED HISTORICAL FORECAST" in value for value in markdown)
    assert not any("Frozen model Brier" in value for value in markdown)


def test_replay_defaults_match_featured_series() -> None:
    app = _run_app()

    assert not app.exception
    assert app.date_input[0].value == pd.Timestamp("2026-06-11").date()
    assert app.date_input[1].value == pd.Timestamp("2026-06-13").date()
    assert app.text_input[0].value == "SAS"
    assert app.text_input[1].value == "NYK"
    assert app.number_input[0].value == 1610612759
    assert app.number_input[1].value == 1610612752


def test_dashboard_renders_semantic_notices_and_footer() -> None:
    app = _run_app()

    assert not app.exception
    markdown = [element.value for element in app.markdown]
    assert any("ℹ️" in value and "Historical Replay" in value for value in markdown)
    assert any("⚠️" in value and "Assumption-based demo" in value for value in markdown)
    assert any(
        "github.com/seungminnam/nba-forecast-lab" in value
        and "Data snapshot: 2026-06-10" in value
        for value in markdown
    )


def _fake_replay_output() -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            team_a_wins=1,
            team_b_wins=3,
            observed_games=pd.DataFrame(),
            is_complete=False,
        ),
        next_game_forecast=SimpleNamespace(
            game_number=5,
            game_date=pd.Timestamp("2026-06-13"),
            home_team_abbreviation="SAS",
            away_team_abbreviation="NYK",
            home_win_probability=0.5457,
            away_win_probability=0.4543,
            home_fair_odds=SimpleNamespace(decimal=1.8325, american=-120),
            away_fair_odds=SimpleNamespace(decimal=2.2012, american=120),
        ),
        result=SimpleNamespace(
            team_a_series_win_probability=0.1379,
            team_b_series_win_probability=0.8621,
            expected_games=5.8026,
        ),
        outcome_table=pd.DataFrame(
            {
                "team": ["SAS", "NYK"],
                "games": [7, 5],
                "probability": [0.1379, 0.4437],
                "label": ["SAS in 7", "NYK in 5"],
            }
        ),
        length_table=pd.DataFrame(
            {
                "games": [5, 6, 7],
                "probability": [0.4437, 0.31, 0.2463],
            }
        ),
    )
