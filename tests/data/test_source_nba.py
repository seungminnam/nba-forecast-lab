import json
from pathlib import Path

import pandas as pd

from nba_forecast.data.source_nba import (
    load_or_fetch_team_games,
    raw_cache_path,
)


def _source_rows(points: int) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "GAME_ID": "0022500001",
                "GAME_DATE": "2025-10-21",
                "SEASON_ID": "22025",
                "TEAM_ID": 1,
                "TEAM_ABBREVIATION": "HOM",
                "MATCHUP": "HOM vs. AWY",
                "WL": "W",
                "PTS": points,
            }
        ]
    )


def test_load_or_fetch_team_games_writes_raw_cache_and_metadata(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, str]] = []

    def fetcher(season: str, season_type: str) -> pd.DataFrame:
        calls.append((season, season_type))
        return _source_rows(110)

    rows = load_or_fetch_team_games(
        "2025-26",
        "Regular Season",
        tmp_path,
        fetcher=fetcher,
    )

    cache_path = raw_cache_path(tmp_path, "2025-26", "Regular Season")
    metadata_path = cache_path.with_suffix(".metadata.json")
    assert calls == [("2025-26", "Regular Season")]
    assert rows.loc[0, "PTS"] == 110
    assert cache_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text())
    assert metadata["endpoint"] == "LeagueGameFinder"
    assert metadata["season"] == "2025-26"
    assert metadata["season_type"] == "Regular Season"
    assert metadata["rows"] == 1


def test_load_or_fetch_team_games_reuses_existing_cache(tmp_path: Path) -> None:
    calls = 0

    def fetcher(season: str, season_type: str) -> pd.DataFrame:
        nonlocal calls
        calls += 1
        return _source_rows(110)

    load_or_fetch_team_games("2025-26", "Playoffs", tmp_path, fetcher=fetcher)
    cached_rows = load_or_fetch_team_games(
        "2025-26",
        "Playoffs",
        tmp_path,
        fetcher=fetcher,
    )

    assert calls == 1
    assert cached_rows.loc[0, "PTS"] == 110


def test_load_or_fetch_team_games_force_replaces_existing_cache(
    tmp_path: Path,
) -> None:
    responses = iter([_source_rows(110), _source_rows(120)])

    def fetcher(season: str, season_type: str) -> pd.DataFrame:
        return next(responses)

    load_or_fetch_team_games("2025-26", "Regular Season", tmp_path, fetcher=fetcher)
    refreshed_rows = load_or_fetch_team_games(
        "2025-26",
        "Regular Season",
        tmp_path,
        force=True,
        fetcher=fetcher,
    )

    assert refreshed_rows.loc[0, "PTS"] == 120
    cache_path = raw_cache_path(tmp_path, "2025-26", "Regular Season")
    persisted_rows = pd.read_csv(cache_path)
    assert persisted_rows.loc[0, "PTS"] == 120


def test_raw_cache_path_is_stable(tmp_path: Path) -> None:
    assert raw_cache_path(
        tmp_path,
        "2025-26",
        "Regular Season",
    ) == (
        tmp_path
        / "nba_stats"
        / "league_game_finder"
        / "2025-26"
        / "regular-season.csv"
    )

