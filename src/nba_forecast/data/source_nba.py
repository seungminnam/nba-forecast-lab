"""Cache-first access to NBA Stats team-game records."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from nba_forecast.data.contracts import expected_season_id

Fetcher = Callable[[str, str], pd.DataFrame]


class RawCacheMetadataError(ValueError):
    """Raised when a raw-cache metadata sidecar is missing or invalid."""


@dataclass(frozen=True)
class RawCacheContext:
    """Validated request context used to transform one raw cache."""

    season_key: str
    season_type: str


def raw_cache_path(cache_dir: Path, season: str, season_type: str) -> Path:
    """Return the stable raw-cache path for an NBA Stats request."""
    season_type_slug = season_type.strip().lower().replace(" ", "-")
    return (
        cache_dir
        / "nba_stats"
        / "league_game_finder"
        / season
        / f"{season_type_slug}.csv"
    )


def load_raw_cache_context(cache_path: Path) -> RawCacheContext:
    """Return validated season context from a raw cache's metadata sidecar."""
    metadata_path = cache_path.with_suffix(".metadata.json")
    if not metadata_path.exists():
        raise RawCacheMetadataError(f"Missing raw-cache metadata: {metadata_path}")
    try:
        metadata = json.loads(metadata_path.read_text())
    except (json.JSONDecodeError, OSError) as error:
        raise RawCacheMetadataError(
            f"Invalid raw-cache metadata: {metadata_path}"
        ) from error

    season = metadata.get("season")
    season_type = metadata.get("season_type")
    if not isinstance(season, str) or not season.strip():
        raise RawCacheMetadataError(
            f"Invalid season in raw-cache metadata: {metadata_path}"
        )
    try:
        expected_season_id(str(season_type), season)
    except ValueError as error:
        raise RawCacheMetadataError(
            f"Invalid season context in raw-cache metadata: {metadata_path}"
        ) from error
    return RawCacheContext(season_key=season, season_type=str(season_type))


def load_or_fetch_team_games(
    season: str,
    season_type: str,
    cache_dir: Path,
    *,
    force: bool = False,
    fetcher: Optional[Fetcher] = None,
) -> pd.DataFrame:
    """Return cached team-game rows, fetching and recording them when needed."""
    cache_path = raw_cache_path(cache_dir, season, season_type)
    if cache_path.exists() and not force:
        return _read_raw_csv(cache_path)

    active_fetcher = fetcher or _fetch_league_game_finder
    rows = active_fetcher(season, season_type)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_cache_path = cache_path.with_suffix(".csv.tmp")
    rows.to_csv(temporary_cache_path, index=False)
    temporary_cache_path.replace(cache_path)

    metadata = {
        "source": "NBA Stats API",
        "endpoint": "LeagueGameFinder",
        "season": season,
        "season_type": season_type,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "rows": len(rows),
    }
    metadata_path = cache_path.with_suffix(".metadata.json")
    temporary_metadata_path = cache_path.with_suffix(".metadata.json.tmp")
    temporary_metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    temporary_metadata_path.replace(metadata_path)

    return _read_raw_csv(cache_path)


def load_or_fetch_history(
    seasons: Sequence[str],
    season_types: Sequence[str],
    cache_dir: Path,
    *,
    force: bool = False,
    fetcher: Optional[Fetcher] = None,
) -> list[Path]:
    """Populate and return stable raw-cache paths for historical requests."""
    paths: list[Path] = []
    for season in seasons:
        for season_type in season_types:
            load_or_fetch_team_games(
                season,
                season_type,
                cache_dir,
                force=force,
                fetcher=fetcher,
            )
            paths.append(raw_cache_path(cache_dir, season, season_type))
    return paths


def _read_raw_csv(cache_path: Path) -> pd.DataFrame:
    return pd.read_csv(
        cache_path,
        dtype={"GAME_ID": "string", "SEASON_ID": "string"},
    )


def _fetch_league_game_finder(season: str, season_type: str) -> pd.DataFrame:
    from nba_api.stats.endpoints import leaguegamefinder

    response = leaguegamefinder.LeagueGameFinder(
        season_nullable=season,
        season_type_nullable=season_type,
    )
    return response.get_data_frames()[0]
