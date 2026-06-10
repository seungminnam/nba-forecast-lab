from pathlib import Path

import pandas as pd
import pytest

from nba_forecast.data.contracts import CanonicalGameError
from nba_forecast.data.transform import team_rows_to_games

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "team_game_rows.csv"


@pytest.fixture
def team_rows() -> pd.DataFrame:
    return pd.read_csv(
        FIXTURE_PATH,
        dtype={"GAME_ID": "string", "SEASON_ID": "string"},
    )


def test_team_rows_to_games_pairs_home_and_away_rows(
    team_rows: pd.DataFrame,
) -> None:
    games = team_rows_to_games(team_rows)

    assert games["game_id"].is_unique
    assert games["game_id"].tolist() == ["0022500001", "0022500002"]

    first_game = games.iloc[0]
    assert first_game["home_team_id"] == 1
    assert first_game["away_team_id"] == 2
    assert first_game["home_win"] == 1
    assert first_game["home_points"] == 110
    assert first_game["away_points"] == 101
    assert first_game["home_fga"] == 88
    assert first_game["away_fga"] == 91
    assert first_game["home_oreb"] == 10
    assert first_game["away_tov"] == 15

    second_game = games.iloc[1]
    assert second_game["home_team_id"] == 3
    assert second_game["away_team_id"] == 4
    assert second_game["home_win"] == 0


def test_team_rows_to_games_rejects_game_missing_away_row(
    team_rows: pd.DataFrame,
) -> None:
    incomplete_rows = team_rows.loc[team_rows["TEAM_ID"] != 2]

    with pytest.raises(CanonicalGameError, match="exactly two team rows"):
        team_rows_to_games(incomplete_rows)


def test_team_rows_to_games_parses_home_team_from_repeated_away_matchup(
    team_rows: pd.DataFrame,
) -> None:
    repeated_matchup_rows = team_rows.copy()
    first_game = repeated_matchup_rows["GAME_ID"] == "0022500001"
    repeated_matchup_rows.loc[first_game, "MATCHUP"] = "AWY @ HOM"

    games = team_rows_to_games(repeated_matchup_rows)

    assert games.loc[0, "home_team_abbreviation"] == "HOM"
    assert games.loc[0, "away_team_abbreviation"] == "AWY"
