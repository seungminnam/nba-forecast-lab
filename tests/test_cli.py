from pathlib import Path

from nba_forecast.cli import main

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "team_game_rows.csv"


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

