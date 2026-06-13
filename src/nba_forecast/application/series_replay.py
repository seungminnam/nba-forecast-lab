"""Historical playoff-series reconstruction and model-backed replay."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from nba_forecast.application.fair_odds import FairOdds, fair_odds_from_probability
from nba_forecast.application.matchup_prediction import (
    MatchupPredictionOutput,
    predict_scheduled_matchup,
)
from nba_forecast.features.matchup_features import ScheduledMatchup
from nba_forecast.models.artifacts import ModelBundle
from nba_forecast.simulation.series import (
    HOME_COURT_SCHEDULE,
    SeriesGameContext,
    SeriesSimulationResult,
    simulate_best_of_seven,
)


@dataclass(frozen=True)
class SeriesReplayInput:
    """Identifiers and cutoff required to reconstruct one playoff series."""

    as_of_date: pd.Timestamp
    next_game_date: pd.Timestamp
    season_id: str
    season_type: str
    season_key: str
    team_a_id: int
    team_a_abbreviation: str
    team_b_id: int
    team_b_abbreviation: str
    simulations: int = 10_000
    seed: int = 2026


@dataclass(frozen=True)
class ObservedSeriesState:
    """Observed playoff-series state strictly before a declared cutoff."""

    team_a_wins: int
    team_b_wins: int
    completed_games: int
    next_game_number: Optional[int]
    next_home_team_id: Optional[int]
    is_complete: bool
    winner_team_id: Optional[int]
    observed_games: pd.DataFrame


@dataclass(frozen=True)
class NextGameForecast:
    """Actual next-game probability and model-implied fair-odds display."""

    game_number: int
    game_date: pd.Timestamp
    home_team_id: int
    home_team_abbreviation: str
    away_team_id: int
    away_team_abbreviation: str
    home_win_probability: float
    away_win_probability: float
    home_fair_odds: FairOdds
    away_fair_odds: FairOdds

    def to_report(self) -> dict[str, object]:
        """Return a JSON-serializable next-game forecast."""
        return {
            "game_number": self.game_number,
            "game_date": pd.Timestamp(self.game_date).date().isoformat(),
            "home_team_id": self.home_team_id,
            "home_team_abbreviation": self.home_team_abbreviation,
            "away_team_id": self.away_team_id,
            "away_team_abbreviation": self.away_team_abbreviation,
            "home_win_probability": self.home_win_probability,
            "away_win_probability": self.away_win_probability,
            "home_fair_odds": asdict(self.home_fair_odds),
            "away_fair_odds": asdict(self.away_fair_odds),
            "market_odds": False,
            "includes_bookmaker_margin": False,
            "betting_recommendation": False,
        }


@dataclass(frozen=True)
class SeriesReplayOutput:
    """Auditable model-backed replay result and chart-ready tables."""

    inputs: SeriesReplayInput
    state: ObservedSeriesState
    replay_timestamp: datetime
    team_a_home_prediction: Optional[MatchupPredictionOutput]
    team_b_home_prediction: Optional[MatchupPredictionOutput]
    next_game_forecast: Optional[NextGameForecast]
    result: Optional[SeriesSimulationResult]
    outcome_table: pd.DataFrame
    length_table: pd.DataFrame

    def to_report(self) -> dict[str, object]:
        """Return a JSON-serializable replay report."""
        observed_games = [
            {
                "game_id": str(game.game_id),
                "game_date": pd.Timestamp(game.game_date).date().isoformat(),
                "home_team_id": int(game.home_team_id),
                "away_team_id": int(game.away_team_id),
                "home_win": int(game.home_win),
            }
            for game in self.state.observed_games.itertuples(index=False)
        ]
        probabilities: Optional[dict[str, object]]
        if self.team_a_home_prediction is None or self.team_b_home_prediction is None:
            probabilities = None
        else:
            probabilities = {
                "team_a_home": self.team_a_home_prediction.home_win_probability,
                "team_b_home": self.team_b_home_prediction.home_win_probability,
                "team_a_home_prediction": self.team_a_home_prediction.to_report(),
                "team_b_home_prediction": self.team_b_home_prediction.to_report(),
            }
        return {
            "replay_timestamp": self.replay_timestamp.isoformat(),
            "as_of_date": pd.Timestamp(self.inputs.as_of_date).date().isoformat(),
            "next_game_date": (
                pd.Timestamp(self.inputs.next_game_date).date().isoformat()
            ),
            "inputs": _replay_input_report(self.inputs),
            "observed_state": {
                "team_a_wins": self.state.team_a_wins,
                "team_b_wins": self.state.team_b_wins,
                "completed_games": self.state.completed_games,
                "next_game_number": self.state.next_game_number,
                "next_home_team_id": self.state.next_home_team_id,
                "is_complete": self.state.is_complete,
                "winner_team_id": self.state.winner_team_id,
                "games": observed_games,
            },
            "next_game_forecast": (
                self.next_game_forecast.to_report()
                if self.next_game_forecast is not None
                else None
            ),
            "probabilities": probabilities,
            "result": asdict(self.result) if self.result is not None else None,
            "assumptions": {
                "venue_probabilities_frozen_at_as_of_date": True,
                "future_team_state_updates_modeled": False,
                "psychological_adjustment_modeled": False,
            },
        }


def reconstruct_series_state(
    games: pd.DataFrame,
    inputs: SeriesReplayInput,
) -> ObservedSeriesState:
    """Return the observed series state using only games before ``as_of_date``."""
    _validate_replay_inputs(inputs)
    history = games.copy()
    history["game_date"] = pd.to_datetime(history["game_date"], errors="raise")
    cutoff = pd.Timestamp(inputs.as_of_date).normalize()
    team_ids = {inputs.team_a_id, inputs.team_b_id}
    pair_matches = history.apply(
        lambda row: {int(row["home_team_id"]), int(row["away_team_id"])} == team_ids,
        axis=1,
    )
    observed = history.loc[
        (history["season_key"].astype(str) == inputs.season_key)
        & (history["season_type"].astype(str) == "Playoffs")
        & (history["game_date"] < cutoff)
        & pair_matches
    ].sort_values(["game_date", "game_id"], ignore_index=True)
    if len(observed) > len(HOME_COURT_SCHEDULE):
        raise ValueError("observed series cannot contain more than seven games")

    team_a_wins = 0
    team_b_wins = 0
    for game_index, game in enumerate(observed.itertuples(index=False)):
        expected_home = (
            inputs.team_a_id
            if HOME_COURT_SCHEDULE[game_index] == "A"
            else inputs.team_b_id
        )
        if int(game.home_team_id) != expected_home:
            raise ValueError(
                "observed games do not match the declared home-court schedule"
            )
        if team_a_wins == 4 or team_b_wins == 4:
            raise ValueError("observed games exist after the series was complete")

        home_winner_id = int(game.home_team_id)
        away_winner_id = int(game.away_team_id)
        winner_id = home_winner_id if int(game.home_win) == 1 else away_winner_id
        if winner_id == inputs.team_a_id:
            team_a_wins += 1
        else:
            team_b_wins += 1

    completed_games = len(observed)
    is_complete = team_a_wins == 4 or team_b_wins == 4
    winner_team_id = (
        inputs.team_a_id
        if team_a_wins == 4
        else inputs.team_b_id if team_b_wins == 4 else None
    )
    next_game_number = None if is_complete else completed_games + 1
    if next_game_number is None:
        next_home_team_id = None
    else:
        next_home_team_id = (
            inputs.team_a_id
            if HOME_COURT_SCHEDULE[next_game_number - 1] == "A"
            else inputs.team_b_id
        )
    return ObservedSeriesState(
        team_a_wins=team_a_wins,
        team_b_wins=team_b_wins,
        completed_games=completed_games,
        next_game_number=next_game_number,
        next_home_team_id=next_home_team_id,
        is_complete=is_complete,
        winner_team_id=winner_team_id,
        observed_games=observed,
    )


def run_series_replay(
    games: pd.DataFrame,
    inputs: SeriesReplayInput,
    bundle: ModelBundle,
    *,
    replay_timestamp: Optional[datetime] = None,
) -> SeriesReplayOutput:
    """Reconstruct and simulate one playoff series from a historical cutoff."""
    state = reconstruct_series_state(games, inputs)
    timestamp = replay_timestamp or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("replay_timestamp must include a timezone")
    timestamp = timestamp.astimezone(timezone.utc)
    if state.is_complete:
        return SeriesReplayOutput(
            inputs=inputs,
            state=state,
            replay_timestamp=timestamp,
            team_a_home_prediction=None,
            team_b_home_prediction=None,
            next_game_forecast=None,
            result=None,
            outcome_table=pd.DataFrame(
                columns=["team", "games", "probability", "label"]
            ),
            length_table=pd.DataFrame(columns=["games", "probability"]),
        )

    team_a_home_prediction = predict_scheduled_matchup(
        games,
        _scheduled_matchup(inputs, home_team="A"),
        as_of_date=inputs.as_of_date,
        bundle=bundle,
        prediction_timestamp=timestamp,
    )
    team_b_home_prediction = predict_scheduled_matchup(
        games,
        _scheduled_matchup(inputs, home_team="B"),
        as_of_date=inputs.as_of_date,
        bundle=bundle,
        prediction_timestamp=timestamp,
    )
    next_game_forecast = _next_game_forecast(
        inputs,
        state,
        team_a_home_prediction,
        team_b_home_prediction,
    )

    def home_win_probability(context: SeriesGameContext) -> float:
        if context.home_team == inputs.team_a_abbreviation:
            return team_a_home_prediction.home_win_probability
        return team_b_home_prediction.home_win_probability

    result = simulate_best_of_seven(
        inputs.team_a_abbreviation,
        inputs.team_b_abbreviation,
        home_win_probability,
        simulations=inputs.simulations,
        seed=inputs.seed,
        initial_team_a_wins=state.team_a_wins,
        initial_team_b_wins=state.team_b_wins,
    )
    return SeriesReplayOutput(
        inputs=inputs,
        state=state,
        replay_timestamp=timestamp,
        team_a_home_prediction=team_a_home_prediction,
        team_b_home_prediction=team_b_home_prediction,
        next_game_forecast=next_game_forecast,
        result=result,
        outcome_table=_outcome_table(result),
        length_table=pd.DataFrame(
            {
                "games": list(result.length_probabilities),
                "probability": list(result.length_probabilities.values()),
            }
        ),
    )


def _next_game_forecast(
    inputs: SeriesReplayInput,
    state: ObservedSeriesState,
    team_a_home_prediction: MatchupPredictionOutput,
    team_b_home_prediction: MatchupPredictionOutput,
) -> NextGameForecast:
    if state.next_game_number is None or state.next_home_team_id is None:
        raise ValueError("active series must have a next game")
    prediction = (
        team_a_home_prediction
        if state.next_home_team_id == inputs.team_a_id
        else team_b_home_prediction
    )
    return NextGameForecast(
        game_number=state.next_game_number,
        game_date=pd.Timestamp(inputs.next_game_date),
        home_team_id=prediction.matchup.home_team_id,
        home_team_abbreviation=prediction.matchup.home_team_abbreviation,
        away_team_id=prediction.matchup.away_team_id,
        away_team_abbreviation=prediction.matchup.away_team_abbreviation,
        home_win_probability=prediction.home_win_probability,
        away_win_probability=prediction.away_win_probability,
        home_fair_odds=fair_odds_from_probability(prediction.home_win_probability),
        away_fair_odds=fair_odds_from_probability(prediction.away_win_probability),
    )


def _scheduled_matchup(
    inputs: SeriesReplayInput,
    *,
    home_team: str,
) -> ScheduledMatchup:
    team_a_home = home_team == "A"
    return ScheduledMatchup(
        game_id=f"replay-{home_team.lower()}-home",
        game_date=pd.Timestamp(inputs.next_game_date),
        season_id=inputs.season_id,
        season_type=inputs.season_type,
        season_key=inputs.season_key,
        home_team_id=inputs.team_a_id if team_a_home else inputs.team_b_id,
        away_team_id=inputs.team_b_id if team_a_home else inputs.team_a_id,
        home_team_abbreviation=(
            inputs.team_a_abbreviation if team_a_home else inputs.team_b_abbreviation
        ),
        away_team_abbreviation=(
            inputs.team_b_abbreviation if team_a_home else inputs.team_a_abbreviation
        ),
    )


def _outcome_table(result: SeriesSimulationResult) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, probability in result.outcome_probabilities.items():
        team, _, games = label.rpartition(" in ")
        rows.append(
            {
                "team": team,
                "games": int(games),
                "probability": probability,
                "label": label,
            }
        )
    return pd.DataFrame(rows)


def _replay_input_report(inputs: SeriesReplayInput) -> dict[str, object]:
    return {
        "season_id": inputs.season_id,
        "season_type": inputs.season_type,
        "season_key": inputs.season_key,
        "team_a_id": inputs.team_a_id,
        "team_a_abbreviation": inputs.team_a_abbreviation,
        "team_b_id": inputs.team_b_id,
        "team_b_abbreviation": inputs.team_b_abbreviation,
        "simulations": inputs.simulations,
        "seed": inputs.seed,
    }


def _validate_replay_inputs(inputs: SeriesReplayInput) -> None:
    cutoff = pd.Timestamp(inputs.as_of_date).normalize()
    next_game_date = pd.Timestamp(inputs.next_game_date).normalize()
    if next_game_date < cutoff:
        raise ValueError("next_game_date must be on or after as_of_date")
    if inputs.season_type != "Playoffs":
        raise ValueError("Historical Replay requires season_type=Playoffs")
    if inputs.team_a_id == inputs.team_b_id:
        raise ValueError("series teams must differ")
    if not inputs.team_a_abbreviation.strip() or not inputs.team_b_abbreviation.strip():
        raise ValueError("team abbreviations must be non-empty")
    if inputs.simulations <= 0:
        raise ValueError("simulations must be greater than zero")
