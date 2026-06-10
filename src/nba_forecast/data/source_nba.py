"""Cache-first access to NBA Stats team-game records."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

Fetcher = Callable[[str, str], pd.DataFrame]


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

