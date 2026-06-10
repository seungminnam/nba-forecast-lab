import pandas as pd

from nba_forecast.features.team_state import (
    PREGAME_TEAM_FEATURE_COLUMNS,
    build_team_state,
)


def _games() -> pd.DataFrame:
    rows = []
    for index, (date, home_win, home_points, away_points) in enumerate(
        [
            ("2025-10-21", 1, 110, 100),
            ("2025-10-22", 0, 98, 105),
            ("2025-10-25", 1, 112, 108),
        ],
        start=1,
    ):
        rows.append(
            {
                "game_id": f"game-{index}",
                "game_date": pd.Timestamp(date),
                "season_id": "22025",
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team_abbreviation": "HOM",
                "away_team_abbreviation": "AWY",
                "home_points": home_points,
                "away_points": away_points,
                "home_fga": 88,
                "away_fga": 90,
                "home_fgm": 42,
                "away_fgm": 39,
                "home_fta": 20,
                "away_fta": 18,
                "home_oreb": 10,
                "away_oreb": 9,
                "home_tov": 12,
                "away_tov": 14,
                "home_win": home_win,
            }
        )
    return pd.DataFrame(rows)


def test_build_team_state_creates_two_rows_per_game() -> None:
    team_state = build_team_state(_games())

    assert len(team_state) == 6
    assert team_state.groupby("game_id").size().eq(2).all()
    first_home = team_state.loc[
        (team_state["game_id"] == "game-1") & (team_state["team_id"] == 1)
    ].iloc[0]
    assert first_home["games_played"] == 0
    assert first_home["season_win_pct"] == 0.5


def test_current_result_does_not_change_current_pregame_features() -> None:
    games = _games()
    original = build_team_state(games)

    changed_games = games.copy()
    changed_games.loc[1, ["home_win", "home_points", "away_points"]] = [1, 120, 90]
    changed = build_team_state(changed_games)

    original_current = original.loc[original["game_id"] == "game-2"].reset_index(
        drop=True
    )
    changed_current = changed.loc[changed["game_id"] == "game-2"].reset_index(drop=True)
    pd.testing.assert_frame_equal(
        original_current[list(PREGAME_TEAM_FEATURE_COLUMNS)],
        changed_current[list(PREGAME_TEAM_FEATURE_COLUMNS)],
    )


def test_changed_result_affects_only_later_features() -> None:
    games = _games()
    original = build_team_state(games)

    changed_games = games.copy()
    changed_games.loc[1, ["home_win", "home_points", "away_points"]] = [1, 120, 90]
    changed = build_team_state(changed_games)

    original_later = original.loc[original["game_id"] == "game-3"].reset_index(
        drop=True
    )
    changed_later = changed.loc[changed["game_id"] == "game-3"].reset_index(drop=True)

    assert not original_later["season_win_pct"].equals(changed_later["season_win_pct"])
    assert not original_later["net_rating_5"].equals(changed_later["net_rating_5"])


def test_rest_days_and_back_to_back_use_previous_game_date() -> None:
    team_state = build_team_state(_games())
    home_team = team_state.loc[team_state["team_id"] == 1].set_index("game_id")

    assert pd.isna(home_team.loc["game-1", "rest_days"])
    assert home_team.loc["game-2", "rest_days"] == 1
    assert home_team.loc["game-2", "is_back_to_back"] == 1
    assert home_team.loc["game-3", "rest_days"] == 3
    assert home_team.loc["game-3", "is_back_to_back"] == 0
