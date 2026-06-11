"""Command-line workflows for NBA Forecast Lab."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

import pandas as pd

from nba_forecast.application.simulator_lab import SimulatorLabInput, run_simulator_lab
from nba_forecast.config import HISTORICAL_SEASONS, RAW_DATA_DIR
from nba_forecast.data.source_nba import load_or_fetch_history, load_or_fetch_team_games
from nba_forecast.data.storage import write_processed_games
from nba_forecast.data.transform import team_rows_to_games
from nba_forecast.evaluation.baselines import evaluate_baselines
from nba_forecast.evaluation.splits import make_temporal_split
from nba_forecast.features.game_features import build_game_features


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
    if args.command == "fetch-history":
        return _fetch_history(
            args.seasons,
            args.season_types,
            args.cache_dir,
            args.force,
        )
    if args.command == "build-features":
        return _build_features(args.games_parquet, args.output_dir)
    if args.command == "evaluate-baselines":
        return _evaluate_baselines(
            args.features_parquet,
            args.train_seasons,
            args.test_season,
            args.output_dir,
        )
    if args.command == "simulate-series":
        return _simulate_series(
            args.team_a,
            args.team_b,
            args.team_a_home_probability,
            args.team_a_away_probability,
            args.simulations,
            args.seed,
            args.output_dir,
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
    build_parser.add_argument("--raw-csv", type=Path, nargs="+", required=True)
    build_parser.add_argument("--output-dir", type=Path, required=True)

    fetch_parser = subparsers.add_parser(
        "fetch-games",
        help="Populate the raw NBA Stats cache for one season and season type.",
    )
    fetch_parser.add_argument("--season", required=True)
    fetch_parser.add_argument("--season-type", default="Regular Season")
    fetch_parser.add_argument("--cache-dir", type=Path, default=RAW_DATA_DIR)
    fetch_parser.add_argument("--force", action="store_true")

    history_parser = subparsers.add_parser(
        "fetch-history",
        help="Populate raw caches for multiple seasons and season types.",
    )
    history_parser.add_argument(
        "--seasons",
        nargs="+",
        default=list(HISTORICAL_SEASONS),
    )
    history_parser.add_argument(
        "--season-types",
        nargs="+",
        default=["Regular Season"],
    )
    history_parser.add_argument("--cache-dir", type=Path, default=RAW_DATA_DIR)
    history_parser.add_argument("--force", action="store_true")

    feature_parser = subparsers.add_parser(
        "build-features",
        help="Build leakage-safe pre-game features from canonical games.",
    )
    feature_parser.add_argument("--games-parquet", type=Path, required=True)
    feature_parser.add_argument("--output-dir", type=Path, required=True)

    evaluation_parser = subparsers.add_parser(
        "evaluate-baselines",
        help="Evaluate probability baselines on an out-of-time season.",
    )
    evaluation_parser.add_argument("--features-parquet", type=Path, required=True)
    evaluation_parser.add_argument("--train-seasons", nargs="+", required=True)
    evaluation_parser.add_argument("--test-season", required=True)
    evaluation_parser.add_argument("--output-dir", type=Path, required=True)

    simulation_parser = subparsers.add_parser(
        "simulate-series",
        help="Run an assumption-based best-of-seven series simulation.",
    )
    simulation_parser.add_argument("--team-a", required=True)
    simulation_parser.add_argument("--team-b", required=True)
    simulation_parser.add_argument(
        "--team-a-home-probability",
        type=float,
        required=True,
    )
    simulation_parser.add_argument(
        "--team-a-away-probability",
        type=float,
        required=True,
    )
    simulation_parser.add_argument("--simulations", type=int, default=10_000)
    simulation_parser.add_argument("--seed", type=int, default=2026)
    simulation_parser.add_argument("--output-dir", type=Path, required=True)

    return parser


def _build_games(raw_csv: list[Path], output_dir: Path) -> int:
    team_rows = pd.concat(
        [
            pd.read_csv(
                path,
                dtype={"GAME_ID": "string", "SEASON_ID": "string"},
            )
            for path in raw_csv
        ],
        ignore_index=True,
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


def _fetch_history(
    seasons: list[str],
    season_types: list[str],
    cache_dir: Path,
    force: bool,
) -> int:
    paths = load_or_fetch_history(
        seasons,
        season_types,
        cache_dir,
        force=force,
    )
    row_count = sum(len(pd.read_csv(path)) for path in paths)
    print(f"Cached {row_count} team-game rows across {len(paths)} raw files")
    return 0


def _build_features(games_parquet: Path, output_dir: Path) -> int:
    games = pd.read_parquet(games_parquet)
    features = build_game_features(games)
    feature_dir = output_dir / "features"
    feature_dir.mkdir(parents=True, exist_ok=True)
    feature_path = feature_dir / "games.parquet"
    temporary_path = feature_path.with_suffix(".parquet.tmp")
    features.to_parquet(temporary_path, index=False)
    temporary_path.replace(feature_path)
    print(f"Wrote {len(features)} pre-game feature rows to {feature_path}")
    return 0


def _evaluate_baselines(
    features_parquet: Path,
    train_seasons: list[str],
    test_season: str,
    output_dir: Path,
) -> int:
    features = pd.read_parquet(features_parquet)
    split = make_temporal_split(
        features,
        train_seasons=train_seasons,
        validation_seasons=[],
        test_seasons=[test_season],
    )
    results = evaluate_baselines(split.train, split.test)
    report_dir = output_dir / "artifacts" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "baseline_metrics.csv"
    results.to_csv(report_path, index=False)
    print(f"Wrote {len(results)} baseline metric rows to {report_path}")
    return 0


def _simulate_series(
    team_a: str,
    team_b: str,
    team_a_home_probability: float,
    team_a_away_probability: float,
    simulations: int,
    seed: int,
    output_dir: Path,
) -> int:
    output = run_simulator_lab(
        SimulatorLabInput(
            team_a=team_a,
            team_b=team_b,
            team_a_home_win_probability=team_a_home_probability,
            team_a_away_win_probability=team_a_away_probability,
            simulations=simulations,
            seed=seed,
        )
    )
    report_dir = output_dir / "artifacts" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "series_simulation.json"
    report_path.write_text(json.dumps(output.to_report(), indent=2, sort_keys=True))
    print(f"Wrote seeded series simulation report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
