"""Sequential pre-game Elo ratings."""

from typing import Optional

import pandas as pd


def build_elo_features(
    games: pd.DataFrame,
    *,
    base_rating: float = 1500.0,
    k_factor: float = 20.0,
    home_advantage: float = 100.0,
    offseason_reversion: float = 0.75,
) -> pd.DataFrame:
    """Return pre-game Elo ratings and home-win probabilities."""
    ordered_games = games.sort_values(["game_date", "game_id"], ignore_index=True)
    ratings: dict[int, float] = {}
    current_season_key: Optional[str] = None
    rows: list[dict[str, object]] = []

    for game in ordered_games.itertuples(index=False):
        season_key = str(game.season_key)
        if current_season_key is not None and season_key != current_season_key:
            ratings = {
                team_id: base_rating + offseason_reversion * (rating - base_rating)
                for team_id, rating in ratings.items()
            }
        current_season_key = season_key

        home_team_id = int(game.home_team_id)
        away_team_id = int(game.away_team_id)
        home_elo = ratings.get(home_team_id, base_rating)
        away_elo = ratings.get(away_team_id, base_rating)
        probability = _home_win_probability(home_elo, away_elo, home_advantage)

        rows.append(
            {
                "game_id": str(game.game_id),
                "home_elo": home_elo,
                "away_elo": away_elo,
                "elo_diff": home_elo - away_elo,
                "elo_home_win_probability": probability,
            }
        )

        adjustment = k_factor * (float(game.home_win) - probability)
        ratings[home_team_id] = home_elo + adjustment
        ratings[away_team_id] = away_elo - adjustment

    return pd.DataFrame(rows)


def _home_win_probability(
    home_elo: float,
    away_elo: float,
    home_advantage: float,
) -> float:
    rating_difference = home_elo + home_advantage - away_elo
    return 1.0 / (1.0 + 10.0 ** (-rating_difference / 400.0))
