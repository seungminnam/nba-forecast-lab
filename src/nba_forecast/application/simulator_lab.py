"""Shared application workflow for assumption-based series simulation."""

from dataclasses import asdict, dataclass

import pandas as pd

from nba_forecast.simulation.series import (
    DEFAULT_SIMULATIONS,
    SeriesGameContext,
    SeriesSimulationResult,
    simulate_best_of_seven,
)


@dataclass(frozen=True)
class SimulatorLabInput:
    """Explicit assumptions for one interactive series simulation."""

    team_a: str
    team_b: str
    team_a_home_win_probability: float
    team_a_away_win_probability: float
    simulations: int = DEFAULT_SIMULATIONS
    seed: int = 2026


@dataclass(frozen=True)
class SimulatorLabOutput:
    """Simulation result and chart-ready tables."""

    inputs: SimulatorLabInput
    result: SeriesSimulationResult
    series_win_table: pd.DataFrame
    outcome_table: pd.DataFrame
    length_table: pd.DataFrame

    def to_report(self) -> dict[str, object]:
        """Return a JSON-serializable report."""
        return {
            "inputs": asdict(self.inputs),
            "result": asdict(self.result),
        }


def run_simulator_lab(inputs: SimulatorLabInput) -> SimulatorLabOutput:
    """Run the shared assumption-based Simulator Lab workflow."""
    _validate_inputs(inputs)

    def home_win_probability(context: SeriesGameContext) -> float:
        if context.home_team == inputs.team_a:
            return inputs.team_a_home_win_probability
        return 1.0 - inputs.team_a_away_win_probability

    result = simulate_best_of_seven(
        inputs.team_a,
        inputs.team_b,
        home_win_probability,
        simulations=inputs.simulations,
        seed=inputs.seed,
    )
    series_win_table = pd.DataFrame(
        {
            "team": [inputs.team_a, inputs.team_b],
            "probability": [
                result.team_a_series_win_probability,
                result.team_b_series_win_probability,
            ],
        }
    )
    outcome_rows = []
    for label, probability in result.outcome_probabilities.items():
        team, _, games = label.rpartition(" in ")
        outcome_rows.append(
            {
                "team": team,
                "games": int(games),
                "probability": probability,
                "label": label,
            }
        )
    outcome_table = pd.DataFrame(outcome_rows)
    length_table = pd.DataFrame(
        {
            "games": list(result.length_probabilities),
            "probability": list(result.length_probabilities.values()),
        }
    )
    return SimulatorLabOutput(
        inputs=inputs,
        result=result,
        series_win_table=series_win_table,
        outcome_table=outcome_table,
        length_table=length_table,
    )


def _validate_inputs(inputs: SimulatorLabInput) -> None:
    if not inputs.team_a.strip() or not inputs.team_b.strip():
        raise ValueError("Team names must be non-empty")
    if inputs.team_a.strip() == inputs.team_b.strip():
        raise ValueError("Team names must be distinct")
    for probability in (
        inputs.team_a_home_win_probability,
        inputs.team_a_away_win_probability,
    ):
        if not 0.0 <= probability <= 1.0:
            raise ValueError("Team A win probabilities must be between 0 and 1")
    if inputs.simulations <= 0:
        raise ValueError("simulations must be greater than zero")
