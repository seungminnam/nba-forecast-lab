import pandas as pd
import pytest

from nba_forecast.features.game_features import (
    MODEL_FEATURE_COLUMNS,
    build_game_features,
)
from nba_forecast.features.matchup_features import (
    ScheduledMatchup,
    build_scheduled_matchup_features,
)


def _games() -> pd.DataFrame:
    rows = []
    for index, (date, home_win, home_points, away_points) in enumerate(
        [
            ("2025-10-21", 1, 110, 100),
            ("2025-10-22", 0, 98, 105),
            ("2025-10-25", 1, 112, 108),
            ("2025-10-28", 0, 101, 109),
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


def _scheduled_third_game() -> ScheduledMatchup:
    return ScheduledMatchup(
        game_id="game-3",
        game_date=pd.Timestamp("2025-10-25"),
        season_id="22025",
        home_team_id=1,
        away_team_id=2,
        home_team_abbreviation="HOM",
        away_team_abbreviation="AWY",
    )


def test_scheduled_snapshot_matches_historical_pregame_features() -> None:
    games = _games()
    expected = build_game_features(games).set_index("game_id").loc["game-3"]

    actual = build_scheduled_matchup_features(
        games,
        _scheduled_third_game(),
        as_of_date=pd.Timestamp("2025-10-25"),
    ).iloc[0]

    pd.testing.assert_series_equal(
        actual[list(MODEL_FEATURE_COLUMNS)],
        expected[list(MODEL_FEATURE_COLUMNS)],
        check_names=False,
    )


def test_snapshot_ignores_results_on_or_after_as_of_date() -> None:
    games = _games()
    original = build_scheduled_matchup_features(
        games,
        _scheduled_third_game(),
        as_of_date=pd.Timestamp("2025-10-25"),
    )
    changed = games.copy()
    changed.loc[
        changed["game_date"] >= pd.Timestamp("2025-10-25"),
        ["home_win", "home_points", "away_points"],
    ] = [0, 80, 130]

    rebuilt = build_scheduled_matchup_features(
        changed,
        _scheduled_third_game(),
        as_of_date=pd.Timestamp("2025-10-25"),
    )

    pd.testing.assert_frame_equal(original, rebuilt)


def test_snapshot_rejects_as_of_date_after_scheduled_game() -> None:
    with pytest.raises(ValueError, match="on or before"):
        build_scheduled_matchup_features(
            _games(),
            _scheduled_third_game(),
            as_of_date=pd.Timestamp("2025-10-26"),
        )
