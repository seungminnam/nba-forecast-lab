import math

import pytest

from nba_forecast.simulation.series import (
    HOME_COURT_SCHEDULE,
    SeriesGameContext,
    simulate_best_of_seven,
)


def test_home_court_schedule_matches_nba_best_of_seven_order() -> None:
    assert HOME_COURT_SCHEDULE == ("A", "A", "B", "B", "A", "B", "A")


def test_simulation_stops_when_team_reaches_four_wins() -> None:
    contexts: list[SeriesGameContext] = []

    def team_a_always_wins(context: SeriesGameContext) -> float:
        contexts.append(context)
        return 1.0 if context.home_team == "Team A" else 0.0

    result = simulate_best_of_seven(
        "Team A",
        "Team B",
        team_a_always_wins,
        simulations=3,
        seed=7,
    )

    assert len(contexts) == 12
    assert result.team_a_series_win_probability == 1.0
    assert result.outcome_probabilities["Team A in 4"] == 1.0
    assert result.length_probabilities == {4: 1.0, 5: 0.0, 6: 0.0, 7: 0.0}
    assert result.expected_games == 4.0


def test_seeded_simulation_is_reproducible() -> None:
    def home_probability(_: SeriesGameContext) -> float:
        return 0.6

    first = simulate_best_of_seven(
        "Team A",
        "Team B",
        home_probability,
        simulations=1_000,
        seed=42,
    )
    second = simulate_best_of_seven(
        "Team A",
        "Team B",
        home_probability,
        simulations=1_000,
        seed=42,
    )

    assert first == second


def test_simulation_passes_home_court_order_and_pregame_score_to_provider() -> None:
    contexts: list[SeriesGameContext] = []
    team_a_wins_by_game = (True, False, True, False, True, False, True)

    def force_seven_games(context: SeriesGameContext) -> float:
        contexts.append(context)
        team_a_wins = team_a_wins_by_game[context.game_number - 1]
        home_wins = team_a_wins == (context.home_team == "Team A")
        return 1.0 if home_wins else 0.0

    simulate_best_of_seven(
        "Team A",
        "Team B",
        force_seven_games,
        simulations=1,
        seed=1,
    )

    assert [context.home_team for context in contexts] == [
        "Team A",
        "Team A",
        "Team B",
        "Team B",
        "Team A",
        "Team B",
        "Team A",
    ]
    assert [(context.team_a_wins, context.team_b_wins) for context in contexts] == [
        (0, 0),
        (1, 0),
        (1, 1),
        (2, 1),
        (2, 2),
        (3, 2),
        (3, 3),
    ]


def test_simulation_probability_distributions_total_one() -> None:
    result = simulate_best_of_seven(
        "Team A",
        "Team B",
        lambda _: 0.57,
        simulations=10_000,
        seed=11,
    )

    assert math.isclose(
        result.team_a_series_win_probability
        + result.team_b_series_win_probability,
        1.0,
    )
    assert math.isclose(sum(result.outcome_probabilities.values()), 1.0)
    assert math.isclose(sum(result.length_probabilities.values()), 1.0)
    assert 4.0 <= result.expected_games <= 7.0


def test_simulation_rejects_invalid_provider_probability() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        simulate_best_of_seven(
            "Team A",
            "Team B",
            lambda _: 1.1,
            simulations=1,
            seed=1,
        )


def test_simulation_starts_from_observed_score_and_skips_completed_games() -> None:
    contexts: list[SeriesGameContext] = []

    def team_a_wins_remaining(context: SeriesGameContext) -> float:
        contexts.append(context)
        return 1.0 if context.home_team == "Team A" else 0.0

    result = simulate_best_of_seven(
        "Team A",
        "Team B",
        team_a_wins_remaining,
        simulations=2,
        seed=1,
        initial_team_a_wins=1,
        initial_team_b_wins=3,
    )

    assert [context.game_number for context in contexts[:3]] == [5, 6, 7]
    assert contexts[0].team_a_wins == 1
    assert contexts[0].team_b_wins == 3
    assert result.team_a_series_win_probability == 1.0
    assert result.outcome_probabilities["Team A in 7"] == 1.0
    assert result.length_probabilities == {4: 0.0, 5: 0.0, 6: 0.0, 7: 1.0}
    assert result.expected_games == 7.0


@pytest.mark.parametrize(
    ("team_a_wins", "team_b_wins"),
    [(-1, 0), (4, 0), (2, 4)],
)
def test_simulation_rejects_invalid_observed_score(
    team_a_wins: int,
    team_b_wins: int,
) -> None:
    with pytest.raises(ValueError, match="initial series score"):
        simulate_best_of_seven(
            "Team A",
            "Team B",
            lambda _: 0.5,
            simulations=1,
            initial_team_a_wins=team_a_wins,
            initial_team_b_wins=team_b_wins,
        )


def test_simulation_accepts_tied_score_before_game_seven() -> None:
    result = simulate_best_of_seven(
        "Team A",
        "Team B",
        lambda _: 1.0,
        simulations=1,
        initial_team_a_wins=3,
        initial_team_b_wins=3,
    )

    assert result.outcome_probabilities["Team A in 7"] == 1.0
