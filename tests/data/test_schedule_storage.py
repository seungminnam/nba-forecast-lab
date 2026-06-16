from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from nba_forecast.data.schedule_storage import write_scheduled_matchups
from nba_forecast.data.schedule_transform import schedule_rows_to_matchups

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "schedule_league_v2_rows.csv"


def _schedule() -> pd.DataFrame:
    rows = pd.read_csv(FIXTURE_PATH, dtype={"gameId": "string"})
    return schedule_rows_to_matchups(
        rows,
        season_key="2026-27",
        schedule_snapshot_at_utc=datetime(2026, 6, 15, 12, tzinfo=timezone.utc),
    )


def test_write_scheduled_matchups_round_trips_parquet_and_duckdb(
    tmp_path: Path,
) -> None:
    schedule = _schedule()

    parquet_path, database_path = write_scheduled_matchups(schedule, tmp_path)

    assert parquet_path == tmp_path / "schedules" / "scheduled_matchups.parquet"
    assert database_path == tmp_path / "schedules" / "schedule.duckdb"

    persisted_parquet = pd.read_parquet(parquet_path)
    pd.testing.assert_frame_equal(persisted_parquet, schedule)

    with duckdb.connect(str(database_path), read_only=True) as connection:
        persisted_duckdb = connection.execute(
            """
            SELECT game_id, season_id, season_type, nba_game_date, game_status
            FROM scheduled_matchups
            ORDER BY game_id
            """
        ).fetchdf()

    expected = schedule[
        ["game_id", "season_id", "season_type", "nba_game_date", "game_status"]
    ].sort_values("game_id", ignore_index=True)
    pd.testing.assert_frame_equal(persisted_duckdb, expected, check_dtype=False)


def test_write_scheduled_matchups_rejects_invalid_data_before_replacement(
    tmp_path: Path,
) -> None:
    schedule = _schedule()
    parquet_path, database_path = write_scheduled_matchups(schedule, tmp_path)
    original_parquet_bytes = parquet_path.read_bytes()

    invalid = schedule.drop(columns=["game_id"])

    try:
        write_scheduled_matchups(invalid, tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid scheduled matchups should be rejected")

    assert parquet_path.read_bytes() == original_parquet_bytes
    with duckdb.connect(str(database_path), read_only=True) as connection:
        persisted_count = connection.execute(
            "SELECT count(*) FROM scheduled_matchups"
        ).fetchone()[0]

    assert persisted_count == len(schedule)
