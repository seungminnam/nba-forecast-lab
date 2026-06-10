"""Transform source-shaped team-game rows into canonical games."""

from typing import Union

import pandas as pd

from nba_forecast.data.contracts import (
    CANONICAL_GAME_COLUMNS,
    SOURCE_TEAM_GAME_COLUMNS,
    CanonicalGameError,
)

CanonicalValue = Union[str, int, pd.Timestamp]


def team_rows_to_games(team_rows: pd.DataFrame) -> pd.DataFrame:
    """Pair NBA Stats team-game rows into one chronologically sorted game row."""
    rows = team_rows.rename(columns=lambda column: str(column).upper()).copy()
    _require_source_columns(rows)

    rows["GAME_ID"] = rows["GAME_ID"].astype("string")
    rows["SEASON_ID"] = rows["SEASON_ID"].astype("string")
    rows["GAME_DATE"] = pd.to_datetime(rows["GAME_DATE"], errors="raise")
    rows["PARSED_HOME_ABBREVIATION"] = rows["MATCHUP"].map(_home_abbreviation)
    rows["IS_HOME"] = (
        rows["TEAM_ABBREVIATION"] == rows["PARSED_HOME_ABBREVIATION"]
    )

    invalid_counts = rows.groupby("GAME_ID", sort=False).size()
    invalid_counts = invalid_counts.loc[invalid_counts != 2]
    if not invalid_counts.empty:
        game_ids = ", ".join(invalid_counts.index.astype(str))
        raise CanonicalGameError(
            "Each game must contain exactly two team rows; "
            f"invalid game_ids: {game_ids}"
        )

    canonical_rows: list[dict[str, CanonicalValue]] = []
    for game_id, game_rows in rows.groupby("GAME_ID", sort=False):
        home_rows = game_rows.loc[game_rows["IS_HOME"]]
        away_rows = game_rows.loc[~game_rows["IS_HOME"]]
        if len(home_rows) != 1 or len(away_rows) != 1:
            raise CanonicalGameError(
                f"Game {game_id} must contain one home row and one away row"
            )

        home = home_rows.iloc[0]
        away = away_rows.iloc[0]
        if int(home["TEAM_ID"]) == int(away["TEAM_ID"]):
            raise CanonicalGameError(f"Game {game_id} contains the same team twice")
        inconsistent_date = home["GAME_DATE"] != away["GAME_DATE"]
        inconsistent_season = home["SEASON_ID"] != away["SEASON_ID"]
        if inconsistent_date or inconsistent_season:
            raise CanonicalGameError(
                f"Game {game_id} contains inconsistent date or season values"
            )

        canonical_rows.append(
            {
                "game_id": str(game_id),
                "game_date": home["GAME_DATE"],
                "season_id": str(home["SEASON_ID"]),
                "home_team_id": int(home["TEAM_ID"]),
                "away_team_id": int(away["TEAM_ID"]),
                "home_team_abbreviation": str(home["TEAM_ABBREVIATION"]),
                "away_team_abbreviation": str(away["TEAM_ABBREVIATION"]),
                "home_points": int(home["PTS"]),
                "away_points": int(away["PTS"]),
                "home_win": int(home["WL"] == "W"),
            }
        )

    games = pd.DataFrame(canonical_rows, columns=CANONICAL_GAME_COLUMNS)
    return games.sort_values(["game_date", "game_id"], ignore_index=True)


def _require_source_columns(rows: pd.DataFrame) -> None:
    missing = sorted(set(SOURCE_TEAM_GAME_COLUMNS) - set(rows.columns))
    if missing:
        missing_columns = ", ".join(missing)
        raise CanonicalGameError(f"Missing required source columns: {missing_columns}")


def _home_abbreviation(matchup: object) -> str:
    matchup_text = str(matchup)
    if " vs. " in matchup_text:
        return matchup_text.split(" vs. ", maxsplit=1)[0]
    if " @ " in matchup_text:
        return matchup_text.split(" @ ", maxsplit=1)[1]
    raise CanonicalGameError(f"Unsupported MATCHUP format: {matchup_text}")
