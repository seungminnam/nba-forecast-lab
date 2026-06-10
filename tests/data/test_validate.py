from pathlib import Path

import pandas as pd
import pytest

from nba_forecast.data.contracts import CanonicalGameError
from nba_forecast.data.transform import team_rows_to_games
from nba_forecast.data.validate import validate_games

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "team_game_rows.csv"


@pytest.fixture
def games() -> pd.DataFrame:
    team_rows = pd.read_csv(
        FIXTURE_PATH,
        dtype={"GAME_ID": "string", "SEASON_ID": "string"},
    )
    return team_rows_to_games(team_rows)


def test_validate_games_accepts_valid_completed_games(games: pd.DataFrame) -> None:
    assert validate_games(games) is None


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda games: pd.concat([games, games.iloc[[0]]]), "duplicate game_id"),
        (
            lambda games: games.assign(away_team_id=games["home_team_id"]),
            "home and away teams must differ",
        ),
        (lambda games: games.assign(home_points=pd.NA), "scores must be present"),
        (lambda games: games.assign(home_win=2), "home_win must be 0 or 1"),
    ],
)
def test_validate_games_rejects_invalid_completed_games(
    games: pd.DataFrame,
    mutate: object,
    message: str,
) -> None:
    invalid_games = mutate(games)  # type: ignore[operator]

    with pytest.raises(CanonicalGameError, match=message):
        validate_games(invalid_games)


def test_validate_games_reports_multiple_failed_rules(games: pd.DataFrame) -> None:
    invalid_games = games.assign(
        away_team_id=games["home_team_id"],
        home_win=2,
    )

    with pytest.raises(CanonicalGameError) as error:
        validate_games(invalid_games)

    assert "home and away teams must differ" in str(error.value)
    assert "home_win must be 0 or 1" in str(error.value)

