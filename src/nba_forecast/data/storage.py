"""Persistence for validated canonical game data."""

from pathlib import Path

import duckdb
import pandas as pd

from nba_forecast.data.validate import validate_games


def write_processed_games(
    games: pd.DataFrame,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Validate and persist canonical games to Parquet and DuckDB."""
    validate_games(games)

    processed_dir = output_dir / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = processed_dir / "games.parquet"
    temporary_parquet_path = processed_dir / "games.parquet.tmp"
    games.to_parquet(temporary_parquet_path, index=False)
    temporary_parquet_path.replace(parquet_path)

    database_path = output_dir / "nba_forecast.duckdb"
    with duckdb.connect(str(database_path)) as connection:
        connection.register("games_frame", games)
        connection.execute("CREATE OR REPLACE TABLE games AS SELECT * FROM games_frame")

    return parquet_path, database_path

