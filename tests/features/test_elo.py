import pandas as pd

from nba_forecast.features.elo import build_elo_features


def _elo_games() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": "game-1",
                "game_date": pd.Timestamp("2025-10-21"),
                "season_id": "22025",
                "home_team_id": 1,
                "away_team_id": 2,
                "home_win": 1,
            },
            {
                "game_id": "game-2",
                "game_date": pd.Timestamp("2025-10-22"),
                "season_id": "22025",
                "home_team_id": 1,
                "away_team_id": 2,
                "home_win": 0,
            },
        ]
    )


def test_elo_features_expose_ratings_before_current_game_update() -> None:
    elo = build_elo_features(_elo_games(), base_rating=1500.0)

    first_game = elo.iloc[0]
    second_game = elo.iloc[1]
    assert first_game["home_elo"] == 1500.0
    assert first_game["away_elo"] == 1500.0
    assert first_game["elo_home_win_probability"] > 0.5
    assert second_game["home_elo"] > 1500.0
    assert second_game["away_elo"] < 1500.0


def test_changing_result_does_not_change_same_game_elo() -> None:
    games = _elo_games()
    original = build_elo_features(games)

    changed_games = games.copy()
    changed_games.loc[0, "home_win"] = 0
    changed = build_elo_features(changed_games)

    assert original.loc[0, "home_elo"] == changed.loc[0, "home_elo"]
    assert original.loc[0, "away_elo"] == changed.loc[0, "away_elo"]
    assert original.loc[1, "home_elo"] != changed.loc[1, "home_elo"]

