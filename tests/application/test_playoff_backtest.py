from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from nba_forecast.application import playoff_backtest
from nba_forecast.application.playoff_backtest import (
    PlayoffBacktestInput,
    run_playoff_backtest,
)
from nba_forecast.evaluation.metrics import probability_metrics


def test_run_playoff_backtest_builds_chronological_predictions_and_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        playoff_backtest,
        "predict_scheduled_matchup",
        _predict_from_prior_home_wins,
    )

    output = run_playoff_backtest(_games(), _inputs(), _bundle())

    assert output.predictions["game_id"].tolist() == ["p1", "p2", "p3"]
    probabilities = [1.0, 1.0, 2 / 3]
    assert output.predictions["home_win_probability"].tolist() == probabilities
    assert output.predictions["home_win"].tolist() == [1, 0, 1]
    assert output.predictions["brier_contribution"].tolist() == pytest.approx(
        [0.0, 1.0, 1 / 9]
    )
    assert output.predictions["predicted_correct"].tolist() == [True, False, True]
    assert output.metrics == probability_metrics([1, 0, 1], probabilities)
    assert output.model_version == "frozen-test"
    assert output.feature_version == "features-test"


def test_run_playoff_backtest_ignores_target_and_future_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        playoff_backtest,
        "predict_scheduled_matchup",
        _predict_from_prior_home_wins,
    )
    games = _games()
    original = run_playoff_backtest(games, _inputs(), _bundle())
    changed = games.copy()
    changed.loc[changed["game_date"] >= pd.Timestamp("2026-04-22"), "home_win"] = 1

    rebuilt = run_playoff_backtest(changed, _inputs(), _bundle())

    original_probabilities = original.predictions["home_win_probability"]
    rebuilt_probabilities = rebuilt.predictions["home_win_probability"]
    assert rebuilt_probabilities.iloc[0] == original_probabilities.iloc[0]
    assert rebuilt_probabilities.iloc[1] == original_probabilities.iloc[1]


def test_run_playoff_backtest_rejects_invalid_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        playoff_backtest,
        "predict_scheduled_matchup",
        _predict_from_prior_home_wins,
    )

    cases = [
        (pd.DataFrame(), PlayoffBacktestInput("2025-26", "42025"), "empty"),
        (_games(), PlayoffBacktestInput("2024-25", "42024"), "no playoff games"),
        (_games(), PlayoffBacktestInput("2025-26", "42024"), "season context"),
        (
            pd.concat([_games(), _games().loc[lambda frame: frame.game_id == "p1"]]),
            PlayoffBacktestInput("2025-26", "42025"),
            "duplicate",
        ),
        (
            _games().assign(home_win=float("nan")),
            PlayoffBacktestInput("2025-26", "42025"),
            "complete outcomes",
        ),
    ]
    for games, inputs, message in cases:
        with pytest.raises(ValueError, match=message):
            run_playoff_backtest(games, inputs, _bundle())


def _predict_from_prior_home_wins(
    completed_games: pd.DataFrame,
    matchup: SimpleNamespace,
    *,
    as_of_date: pd.Timestamp,
    bundle: SimpleNamespace,
) -> SimpleNamespace:
    history = completed_games.loc[
        pd.to_datetime(completed_games["game_date"]) < pd.Timestamp(as_of_date)
    ]
    probability = float(history["home_win"].mean()) if not history.empty else 0.5
    return SimpleNamespace(
        matchup=matchup,
        model_version=bundle.metadata.version,
        feature_version="features-test",
        home_win_probability=probability,
        away_win_probability=1.0 - probability,
        prediction_timestamp=datetime(2026, 6, 15, tzinfo=timezone.utc),
    )


def _inputs() -> PlayoffBacktestInput:
    return PlayoffBacktestInput(season_key="2025-26", season_id="42025")


def _bundle() -> SimpleNamespace:
    return SimpleNamespace(metadata=SimpleNamespace(version="frozen-test"))


def _games() -> pd.DataFrame:
    rows = [
        ("r1", "2026-04-18", "22025", "Regular Season", 1),
        ("p2", "2026-04-22", "42025", "Playoffs", 0),
        ("p1", "2026-04-20", "42025", "Playoffs", 1),
        ("p3", "2026-04-24", "42025", "Playoffs", 1),
    ]
    return pd.DataFrame(
        [
            {
                "game_id": game_id,
                "game_date": pd.Timestamp(game_date),
                "season_id": season_id,
                "season_type": season_type,
                "season_key": "2025-26",
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team_abbreviation": "AAA",
                "away_team_abbreviation": "BBB",
                "home_win": home_win,
            }
            for game_id, game_date, season_id, season_type, home_win in rows
        ]
    )
