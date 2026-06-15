"""Join one frozen pre-game forecast to one verified completed outcome."""

from dataclasses import dataclass

import pandas as pd

from nba_forecast.application.series_replay import SeriesReplayOutput


@dataclass(frozen=True)
class ForecastOutcome:
    """Verified result recorded separately from the pre-game snapshot."""

    game_id: str
    game_date: pd.Timestamp
    home_team_abbreviation: str
    away_team_abbreviation: str
    home_points: int
    away_points: int
    final_team_a_wins: int
    final_team_b_wins: int


@dataclass(frozen=True)
class ForecastRetrospective:
    """Auditable comparison between a frozen forecast and its outcome."""

    forecast: SeriesReplayOutput
    outcome: ForecastOutcome
    predicted_game_winner: str
    actual_game_winner: str
    predicted_series_winner: str
    actual_series_winner: str
    game_brier_score: float


def build_forecast_retrospective(
    forecast: SeriesReplayOutput,
    outcome: ForecastOutcome,
) -> ForecastRetrospective:
    """Validate and compare one frozen next-game forecast with its outcome."""
    next_game = forecast.next_game_forecast
    result = forecast.result
    if next_game is None or result is None:
        raise ValueError("forecast must include an active next game and series result")

    forecast_teams = {
        next_game.home_team_abbreviation,
        next_game.away_team_abbreviation,
    }
    outcome_teams = {
        outcome.home_team_abbreviation,
        outcome.away_team_abbreviation,
    }
    if forecast_teams != outcome_teams:
        raise ValueError("forecast and outcome teams must match")
    if (
        next_game.home_team_abbreviation != outcome.home_team_abbreviation
        or next_game.away_team_abbreviation != outcome.away_team_abbreviation
    ):
        raise ValueError("forecast and outcome venue directions must match")
    if pd.Timestamp(next_game.game_date).normalize() != pd.Timestamp(
        outcome.game_date
    ).normalize():
        raise ValueError("forecast and outcome date must match")
    if outcome.home_points == outcome.away_points:
        raise ValueError("completed game outcome cannot be tied")

    final_wins = (outcome.final_team_a_wins, outcome.final_team_b_wins)
    if sum(wins == 4 for wins in final_wins) != 1 or any(
        wins not in range(5) for wins in final_wins
    ):
        raise ValueError("final series score must contain one four-win team")
    if sum(final_wins) != next_game.game_number:
        raise ValueError("final series score must end on the forecasted game")

    predicted_game_winner = (
        next_game.home_team_abbreviation
        if next_game.home_win_probability >= next_game.away_win_probability
        else next_game.away_team_abbreviation
    )
    actual_home_win = outcome.home_points > outcome.away_points
    actual_game_winner = (
        outcome.home_team_abbreviation
        if actual_home_win
        else outcome.away_team_abbreviation
    )

    predicted_series_winner = (
        forecast.inputs.team_a_abbreviation
        if result.team_a_series_win_probability
        >= result.team_b_series_win_probability
        else forecast.inputs.team_b_abbreviation
    )
    actual_series_winner = (
        forecast.inputs.team_a_abbreviation
        if outcome.final_team_a_wins == 4
        else forecast.inputs.team_b_abbreviation
    )
    if actual_game_winner != actual_series_winner:
        raise ValueError("Game 5 winner must match the final series winner")

    actual_home_win_indicator = 1.0 if actual_home_win else 0.0
    game_brier_score = (
        next_game.home_win_probability - actual_home_win_indicator
    ) ** 2
    return ForecastRetrospective(
        forecast=forecast,
        outcome=outcome,
        predicted_game_winner=predicted_game_winner,
        actual_game_winner=actual_game_winner,
        predicted_series_winner=predicted_series_winner,
        actual_series_winner=actual_series_winner,
        game_brier_score=game_brier_score,
    )
