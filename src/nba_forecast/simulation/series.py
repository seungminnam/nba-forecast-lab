"""Best-of-seven Monte Carlo series simulation."""

import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

HOME_COURT_SCHEDULE = ("A", "A", "B", "B", "A", "B", "A")
DEFAULT_SIMULATIONS = 10_000


@dataclass(frozen=True)
class SeriesGameContext:
    """Information available immediately before one simulated series game."""

    game_number: int
    home_team: str
    away_team: str
    team_a: str
    team_b: str
    team_a_wins: int
    team_b_wins: int


@dataclass(frozen=True)
class SeriesSimulationResult:
    """Normalized outcome distribution from repeated sampled series."""

    team_a: str
    team_b: str
    simulations: int
    seed: Optional[int]
    team_a_series_win_probability: float
    team_b_series_win_probability: float
    outcome_probabilities: dict[str, float]
    length_probabilities: dict[int, float]
    expected_games: float


HomeWinProbability = Callable[[SeriesGameContext], float]


def simulate_best_of_seven(
    team_a: str,
    team_b: str,
    home_win_probability: HomeWinProbability,
    *,
    simulations: int = DEFAULT_SIMULATIONS,
    seed: Optional[int] = None,
    initial_team_a_wins: int = 0,
    initial_team_b_wins: int = 0,
) -> SeriesSimulationResult:
    """Simulate a best-of-seven series where team A owns home-court advantage."""
    if not team_a or not team_b or team_a == team_b:
        raise ValueError("Series teams must be distinct non-empty names")
    if simulations <= 0:
        raise ValueError("simulations must be greater than zero")
    _validate_initial_score(initial_team_a_wins, initial_team_b_wins)

    rng = random.Random(seed)
    outcome_counts = {
        f"{team} in {games}": 0
        for team in (team_a, team_b)
        for games in range(4, 8)
    }
    length_counts = {games: 0 for games in range(4, 8)}
    team_a_series_wins = 0
    completed_games = initial_team_a_wins + initial_team_b_wins

    for _ in range(simulations):
        team_a_wins = initial_team_a_wins
        team_b_wins = initial_team_b_wins

        for game_index in range(completed_games, len(HOME_COURT_SCHEDULE)):
            home_court = HOME_COURT_SCHEDULE[game_index]
            home_team, away_team = (
                (team_a, team_b) if home_court == "A" else (team_b, team_a)
            )
            context = SeriesGameContext(
                game_number=game_index + 1,
                home_team=home_team,
                away_team=away_team,
                team_a=team_a,
                team_b=team_b,
                team_a_wins=team_a_wins,
                team_b_wins=team_b_wins,
            )
            probability = float(home_win_probability(context))
            if not 0.0 <= probability <= 1.0:
                raise ValueError("Home win probability must be between 0 and 1")

            home_wins = rng.random() < probability
            team_a_wins_game = home_wins == (home_team == team_a)
            if team_a_wins_game:
                team_a_wins += 1
            else:
                team_b_wins += 1

            if team_a_wins == 4 or team_b_wins == 4:
                series_length = game_index + 1
                winner = team_a if team_a_wins == 4 else team_b
                if winner == team_a:
                    team_a_series_wins += 1
                outcome_counts[f"{winner} in {series_length}"] += 1
                length_counts[series_length] += 1
                break

    outcome_probabilities = _normalize(outcome_counts, simulations)
    length_probabilities = _normalize(length_counts, simulations)
    team_a_probability = team_a_series_wins / simulations
    return SeriesSimulationResult(
        team_a=team_a,
        team_b=team_b,
        simulations=simulations,
        seed=seed,
        team_a_series_win_probability=team_a_probability,
        team_b_series_win_probability=1.0 - team_a_probability,
        outcome_probabilities=outcome_probabilities,
        length_probabilities=length_probabilities,
        expected_games=sum(
            games * probability for games, probability in length_probabilities.items()
        ),
    )


def _validate_initial_score(team_a_wins: int, team_b_wins: int) -> None:
    if (
        team_a_wins < 0
        or team_b_wins < 0
        or team_a_wins >= 4
        or team_b_wins >= 4
        or team_a_wins + team_b_wins > 6
    ):
        raise ValueError("initial series score must represent an active series")


def _normalize(counts: dict, simulations: int) -> dict:
    return {key: count / simulations for key, count in counts.items()}
