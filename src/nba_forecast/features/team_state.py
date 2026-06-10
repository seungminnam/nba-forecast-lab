"""Build point-in-time team state from completed canonical games."""

import pandas as pd

ROLLING_WINDOWS = (5, 10, 20)
RATING_COLUMNS = ("team_win", "offensive_rating", "defensive_rating", "net_rating")
PREGAME_TEAM_FEATURE_COLUMNS = (
    "games_played",
    "season_win_pct",
    "rest_days",
    "is_back_to_back",
    "win_pct_5",
    "win_pct_10",
    "win_pct_20",
    "offensive_rating_5",
    "offensive_rating_10",
    "offensive_rating_20",
    "defensive_rating_5",
    "defensive_rating_10",
    "defensive_rating_20",
    "net_rating_5",
    "net_rating_10",
    "net_rating_20",
)


def build_team_state(games: pd.DataFrame) -> pd.DataFrame:
    """Return one team-perspective row per game with shifted pre-game features."""
    rows = pd.concat(
        [_team_rows(games, is_home=True), _team_rows(games, is_home=False)],
        ignore_index=True,
    )
    rows["game_date"] = pd.to_datetime(rows["game_date"], errors="raise")

    rows["team_possessions"] = _estimated_possessions(
        rows["team_fga"],
        rows["team_fta"],
        rows["team_oreb"],
        rows["team_tov"],
    )
    rows["opponent_possessions"] = _estimated_possessions(
        rows["opponent_fga"],
        rows["opponent_fta"],
        rows["opponent_oreb"],
        rows["opponent_tov"],
    )
    rows["offensive_rating"] = 100 * rows["team_points"] / rows["team_possessions"]
    rows["defensive_rating"] = (
        100 * rows["opponent_points"] / rows["opponent_possessions"]
    )
    rows["net_rating"] = rows["offensive_rating"] - rows["defensive_rating"]

    group_keys = ["season_id", "team_id"]
    rows = rows.sort_values(group_keys + ["game_date", "game_id"], ignore_index=True)
    grouped = rows.groupby(group_keys, sort=False)
    rows["games_played"] = grouped.cumcount()
    previous_game_date = grouped["game_date"].shift(1)
    rows["rest_days"] = (rows["game_date"] - previous_game_date).dt.days
    rows["is_back_to_back"] = rows["rest_days"].eq(1).astype(int)
    rows["season_win_pct"] = grouped["team_win"].transform(
        lambda values: values.shift(1).expanding().mean()
    )
    rows["season_win_pct"] = rows["season_win_pct"].fillna(0.5)

    for source_column in RATING_COLUMNS:
        output_prefix = "win_pct" if source_column == "team_win" else source_column
        for window in ROLLING_WINDOWS:
            rows[f"{output_prefix}_{window}"] = grouped[source_column].transform(
                lambda values, size=window: values.shift(1)
                .rolling(size, min_periods=1)
                .mean()
            )

    return rows.sort_values(
        ["game_date", "game_id", "is_home"],
        ascending=[True, True, False],
        ignore_index=True,
    )


def _team_rows(games: pd.DataFrame, *, is_home: bool) -> pd.DataFrame:
    team_side = "home" if is_home else "away"
    opponent_side = "away" if is_home else "home"
    team_win = games["home_win"] if is_home else 1 - games["home_win"]
    return pd.DataFrame(
        {
            "game_id": games["game_id"],
            "game_date": games["game_date"],
            "season_id": games["season_id"],
            "team_id": games[f"{team_side}_team_id"],
            "opponent_id": games[f"{opponent_side}_team_id"],
            "is_home": int(is_home),
            "team_win": team_win,
            "team_points": games[f"{team_side}_points"],
            "opponent_points": games[f"{opponent_side}_points"],
            "team_fga": games[f"{team_side}_fga"],
            "opponent_fga": games[f"{opponent_side}_fga"],
            "team_fta": games[f"{team_side}_fta"],
            "opponent_fta": games[f"{opponent_side}_fta"],
            "team_oreb": games[f"{team_side}_oreb"],
            "opponent_oreb": games[f"{opponent_side}_oreb"],
            "team_tov": games[f"{team_side}_tov"],
            "opponent_tov": games[f"{opponent_side}_tov"],
        }
    )


def _estimated_possessions(
    fga: pd.Series,
    fta: pd.Series,
    oreb: pd.Series,
    tov: pd.Series,
) -> pd.Series:
    return fga + 0.44 * fta - oreb + tov

