from pathlib import Path

import pandas as pd

from nba_forecast.cli import main

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "team_game_rows.csv"
MULTI_SEASON_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "multi_season_team_game_rows.csv"
)


def test_build_games_command_creates_processed_outputs(
    tmp_path: Path,
    capsys: object,
) -> None:
    exit_code = main(
        [
            "build-games",
            "--raw-csv",
            str(FIXTURE_PATH),
            "--output-dir",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert exit_code == 0
    assert "Wrote 2 canonical games" in captured.out
    assert (tmp_path / "processed" / "games.parquet").exists()
    assert (tmp_path / "nba_forecast.duckdb").exists()


def test_build_games_command_combines_multiple_raw_csv_files(tmp_path: Path) -> None:
    rows = pd.read_csv(
        MULTI_SEASON_FIXTURE_PATH,
        dtype={"GAME_ID": "string", "SEASON_ID": "string"},
    )
    first_path = tmp_path / "first.csv"
    second_path = tmp_path / "second.csv"
    rows.loc[rows["SEASON_ID"] == "22024"].to_csv(first_path, index=False)
    rows.loc[rows["SEASON_ID"] == "22025"].to_csv(second_path, index=False)

    exit_code = main(
        [
            "build-games",
            "--raw-csv",
            str(first_path),
            str(second_path),
            "--output-dir",
            str(tmp_path / "output"),
        ]
    )

    games = pd.read_parquet(tmp_path / "output" / "processed" / "games.parquet")
    assert exit_code == 0
    assert len(games) == 4
    assert games["season_id"].tolist() == ["22024", "22024", "22025", "22025"]


def test_feature_and_baseline_commands_create_reproducible_outputs(
    tmp_path: Path,
) -> None:
    assert (
        main(
            [
                "build-games",
                "--raw-csv",
                str(MULTI_SEASON_FIXTURE_PATH),
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "build-features",
                "--games-parquet",
                str(tmp_path / "processed" / "games.parquet"),
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "evaluate-baselines",
                "--features-parquet",
                str(tmp_path / "features" / "games.parquet"),
                "--train-seasons",
                "22024",
                "--test-season",
                "22025",
                "--output-dir",
                str(tmp_path),
            ]
        )
        == 0
    )

    assert (tmp_path / "features" / "games.parquet").exists()
    report_path = tmp_path / "artifacts" / "reports" / "baseline_metrics.csv"
    assert report_path.exists()

    report = pd.read_csv(report_path)
    assert report["model"].tolist() == [
        "constant_home_rate",
        "season_win_pct",
        "elo",
        "logistic_regression",
    ]
