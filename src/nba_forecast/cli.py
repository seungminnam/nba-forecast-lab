"""Command-line workflows for NBA Forecast Lab."""

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

import pandas as pd

from nba_forecast.config import RAW_DATA_DIR
from nba_forecast.data.source_nba import load_or_fetch_team_games
from nba_forecast.data.storage import write_processed_games
from nba_forecast.data.transform import team_rows_to_games


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run an NBA Forecast Lab command."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "build-games":
        return _build_games(args.raw_csv, args.output_dir)
    if args.command == "fetch-games":
        return _fetch_games(
            args.season,
            args.season_type,
            args.cache_dir,
            args.force,
        )

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nba-forecast")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build-games",
        help="Build validated canonical games from a raw team-game CSV.",
    )
    build_parser.add_argument("--raw-csv", type=Path, required=True)
    build_parser.add_argument("--output-dir", type=Path, required=True)

    fetch_parser = subparsers.add_parser(
        "fetch-games",
        help="Populate the raw NBA Stats cache for one season and season type.",
    )
    fetch_parser.add_argument("--season", required=True)
    fetch_parser.add_argument("--season-type", default="Regular Season")
    fetch_parser.add_argument("--cache-dir", type=Path, default=RAW_DATA_DIR)
    fetch_parser.add_argument("--force", action="store_true")

    return parser


def _build_games(raw_csv: Path, output_dir: Path) -> int:
    team_rows = pd.read_csv(
        raw_csv,
        dtype={"GAME_ID": "string", "SEASON_ID": "string"},
    )
    games = team_rows_to_games(team_rows)
    parquet_path, database_path = write_processed_games(games, output_dir)
    print(
        f"Wrote {len(games)} canonical games to {parquet_path} "
        f"and {database_path}"
    )
    return 0


def _fetch_games(
    season: str,
    season_type: str,
    cache_dir: Path,
    force: bool,
) -> int:
    rows = load_or_fetch_team_games(
        season,
        season_type,
        cache_dir,
        force=force,
    )
    print(f"Cached {len(rows)} team-game rows for {season} {season_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

