from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from nba_forecast.application import series_replay
from nba_forecast.models import artifacts

APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"


def test_streamlit_app_renders_simulator_results() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()

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
    app = AppTest.from_file(str(APP_PATH)).run()

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
    app = AppTest.from_file(str(APP_PATH)).run()

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
