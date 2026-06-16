"""Persistence for validated scheduled matchup data."""

from pathlib import Path

import duckdb
import pandas as pd

from nba_forecast.data.schedule_transform import validate_scheduled_matchups


def write_scheduled_matchups(
    schedule: pd.DataFrame,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Validate and persist scheduled matchups to Parquet and DuckDB."""
    validate_scheduled_matchups(schedule)

    schedule_dir = output_dir / "schedules"
    schedule_dir.mkdir(parents=True, exist_ok=True)

    parquet_path = schedule_dir / "scheduled_matchups.parquet"
    temporary_parquet_path = schedule_dir / "scheduled_matchups.parquet.tmp"
    schedule.to_parquet(temporary_parquet_path, index=False)
    temporary_parquet_path.replace(parquet_path)

    database_path = schedule_dir / "schedule.duckdb"
    with duckdb.connect(str(database_path)) as connection:
        connection.register("scheduled_matchups_frame", schedule)
        connection.execute(
            "CREATE OR REPLACE TABLE scheduled_matchups AS "
            "SELECT * FROM scheduled_matchups_frame"
        )

    return parquet_path, database_path
