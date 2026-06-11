import math

import pytest

from nba_forecast.application.simulator_lab import (
    SimulatorLabInput,
    run_simulator_lab,
)


def test_simulator_lab_converts_team_a_venue_probabilities() -> None:
    output = run_simulator_lab(
        SimulatorLabInput(
            team_a="Knicks",
            team_b="Spurs",
            team_a_home_win_probability=1.0,
            team_a_away_win_probability=1.0,
            simulations=10,
            seed=7,
        )
    )

    assert output.result.team_a_series_win_probability == 1.0
    assert output.result.outcome_probabilities["Knicks in 4"] == 1.0


def test_simulator_lab_returns_chart_ready_probability_tables() -> None:
    output = run_simulator_lab(
        SimulatorLabInput(
            team_a="Knicks",
            team_b="Spurs",
            team_a_home_win_probability=0.62,
            team_a_away_win_probability=0.47,
            simulations=1_000,
            seed=2026,
        )
    )

    assert output.series_win_table["team"].tolist() == ["Knicks", "Spurs"]
    assert math.isclose(output.series_win_table["probability"].sum(), 1.0)
    assert set(output.outcome_table.columns) == {
        "team",
        "games",
        "probability",
        "label",
    }
    assert output.length_table["games"].tolist() == [4, 5, 6, 7]
    assert math.isclose(output.length_table["probability"].sum(), 1.0)


def test_simulator_lab_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="distinct"):
        run_simulator_lab(
            SimulatorLabInput(
                team_a="Knicks",
                team_b="Knicks",
                team_a_home_win_probability=0.6,
                team_a_away_win_probability=0.4,
            )
        )
