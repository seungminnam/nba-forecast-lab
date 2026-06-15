from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest

from nba_forecast.application.forecast_retrospective import (
    ForecastOutcome,
    build_forecast_retrospective,
)


def test_build_retrospective_joins_frozen_forecast_to_verified_outcome() -> None:
    retrospective = build_forecast_retrospective(_forecast(), _outcome())

    assert retrospective.predicted_game_winner == "SAS"
    assert retrospective.actual_game_winner == "NYK"
    assert retrospective.predicted_series_winner == "NYK"
    assert retrospective.actual_series_winner == "NYK"
    assert retrospective.game_brier_score == pytest.approx(0.5457**2)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("away_team_abbreviation", "BOS", "teams"),
        ("game_date", pd.Timestamp("2026-06-14"), "date"),
        ("final_team_a_wins", 4, "final series score"),
        ("final_team_b_wins", 3, "final series score"),
    ],
)
def test_build_retrospective_rejects_invalid_outcome(
    field: str,
    value: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_forecast_retrospective(
            _forecast(),
            replace(_outcome(), **{field: value}),
        )


def test_build_retrospective_rejects_game_five_winner_that_differs_from_champion(
) -> None:
    with pytest.raises(ValueError, match="Game 5 winner"):
        build_forecast_retrospective(
            _forecast(),
            replace(_outcome(), home_points=95, away_points=90),
        )


def _forecast() -> SimpleNamespace:
    return SimpleNamespace(
        inputs=SimpleNamespace(
            team_a_abbreviation="SAS",
            team_b_abbreviation="NYK",
        ),
        next_game_forecast=SimpleNamespace(
            game_number=5,
            game_date=pd.Timestamp("2026-06-13"),
            home_team_abbreviation="SAS",
            away_team_abbreviation="NYK",
            home_win_probability=0.5457,
            away_win_probability=0.4543,
        ),
        result=SimpleNamespace(
            team_a_series_win_probability=0.1379,
            team_b_series_win_probability=0.8621,
            expected_games=5.8026,
        ),
    )


def _outcome() -> ForecastOutcome:
    return ForecastOutcome(
        game_id="2026-finals-game-5",
        game_date=pd.Timestamp("2026-06-13"),
        home_team_abbreviation="SAS",
        away_team_abbreviation="NYK",
        home_points=90,
        away_points=94,
        final_team_a_wins=1,
        final_team_b_wins=4,
    )
