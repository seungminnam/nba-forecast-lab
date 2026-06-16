import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from nba_forecast.data.source_schedule import (
    ScheduleSnapshotMetadataError,
    fetch_schedule_snapshot,
    load_schedule_snapshot,
    load_schedule_snapshot_context,
)


def test_fetch_schedule_snapshot_writes_append_only_csv_and_metadata(
    tmp_path: Path,
) -> None:
    fetched_at = datetime(2026, 6, 15, 12, 0, 0, 123456, tzinfo=timezone.utc)

    snapshot = fetch_schedule_snapshot(
        "2026-27",
        tmp_path,
        fetcher=lambda season: _source_rows(),
        fetched_at=fetched_at,
    )

    assert snapshot.csv_path == (
        tmp_path
        / "nba_stats"
        / "schedule_league_v2"
        / "2026-27"
        / "20260615T120000.123456Z.csv"
    )
    assert snapshot.metadata_path == snapshot.csv_path.with_suffix(
        ".metadata.json"
    )
    pd.testing.assert_frame_equal(
        load_schedule_snapshot(snapshot.csv_path),
        _source_rows(),
    )

    metadata = json.loads(snapshot.metadata_path.read_text())
    assert metadata == {
        "source": "NBA Stats API",
        "endpoint": "ScheduleLeagueV2",
        "season": "2026-27",
        "fetched_at_utc": "2026-06-15T12:00:00.123456+00:00",
        "rows": 1,
        "columns": _source_rows().columns.tolist(),
    }


def test_fetch_schedule_snapshot_rejects_naive_timestamp(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        fetch_schedule_snapshot(
            "2026-27",
            tmp_path,
            fetcher=lambda season: _source_rows(),
            fetched_at=datetime(2026, 6, 15, 12),
        )


def test_fetch_schedule_snapshot_refuses_to_overwrite_existing_snapshot(
    tmp_path: Path,
) -> None:
    fetched_at = datetime(2026, 6, 15, 12, tzinfo=timezone.utc)
    fetch_schedule_snapshot(
        "2026-27",
        tmp_path,
        fetcher=lambda season: _source_rows(),
        fetched_at=fetched_at,
    )

    with pytest.raises(FileExistsError, match="already exists"):
        fetch_schedule_snapshot(
            "2026-27",
            tmp_path,
            fetcher=lambda season: _source_rows(),
            fetched_at=fetched_at,
        )


def test_fetch_schedule_snapshot_failure_leaves_directory_unchanged(
    tmp_path: Path,
) -> None:
    def failing_fetcher(season: str) -> pd.DataFrame:
        raise RuntimeError("source unavailable")

    with pytest.raises(RuntimeError, match="source unavailable"):
        fetch_schedule_snapshot(
            "2026-27",
            tmp_path,
            fetcher=failing_fetcher,
            fetched_at=datetime(2026, 6, 15, 12, tzinfo=timezone.utc),
        )

    assert not (tmp_path / "nba_stats").exists()


def test_load_schedule_snapshot_context_reads_valid_metadata(tmp_path: Path) -> None:
    snapshot = fetch_schedule_snapshot(
        "2026-27",
        tmp_path,
        fetcher=lambda season: _source_rows(),
        fetched_at=datetime(2026, 6, 15, 12, tzinfo=timezone.utc),
    )

    context = load_schedule_snapshot_context(snapshot.csv_path)

    assert context.season_key == "2026-27"
    assert context.fetched_at_utc == datetime(
        2026,
        6,
        15,
        12,
        tzinfo=timezone.utc,
    )


def test_load_schedule_snapshot_context_rejects_missing_or_invalid_metadata(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "schedule.csv"
    csv_path.write_text("gameId\n")

    with pytest.raises(ScheduleSnapshotMetadataError, match="Missing"):
        load_schedule_snapshot_context(csv_path)

    csv_path.with_suffix(".metadata.json").write_text("{invalid")
    with pytest.raises(ScheduleSnapshotMetadataError, match="Invalid"):
        load_schedule_snapshot_context(csv_path)

    csv_path.with_suffix(".metadata.json").write_text(
        json.dumps(
            {
                "season": "invalid",
                "fetched_at_utc": "2026-06-15T12:00:00+00:00",
            }
        )
    )
    with pytest.raises(ScheduleSnapshotMetadataError, match="Invalid"):
        load_schedule_snapshot_context(csv_path)


def _source_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "gameId": "0022600001",
                "gameStatus": 1,
                "gameStatusText": "7:30 pm ET",
                "gameDateTimeUTC": "2026-10-22T23:30:00Z",
                "gameDateEst": "2026-10-22T00:00:00",
                "ifNecessary": False,
                "postponedStatus": 0,
                "homeTeam_teamId": 1,
                "homeTeam_teamTricode": "HOM",
                "awayTeam_teamId": 2,
                "awayTeam_teamTricode": "AWY",
            }
        ]
    ).astype({"gameId": "string"})
