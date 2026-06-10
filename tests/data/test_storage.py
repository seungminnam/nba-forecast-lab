from pathlib import Path

import duckdb
import pandas as pd

from nba_forecast.data.storage import write_processed_games
from nba_forecast.data.transform import team_rows_to_games

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "team_game_rows.csv"


def test_write_processed_games_creates_parquet_and_duckdb(tmp_path: Path) -> None:
    team_rows = pd.read_csv(
        FIXTURE_PATH,
        dtype={"GAME_ID": "string", "SEASON_ID": "string"},
    )
    games = team_rows_to_games(team_rows)

    parquet_path, database_path = write_processed_games(games, tmp_path)

    assert parquet_path == tmp_path / "processed" / "games.parquet"
    assert database_path == tmp_path / "nba_forecast.duckdb"
    assert parquet_path.exists()
    assert database_path.exists()

    persisted_parquet = pd.read_parquet(parquet_path)
    assert persisted_parquet["game_id"].tolist() == ["0022500001", "0022500002"]

    with duckdb.connect(str(database_path), read_only=True) as connection:
        persisted_ids = connection.execute(
            "SELECT game_id FROM games ORDER BY game_id"
        ).fetchall()

    assert persisted_ids == [("0022500001",), ("0022500002",)]

