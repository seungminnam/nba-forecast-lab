"""Immutable NBA Stats schedule snapshots."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from nba_forecast.data.contracts import expected_season_id

ScheduleFetcher = Callable[[str], pd.DataFrame]


class ScheduleSnapshotMetadataError(ValueError):
    """Raised when a schedule snapshot's metadata is missing or invalid."""


@dataclass(frozen=True)
class ScheduleSnapshot:
    """Paths for one immutable source-shaped schedule snapshot."""

    csv_path: Path
    metadata_path: Path


@dataclass(frozen=True)
class ScheduleSnapshotContext:
    """Validated metadata needed to transform one schedule snapshot."""

    season_key: str
    fetched_at_utc: datetime


def fetch_schedule_snapshot(
    season: str,
    cache_dir: Path,
    *,
    fetcher: Optional[ScheduleFetcher] = None,
    fetched_at: Optional[datetime] = None,
) -> ScheduleSnapshot:
    """Fetch and preserve one append-only ScheduleLeagueV2 snapshot."""
    _validate_season_key(season)
    timestamp = _utc_datetime(fetched_at or datetime.now(timezone.utc))
    snapshot_dir = cache_dir / "nba_stats" / "schedule_league_v2" / season
    filename = timestamp.strftime("%Y%m%dT%H%M%S.%fZ")
    csv_path = snapshot_dir / f"{filename}.csv"
    metadata_path = snapshot_dir / f"{filename}.metadata.json"
    if csv_path.exists() or metadata_path.exists():
        raise FileExistsError(f"Schedule snapshot already exists: {csv_path}")

    active_fetcher = fetcher or _fetch_schedule_league_v2
    rows = active_fetcher(season)

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    temporary_csv_path = csv_path.with_suffix(".csv.tmp")
    rows.to_csv(temporary_csv_path, index=False)
    temporary_csv_path.replace(csv_path)

    metadata = {
        "source": "NBA Stats API",
        "endpoint": "ScheduleLeagueV2",
        "season": season,
        "fetched_at_utc": timestamp.isoformat(),
        "rows": len(rows),
        "columns": rows.columns.tolist(),
    }
    temporary_metadata_path = csv_path.with_suffix(".metadata.json.tmp")
    temporary_metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    temporary_metadata_path.replace(metadata_path)
    return ScheduleSnapshot(csv_path=csv_path, metadata_path=metadata_path)


def load_schedule_snapshot(csv_path: Path) -> pd.DataFrame:
    """Load source-shaped schedule rows from one explicit snapshot."""
    return pd.read_csv(csv_path, dtype={"gameId": "string"})


def load_schedule_snapshot_context(csv_path: Path) -> ScheduleSnapshotContext:
    """Read and validate metadata for one explicit schedule snapshot."""
    metadata_path = csv_path.with_suffix(".metadata.json")
    if not metadata_path.exists():
        raise ScheduleSnapshotMetadataError(
            f"Missing schedule snapshot metadata: {metadata_path}"
        )
    try:
        metadata = json.loads(metadata_path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        raise ScheduleSnapshotMetadataError(
            f"Invalid schedule snapshot metadata: {metadata_path}"
        ) from error

    season = metadata.get("season")
    fetched_at = metadata.get("fetched_at_utc")
    if not isinstance(season, str):
        raise ScheduleSnapshotMetadataError(
            f"Invalid season in schedule snapshot metadata: {metadata_path}"
        )
    try:
        _validate_season_key(season)
        timestamp = _utc_datetime(fetched_at)
    except (TypeError, ValueError) as error:
        raise ScheduleSnapshotMetadataError(
            f"Invalid schedule snapshot metadata: {metadata_path}"
        ) from error
    return ScheduleSnapshotContext(
        season_key=season,
        fetched_at_utc=timestamp.to_pydatetime(),
    )


def _fetch_schedule_league_v2(season: str) -> pd.DataFrame:
    from nba_api.stats.endpoints import scheduleleaguev2

    response = scheduleleaguev2.ScheduleLeagueV2(season=season)
    return response.season_games.get_data_frame()


def _validate_season_key(season: str) -> None:
    expected_season_id("Regular Season", season)


def _utc_datetime(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("schedule snapshot timestamps must be timezone-aware")
    return timestamp.tz_convert("UTC")
