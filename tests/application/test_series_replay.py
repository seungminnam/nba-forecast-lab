from datetime import datetime, timezone

import pandas as pd
import pytest

from nba_forecast.application.series_replay import (
    SeriesReplayInput,
    reconstruct_series_state,
    run_series_replay,
)
from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS
from nba_forecast.models.artifacts import ModelBundle, ModelBundleMetadata
from nba_forecast.models.baselines import fit_logistic_regression
from nba_forecast.models.calibration import RawCalibrator


def test_reconstruct_series_state_excludes_games_on_and_after_cutoff() -> None:
    inputs = _replay_inputs(as_of_date="2026-06-10")

    state = reconstruct_series_state(_games(), inputs)

    assert state.team_a_wins == 1
    assert state.team_b_wins == 2
    assert state.completed_games == 3
    assert state.next_game_number == 4
    assert state.next_home_team_id == 2
    assert state.is_complete is False
    assert state.observed_games["game_id"].tolist() == [
        "finals-1",
        "finals-2",
        "finals-3",
    ]


def test_reconstruct_series_state_starts_before_game_one() -> None:
    state = reconstruct_series_state(
        _games(),
        _replay_inputs(as_of_date="2026-06-03"),
    )

    assert state.team_a_wins == 0
    assert state.team_b_wins == 0
    assert state.completed_games == 0
    assert state.next_game_number == 1
    assert state.next_home_team_id == 1


def test_reconstruct_series_state_rejects_wrong_home_court_owner() -> None:
    with pytest.raises(ValueError, match="home-court schedule"):
        reconstruct_series_state(
            _games(),
            _replay_inputs(
                as_of_date="2026-06-10",
                team_a_id=2,
                team_a_abbreviation="BET",
                team_b_id=1,
                team_b_abbreviation="ALP",
            ),
        )


def test_model_backed_replay_uses_observed_score_and_two_frozen_probabilities() -> None:
    inputs = _replay_inputs(as_of_date="2026-06-10")

    output = run_series_replay(
        _games(),
        inputs,
        _bundle(),
        replay_timestamp=datetime(2026, 6, 13, 0, 0, tzinfo=timezone.utc),
    )
    report = output.to_report()

    assert output.state.team_a_wins == 1
    assert output.state.team_b_wins == 2
    assert output.result is not None
    assert output.result.outcome_probabilities["ALP in 4"] == 0.0
    assert output.team_a_home_prediction is not None
    assert output.team_b_home_prediction is not None
    assert report["replay_timestamp"] == "2026-06-13T00:00:00+00:00"
    assert report["observed_state"]["next_game_number"] == 4
    assert report["probabilities"]["team_a_home"] == (
        output.team_a_home_prediction.home_win_probability
    )
    assert report["probabilities"]["team_b_home"] == (
        output.team_b_home_prediction.home_win_probability
    )


def test_model_backed_replay_ignores_games_on_and_after_cutoff() -> None:
    inputs = _replay_inputs(as_of_date="2026-06-10")
    games = _games()
    original = run_series_replay(games, inputs, _bundle())
    changed = games.copy()
    changed.loc[
        changed["game_date"] >= pd.Timestamp("2026-06-10"),
        ["home_win", "home_points", "away_points"],
    ] = [1, 140, 80]

    rebuilt = run_series_replay(changed, inputs, _bundle())

    assert rebuilt.state.team_a_wins == original.state.team_a_wins
    assert rebuilt.state.team_b_wins == original.state.team_b_wins
    assert rebuilt.team_a_home_prediction is not None
    assert original.team_a_home_prediction is not None
    assert rebuilt.team_b_home_prediction is not None
    assert original.team_b_home_prediction is not None
    assert (
        rebuilt.team_a_home_prediction.home_win_probability
        == original.team_a_home_prediction.home_win_probability
    )
    assert (
        rebuilt.team_b_home_prediction.home_win_probability
        == original.team_b_home_prediction.home_win_probability
    )
    assert rebuilt.result == original.result


def test_completed_series_reports_observed_winner_without_simulation() -> None:
    games = _games()
    game_five = games.iloc[[0]].copy()
    game_five["game_id"] = "finals-5"
    game_five["game_date"] = pd.Timestamp("2026-06-13")
    game_five["home_win"] = 0
    game_six = games.iloc[[2]].copy()
    game_six["game_id"] = "finals-6"
    game_six["game_date"] = pd.Timestamp("2026-06-15")
    game_six["home_win"] = 1
    games = pd.concat([games, game_five, game_six], ignore_index=True)

    output = run_series_replay(
        games,
        _replay_inputs(as_of_date="2026-06-16"),
        _bundle(),
    )

    assert output.state.is_complete is True
    assert output.state.winner_team_id == 2
    assert output.team_a_home_prediction is None
    assert output.team_b_home_prediction is None
    assert output.result is None
    assert output.to_report()["probabilities"] is None


def _replay_inputs(
    *,
    as_of_date: str,
    team_a_id: int = 1,
    team_a_abbreviation: str = "ALP",
    team_b_id: int = 2,
    team_b_abbreviation: str = "BET",
) -> SeriesReplayInput:
    return SeriesReplayInput(
        as_of_date=pd.Timestamp(as_of_date),
        next_game_date=pd.Timestamp(as_of_date),
        season_id="42025",
        season_type="Playoffs",
        season_key="2025-26",
        team_a_id=team_a_id,
        team_a_abbreviation=team_a_abbreviation,
        team_b_id=team_b_id,
        team_b_abbreviation=team_b_abbreviation,
        simulations=100,
        seed=7,
    )


def _games() -> pd.DataFrame:
    rows = []
    outcomes = [
        ("finals-1", "2026-06-03", 1, 2, 0),
        ("finals-2", "2026-06-05", 1, 2, 1),
        ("finals-3", "2026-06-08", 2, 1, 1),
        ("finals-4", "2026-06-10", 2, 1, 0),
    ]
    for game_id, date, home_id, away_id, home_win in outcomes:
        rows.append(
            {
                "game_id": game_id,
                "game_date": pd.Timestamp(date),
                "season_id": "42025",
                "season_type": "Playoffs",
                "season_key": "2025-26",
                "home_team_id": home_id,
                "away_team_id": away_id,
                "home_team_abbreviation": "ALP" if home_id == 1 else "BET",
                "away_team_abbreviation": "ALP" if away_id == 1 else "BET",
                "home_points": 110,
                "away_points": 100,
                "home_fga": 88,
                "away_fga": 90,
                "home_fgm": 42,
                "away_fgm": 39,
                "home_fta": 20,
                "away_fta": 18,
                "home_oreb": 10,
                "away_oreb": 9,
                "home_tov": 12,
                "away_tov": 14,
                "home_win": home_win,
            }
        )
    return pd.DataFrame(rows)


def _bundle() -> ModelBundle:
    rows = 20
    frame = pd.DataFrame(
        {
            feature: [
                ((-1) ** index) * (position + 1) / 10
                for index in range(rows)
            ]
            for position, feature in enumerate(MODEL_FEATURE_COLUMNS)
        }
    )
    frame["home_win"] = [index % 2 for index in range(rows)]
    metadata = ModelBundleMetadata(
        version="series-replay-test",
        created_at=datetime(2026, 6, 13, tzinfo=timezone.utc).isoformat(),
        base_model="logistic_regression",
        calibration_method="raw",
        feature_columns=MODEL_FEATURE_COLUMNS,
        training_seasons=("22025",),
        calibration_season="22025",
        test_season="22025",
        metrics={"brier_score": 0.2},
    )
    return ModelBundle(
        model=fit_logistic_regression(frame),
        calibrator=RawCalibrator(),
        metadata=metadata,
    )
