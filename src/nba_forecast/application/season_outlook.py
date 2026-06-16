"""Load game history and run off-season win projection."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from nba_forecast.simulation.season import SeasonOutlookResult, simulate_season

_BASE_RATING = 1500.0
_K_FACTOR = 20.0
_OFFSEASON_REVERSION = 0.75


def run_season_outlook(
    games_path: Path,
    *,
    simulations: int = 10_000,
    home_advantage: float = 100.0,
    seed: Optional[int] = None,
) -> SeasonOutlookResult:
    """Load games parquet, compute final team Elo ratings, run season simulation."""
    games = pd.read_parquet(games_path)
    team_elos = compute_final_elos(games, home_advantage=home_advantage)
    return simulate_season(
        team_elos,
        simulations=simulations,
        home_advantage=home_advantage,
        seed=seed,
    )


def compute_final_elos(
    games: pd.DataFrame,
    *,
    home_advantage: float = 100.0,
) -> dict[str, float]:
    """Replay game history and return each team's final Elo rating by abbreviation."""
    ordered = games.sort_values(["game_date", "game_id"], ignore_index=True)
    ratings: dict[int, float] = {}
    id_to_abbr: dict[int, str] = {}
    current_season: Optional[str] = None

    for row in ordered.itertuples(index=False):
        season_key = str(row.season_key)

        if current_season is not None and season_key != current_season:
            ratings = {
                tid: _BASE_RATING + _OFFSEASON_REVERSION * (r - _BASE_RATING)
                for tid, r in ratings.items()
            }
        current_season = season_key

        home_id = int(row.home_team_id)
        away_id = int(row.away_team_id)
        id_to_abbr[home_id] = str(row.home_team_abbreviation)
        id_to_abbr[away_id] = str(row.away_team_abbreviation)

        home_elo = ratings.get(home_id, _BASE_RATING)
        away_elo = ratings.get(away_id, _BASE_RATING)
        p = 1.0 / (1.0 + 10.0 ** (-((home_elo + home_advantage) - away_elo) / 400.0))

        adj = _K_FACTOR * (float(row.home_win) - p)
        ratings[home_id] = home_elo + adj
        ratings[away_id] = away_elo - adj

    return {id_to_abbr[tid]: r for tid, r in ratings.items() if tid in id_to_abbr}
