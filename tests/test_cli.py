import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from nba_forecast.cli import main
from nba_forecast.data.source_nba import raw_cache_path
from nba_forecast.features.game_features import MODEL_FEATURE_COLUMNS
from nba_forecast.models.artifacts import (
    ModelBundle,
    ModelBundleMetadata,
    save_model_bundle,
)
from nba_forecast.models.baselines import fit_logistic_regression
from nba_forecast.models.calibration import RawCalibrator

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


def test_fetch_history_command_reuses_existing_season_caches(
    tmp_path: Path,
) -> None:
    rows = pd.read_csv(MULTI_SEASON_FIXTURE_PATH)
    for season in ("2024-25", "2025-26"):
        path = raw_cache_path(tmp_path, season, "Regular Season")
        path.parent.mkdir(parents=True, exist_ok=True)
        rows.to_csv(path, index=False)

    exit_code = main(
        [
            "fetch-history",
            "--seasons",
            "2024-25",
            "2025-26",
            "--season-types",
            "Regular Season",
            "--cache-dir",
            str(tmp_path),
        ]
    )

    assert exit_code == 0


def test_simulate_series_command_writes_json_report(tmp_path: Path) -> None:
    exit_code = main(
        [
            "simulate-series",
            "--team-a",
            "Knicks",
            "--team-b",
            "Spurs",
            "--team-a-home-probability",
            "0.62",
            "--team-a-away-probability",
            "0.47",
            "--simulations",
            "1000",
            "--seed",
            "2026",
            "--output-dir",
            str(tmp_path),
        ]
    )

    report_path = tmp_path / "artifacts" / "reports" / "series_simulation.json"
    report = json.loads(report_path.read_text())

    assert exit_code == 0
    assert report["inputs"]["team_a"] == "Knicks"
    assert report["inputs"]["team_b"] == "Spurs"
    assert report["result"]["simulations"] == 1000


def test_predict_matchup_command_writes_auditable_json_report(tmp_path: Path) -> None:
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
    bundle_path = tmp_path / "model.joblib"
    _write_test_bundle(bundle_path)

    exit_code = main(
        [
            "predict-matchup",
            "--games-parquet",
            str(tmp_path / "processed" / "games.parquet"),
            "--model-bundle",
            str(bundle_path),
            "--game-id",
            "scheduled-1",
            "--game-date",
            "2025-10-25",
            "--as-of-date",
            "2025-10-25",
            "--season-id",
            "22025",
            "--home-team-id",
            "1",
            "--away-team-id",
            "2",
            "--home-team-abbreviation",
            "HOM",
            "--away-team-abbreviation",
            "AWY",
            "--output-dir",
            str(tmp_path),
        ]
    )

    report_path = (
        tmp_path / "artifacts" / "predictions" / "matchup_prediction.json"
    )
    report = json.loads(report_path.read_text())

    assert exit_code == 0
    assert report["as_of_date"] == "2025-10-25"
    assert report["model_version"] == "cli-test-raw"
    assert report["prediction_timestamp"].endswith("+00:00")
    assert report["feature_version"] == "model-features-v1"
    assert report["final_outcome"] is None
    assert report["matchup"]["game_id"] == "scheduled-1"
    assert 0.0 < report["home_win_probability"] < 1.0
    assert set(report["features"]) == set(MODEL_FEATURE_COLUMNS)


def _write_test_bundle(path: Path) -> None:
    rows = 20
    frame = pd.DataFrame(
        {
            feature: [
                ((-1) ** index) * (position + 1) / 10
                for index in range(rows)
            ]
            for position, feature in enumerate(MODEL_FEATURE_COLUMNS)
        }
    )
    frame["home_win"] = [index % 2 for index in range(rows)]
    metadata = ModelBundleMetadata(
        version="cli-test-raw",
        created_at=datetime(2026, 6, 11, tzinfo=timezone.utc).isoformat(),
        base_model="logistic_regression",
        calibration_method="raw",
        feature_columns=MODEL_FEATURE_COLUMNS,
        training_seasons=("22025",),
        calibration_season="22025",
        test_season="22025",
        metrics={"brier_score": 0.2},
    )
    save_model_bundle(
        ModelBundle(
            model=fit_logistic_regression(frame),
            calibrator=RawCalibrator(),
            metadata=metadata,
        ),
        path,
    )
